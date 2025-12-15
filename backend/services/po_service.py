"""
Purchase Order Service

Business logic for Purchase Order operations:
- Create PO with line items
- Retrieve PO by ID
- List all POs
- Calculate totals
- Generate unique PO IDs
- Update PO status (used by receipt service later)
"""

from typing import List, Optional
from backend.database import db, row_to_dict, rows_to_dict_list
from backend.models import CreatePORequest, PurchaseOrderResponse, POListItem, POLineResponse
from backend.config import PO_PREFIX, PO_STATUS_OPEN
from backend.utils import (
    get_current_timestamp,
    generate_document_id,
    calculate_line_total,
    calculate_document_total,
    validate_required_field,
    validate_positive_number
)


# ============================================================================
# PURCHASE ORDER CREATION
# ============================================================================

def create_purchase_order(request: CreatePORequest) -> PurchaseOrderResponse:
    """
    Create a new Purchase Order with line items.

    Business Logic:
    1. Validate request data
    2. Generate unique PO ID (format: PO-YYYY-NNN)
    3. Calculate line totals and document total
    4. Insert PO header
    5. Insert PO lines
    6. Set initial status to 'open'

    Args:
        request: CreatePORequest with vendor info and line items

    Returns:
        PurchaseOrderResponse with created PO data

    Raises:
        ValueError: If validation fails
        Exception: If database operation fails
    """
    # Validate request
    validate_required_field(request.vendor_name, "Vendor name")
    validate_required_field(request.vendor_id, "Vendor ID")

    if not request.lines or len(request.lines) == 0:
        raise ValueError("PO must have at least one line item")

    # Validate each line
    for line in request.lines:
        validate_positive_number(line.quantity_ordered, f"Quantity on line {line.line_number}")
        validate_positive_number(line.unit_price, f"Unit price on line {line.line_number}")

    # Generate unique PO ID
    existing_po_ids = _get_all_po_ids()
    po_id = generate_document_id(PO_PREFIX, existing_po_ids)

    # Calculate totals
    line_totals = []
    for line in request.lines:
        line_total = calculate_line_total(line.quantity_ordered, line.unit_price)
        line.line_total = line_total
        line_totals.append(line_total)

    total_amount = calculate_document_total(line_totals)

    # Get current timestamp
    created_date = get_current_timestamp()

    # Insert PO header
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Insert purchase_orders record
        cursor.execute("""
            INSERT INTO purchase_orders (
                po_id, vendor_name, vendor_id, status, created_date,
                expected_delivery, total_amount, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            po_id,
            request.vendor_name,
            request.vendor_id,
            PO_STATUS_OPEN,
            created_date,
            request.expected_delivery,
            total_amount,
            request.notes
        ))

        # Insert PO lines
        line_responses = []
        for line in request.lines:
            cursor.execute("""
                INSERT INTO po_lines (
                    po_id, line_number, product_sku, product_description,
                    quantity_ordered, unit_price, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                po_id,
                line.line_number,
                line.product_sku,
                line.product_description,
                line.quantity_ordered,
                line.unit_price,
                line.line_total
            ))

            line_id = cursor.lastrowid

            line_responses.append(POLineResponse(
                line_id=line_id,
                line_number=line.line_number,
                product_sku=line.product_sku,
                product_description=line.product_description,
                quantity_ordered=line.quantity_ordered,
                unit_price=line.unit_price,
                line_total=line.line_total
            ))

    # Return created PO
    return PurchaseOrderResponse(
        po_id=po_id,
        vendor_name=request.vendor_name,
        vendor_id=request.vendor_id,
        status=PO_STATUS_OPEN,
        created_date=created_date,
        expected_delivery=request.expected_delivery,
        total_amount=total_amount,
        notes=request.notes,
        lines=line_responses
    )


# ============================================================================
# PURCHASE ORDER RETRIEVAL
# ============================================================================

def get_purchase_order(po_id: str) -> Optional[PurchaseOrderResponse]:
    """
    Retrieve a Purchase Order by ID with all line items.

    Args:
        po_id: Purchase Order ID

    Returns:
        PurchaseOrderResponse if found, None otherwise
    """
    # Get PO header
    po_header = db.execute_query(
        "SELECT * FROM purchase_orders WHERE po_id = ?",
        (po_id,)
    )

    if not po_header:
        return None

    po = row_to_dict(po_header[0])

    # Get PO lines
    po_lines = db.execute_query(
        "SELECT * FROM po_lines WHERE po_id = ? ORDER BY line_number",
        (po_id,)
    )

    lines = []
    for line_row in po_lines:
        line = row_to_dict(line_row)
        lines.append(POLineResponse(
            line_id=line['line_id'],
            line_number=line['line_number'],
            product_sku=line['product_sku'],
            product_description=line['product_description'],
            quantity_ordered=line['quantity_ordered'],
            unit_price=line['unit_price'],
            line_total=line['line_total']
        ))

    return PurchaseOrderResponse(
        po_id=po['po_id'],
        vendor_name=po['vendor_name'],
        vendor_id=po['vendor_id'],
        status=po['status'],
        created_date=po['created_date'],
        expected_delivery=po['expected_delivery'],
        total_amount=po['total_amount'],
        notes=po['notes'],
        lines=lines
    )


def list_purchase_orders() -> List[POListItem]:
    """
    List all Purchase Orders with summary information.

    Returns:
        List of POListItem objects
    """
    query = """
        SELECT
            po.po_id,
            po.vendor_name,
            po.status,
            po.created_date,
            po.total_amount,
            COUNT(lines.line_id) as line_count
        FROM purchase_orders po
        LEFT JOIN po_lines lines ON po.po_id = lines.po_id
        GROUP BY po.po_id
        ORDER BY po.created_date DESC
    """

    results = db.execute_query(query)

    po_list = []
    for row in results:
        po_dict = row_to_dict(row)
        po_list.append(POListItem(
            po_id=po_dict['po_id'],
            vendor_name=po_dict['vendor_name'],
            status=po_dict['status'],
            created_date=po_dict['created_date'],
            total_amount=po_dict['total_amount'],
            line_count=po_dict['line_count'] or 0
        ))

    return po_list


# ============================================================================
# PURCHASE ORDER STATUS UPDATES
# ============================================================================

def update_po_status(po_id: str, new_status: str) -> bool:
    """
    Update the status of a Purchase Order.

    This function is used by other services (e.g., receipt service)
    to update PO status based on business events.

    Args:
        po_id: Purchase Order ID
        new_status: New status value

    Returns:
        True if updated successfully, False otherwise
    """
    rows_affected = db.execute_update(
        "UPDATE purchase_orders SET status = ? WHERE po_id = ?",
        (new_status, po_id)
    )

    return rows_affected > 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_all_po_ids() -> List[str]:
    """
    Get list of all existing PO IDs.

    Used for generating unique PO IDs.

    Returns:
        List of PO ID strings
    """
    results = db.execute_query("SELECT po_id FROM purchase_orders")
    return [row['po_id'] for row in results]


def get_po_lines_by_sku(po_id: str, product_sku: str) -> List[dict]:
    """
    Get PO lines for a specific product SKU.

    Used by match engine to find PO prices for invoice verification.

    Args:
        po_id: Purchase Order ID
        product_sku: Product SKU to search for

    Returns:
        List of matching PO line dictionaries
    """
    results = db.execute_query(
        "SELECT * FROM po_lines WHERE po_id = ? AND product_sku = ?",
        (po_id, product_sku)
    )

    return rows_to_dict_list(results)


def po_exists(po_id: str) -> bool:
    """
    Check if a Purchase Order exists.

    Args:
        po_id: Purchase Order ID

    Returns:
        True if PO exists, False otherwise
    """
    results = db.execute_query(
        "SELECT COUNT(*) as count FROM purchase_orders WHERE po_id = ?",
        (po_id,)
    )

    if results:
        return results[0]['count'] > 0

    return False
