"""
Goods Receipt Service

Business logic for Goods Receipt operations:
- Create Goods Receipt linked to Purchase Order (and optionally ASN)
- Retrieve Receipt by ID
- List all Receipts
- Update PO status based on receipt quantities
- Calculate cumulative received quantities
- Generate unique Receipt IDs
"""

from typing import List, Optional
from backend.database import db, row_to_dict, rows_to_dict_list
from backend.models import CreateReceiptRequest, ReceiptResponse, ReceiptListItem, ReceiptLineResponse
from backend.config import (
    RECEIPT_PREFIX,
    PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_RECEIVED
)
from backend.utils import (
    get_current_timestamp,
    generate_document_id,
    validate_required_field,
    validate_positive_number
)
from backend.services.po_service import po_exists, get_purchase_order, update_po_status
from backend.services.asn_service import asn_exists


# ============================================================================
# GOODS RECEIPT CREATION
# ============================================================================

def create_receipt(request: CreateReceiptRequest) -> ReceiptResponse:
    """
    Create a new Goods Receipt linked to a Purchase Order.

    Business Logic:
    1. Validate that PO exists
    2. Optionally validate that ASN exists (if provided)
    3. Validate request data
    4. Generate unique Receipt ID (format: GR-YYYY-NNN)
    5. Insert Receipt header
    6. Insert Receipt lines
    7. Update PO status based on cumulative received quantities

    Args:
        request: CreateReceiptRequest with PO reference and line items

    Returns:
        ReceiptResponse with created Receipt data

    Raises:
        ValueError: If validation fails
        Exception: If database operation fails
    """
    # Validate that PO exists
    if not po_exists(request.po_id):
        raise ValueError(f"Purchase Order {request.po_id} does not exist")

    # Validate that ASN exists (if provided)
    if request.asn_id and not asn_exists(request.asn_id):
        raise ValueError(f"ASN {request.asn_id} does not exist")

    # Validate request
    validate_required_field(request.received_date, "Received date")

    if not request.lines or len(request.lines) == 0:
        raise ValueError("Receipt must have at least one line item")

    # Validate each line
    for line in request.lines:
        validate_positive_number(line.quantity_received, f"Quantity on line {line.line_number}")

    # Generate unique Receipt ID
    existing_receipt_ids = _get_all_receipt_ids()
    receipt_id = generate_document_id(RECEIPT_PREFIX, existing_receipt_ids)

    # Insert Receipt header
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Insert receipts record
        cursor.execute("""
            INSERT INTO receipts (
                receipt_id, po_id, asn_id, received_date,
                warehouse_location, received_by, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            receipt_id,
            request.po_id,
            request.asn_id,
            request.received_date,
            request.warehouse_location,
            request.received_by,
            request.notes
        ))

        # Insert Receipt lines
        line_responses = []
        for line in request.lines:
            cursor.execute("""
                INSERT INTO receipt_lines (
                    receipt_id, line_number, product_sku, product_description,
                    quantity_received, condition
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                receipt_id,
                line.line_number,
                line.product_sku,
                line.product_description,
                line.quantity_received,
                line.condition or "good"
            ))

            line_id = cursor.lastrowid

            line_responses.append(ReceiptLineResponse(
                line_id=line_id,
                line_number=line.line_number,
                product_sku=line.product_sku,
                product_description=line.product_description,
                quantity_received=line.quantity_received,
                condition=line.condition or "good"
            ))

    # Update PO status based on receipt
    _update_po_status_after_receipt(request.po_id)

    # Return created Receipt
    return ReceiptResponse(
        receipt_id=receipt_id,
        po_id=request.po_id,
        asn_id=request.asn_id,
        received_date=request.received_date,
        warehouse_location=request.warehouse_location,
        received_by=request.received_by,
        notes=request.notes,
        lines=line_responses
    )


# ============================================================================
# GOODS RECEIPT RETRIEVAL
# ============================================================================

def get_receipt(receipt_id: str) -> Optional[ReceiptResponse]:
    """
    Retrieve a Goods Receipt by ID with all line items.

    Args:
        receipt_id: Receipt ID

    Returns:
        ReceiptResponse if found, None otherwise
    """
    # Get Receipt header
    receipt_header = db.execute_query(
        "SELECT * FROM receipts WHERE receipt_id = ?",
        (receipt_id,)
    )

    if not receipt_header:
        return None

    receipt = row_to_dict(receipt_header[0])

    # Get Receipt lines
    receipt_lines = db.execute_query(
        "SELECT * FROM receipt_lines WHERE receipt_id = ? ORDER BY line_number",
        (receipt_id,)
    )

    lines = []
    for line_row in receipt_lines:
        line = row_to_dict(line_row)
        lines.append(ReceiptLineResponse(
            line_id=line['line_id'],
            line_number=line['line_number'],
            product_sku=line['product_sku'],
            product_description=line['product_description'],
            quantity_received=line['quantity_received'],
            condition=line['condition']
        ))

    return ReceiptResponse(
        receipt_id=receipt['receipt_id'],
        po_id=receipt['po_id'],
        asn_id=receipt['asn_id'],
        received_date=receipt['received_date'],
        warehouse_location=receipt['warehouse_location'],
        received_by=receipt['received_by'],
        notes=receipt['notes'],
        lines=lines
    )


def list_receipts() -> List[ReceiptListItem]:
    """
    List all Goods Receipts with summary information.

    Returns:
        List of ReceiptListItem objects
    """
    query = """
        SELECT
            r.receipt_id,
            r.po_id,
            r.asn_id,
            r.received_date,
            r.warehouse_location,
            COUNT(lines.line_id) as line_count
        FROM receipts r
        LEFT JOIN receipt_lines lines ON r.receipt_id = lines.receipt_id
        GROUP BY r.receipt_id
        ORDER BY r.received_date DESC
    """

    results = db.execute_query(query)

    receipt_list = []
    for row in results:
        receipt_dict = row_to_dict(row)
        receipt_list.append(ReceiptListItem(
            receipt_id=receipt_dict['receipt_id'],
            po_id=receipt_dict['po_id'],
            asn_id=receipt_dict['asn_id'],
            received_date=receipt_dict['received_date'],
            warehouse_location=receipt_dict['warehouse_location'],
            line_count=receipt_dict['line_count'] or 0
        ))

    return receipt_list


def get_receipts_by_po(po_id: str) -> List[ReceiptListItem]:
    """
    Get all Receipts for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID

    Returns:
        List of ReceiptListItem objects for the PO
    """
    query = """
        SELECT
            r.receipt_id,
            r.po_id,
            r.asn_id,
            r.received_date,
            r.warehouse_location,
            COUNT(lines.line_id) as line_count
        FROM receipts r
        LEFT JOIN receipt_lines lines ON r.receipt_id = lines.receipt_id
        WHERE r.po_id = ?
        GROUP BY r.receipt_id
        ORDER BY r.received_date DESC
    """

    results = db.execute_query(query, (po_id,))

    receipt_list = []
    for row in results:
        receipt_dict = row_to_dict(row)
        receipt_list.append(ReceiptListItem(
            receipt_id=receipt_dict['receipt_id'],
            po_id=receipt_dict['po_id'],
            asn_id=receipt_dict['asn_id'],
            received_date=receipt_dict['received_date'],
            warehouse_location=receipt_dict['warehouse_location'],
            line_count=receipt_dict['line_count'] or 0
        ))

    return receipt_list


# ============================================================================
# PO STATUS UPDATE LOGIC
# ============================================================================

def _update_po_status_after_receipt(po_id: str) -> None:
    """
    Update PO status based on cumulative received quantities.

    Business Rules:
    - If any line items received → status = 'partially_received'
    - If all line items fully received → status = 'received'

    Args:
        po_id: Purchase Order ID
    """
    # Get PO details
    po = get_purchase_order(po_id)
    if not po:
        return

    # Get cumulative received quantities by SKU
    cumulative_receipts = _get_cumulative_receipts_for_po(po_id)

    # Check receipt status for each PO line
    all_lines_received = True
    any_lines_received = False

    for po_line in po.lines:
        received_qty = cumulative_receipts.get(po_line.product_sku, 0.0)

        if received_qty > 0:
            any_lines_received = True

        if received_qty < po_line.quantity_ordered:
            all_lines_received = False

    # Update PO status
    if all_lines_received:
        update_po_status(po_id, PO_STATUS_RECEIVED)
    elif any_lines_received:
        update_po_status(po_id, PO_STATUS_PARTIALLY_RECEIVED)


def _get_cumulative_receipts_for_po(po_id: str) -> dict:
    """
    Get cumulative received quantities for all SKUs in a PO.

    Args:
        po_id: Purchase Order ID

    Returns:
        Dictionary mapping SKU to total received quantity
    """
    query = """
        SELECT
            rl.product_sku,
            SUM(rl.quantity_received) as total_received
        FROM receipts r
        JOIN receipt_lines rl ON r.receipt_id = rl.receipt_id
        WHERE r.po_id = ?
        GROUP BY rl.product_sku
    """

    results = db.execute_query(query, (po_id,))

    cumulative = {}
    for row in results:
        cumulative[row['product_sku']] = row['total_received']

    return cumulative


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_all_receipt_ids() -> List[str]:
    """
    Get list of all existing Receipt IDs.

    Used for generating unique Receipt IDs.

    Returns:
        List of Receipt ID strings
    """
    results = db.execute_query("SELECT receipt_id FROM receipts")
    return [row['receipt_id'] for row in results]


def receipt_exists(receipt_id: str) -> bool:
    """
    Check if a Receipt exists.

    Args:
        receipt_id: Receipt ID

    Returns:
        True if Receipt exists, False otherwise
    """
    results = db.execute_query(
        "SELECT COUNT(*) as count FROM receipts WHERE receipt_id = ?",
        (receipt_id,)
    )

    if results:
        return results[0]['count'] > 0

    return False


def get_receipt_lines_by_sku(po_id: str, product_sku: str) -> List[dict]:
    """
    Get all receipt lines for a specific PO and product SKU.

    Used by match engine to find received quantities for invoice verification.

    Args:
        po_id: Purchase Order ID
        product_sku: Product SKU to search for

    Returns:
        List of matching receipt line dictionaries
    """
    query = """
        SELECT rl.*
        FROM receipt_lines rl
        JOIN receipts r ON rl.receipt_id = r.receipt_id
        WHERE r.po_id = ? AND rl.product_sku = ?
    """

    results = db.execute_query(query, (po_id, product_sku))
    return rows_to_dict_list(results)
