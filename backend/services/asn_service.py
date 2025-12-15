"""
Advanced Shipment Notice (ASN) Service

Business logic for ASN operations:
- Create ASN linked to Purchase Order
- Retrieve ASN by ID
- List all ASNs
- Validate ASN against PO
- Generate unique ASN IDs
- Update ASN status (for future use by receipt service)
"""

from typing import List, Optional
from backend.database import db, row_to_dict, rows_to_dict_list
from backend.models import CreateASNRequest, ASNResponse, ASNListItem, ASNLineResponse
from backend.config import ASN_PREFIX, ASN_STATUS_CREATED
from backend.utils import (
    get_current_timestamp,
    generate_document_id,
    validate_required_field,
    validate_positive_number
)
from backend.services.po_service import po_exists, get_purchase_order


# ============================================================================
# ASN CREATION
# ============================================================================

def create_asn(request: CreateASNRequest) -> ASNResponse:
    """
    Create a new Advanced Shipment Notice linked to a Purchase Order.

    Business Logic:
    1. Validate that PO exists
    2. Validate request data
    3. Check that ASN quantities don't exceed PO quantities (warning only)
    4. Generate unique ASN ID (format: ASN-YYYY-NNN)
    5. Insert ASN header
    6. Insert ASN lines
    7. Set initial status to 'created'

    Args:
        request: CreateASNRequest with PO reference and line items

    Returns:
        ASNResponse with created ASN data

    Raises:
        ValueError: If validation fails
        Exception: If database operation fails
    """
    # Validate that PO exists
    if not po_exists(request.po_id):
        raise ValueError(f"Purchase Order {request.po_id} does not exist")

    # Validate request
    validate_required_field(request.vendor_name, "Vendor name")
    validate_required_field(request.ship_date, "Ship date")

    if not request.lines or len(request.lines) == 0:
        raise ValueError("ASN must have at least one line item")

    # Validate each line
    for line in request.lines:
        validate_positive_number(line.quantity_shipped, f"Quantity on line {line.line_number}")

    # Optional: Validate ASN quantities against PO quantities (warning only for now)
    # In a real system, you might want to enforce strict validation here
    po = get_purchase_order(request.po_id)
    if po:
        _validate_asn_quantities(request.lines, po)

    # Generate unique ASN ID
    existing_asn_ids = _get_all_asn_ids()
    asn_id = generate_document_id(ASN_PREFIX, existing_asn_ids)

    # Insert ASN header
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Insert asns record
        cursor.execute("""
            INSERT INTO asns (
                asn_id, po_id, vendor_name, ship_date,
                expected_delivery, status, tracking_number, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asn_id,
            request.po_id,
            request.vendor_name,
            request.ship_date,
            request.expected_delivery,
            ASN_STATUS_CREATED,
            request.tracking_number,
            request.notes
        ))

        # Insert ASN lines
        line_responses = []
        for line in request.lines:
            cursor.execute("""
                INSERT INTO asn_lines (
                    asn_id, line_number, product_sku, product_description,
                    quantity_shipped
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                asn_id,
                line.line_number,
                line.product_sku,
                line.product_description,
                line.quantity_shipped
            ))

            line_id = cursor.lastrowid

            line_responses.append(ASNLineResponse(
                line_id=line_id,
                line_number=line.line_number,
                product_sku=line.product_sku,
                product_description=line.product_description,
                quantity_shipped=line.quantity_shipped
            ))

    # Return created ASN
    return ASNResponse(
        asn_id=asn_id,
        po_id=request.po_id,
        vendor_name=request.vendor_name,
        ship_date=request.ship_date,
        expected_delivery=request.expected_delivery,
        status=ASN_STATUS_CREATED,
        tracking_number=request.tracking_number,
        notes=request.notes,
        lines=line_responses
    )


# ============================================================================
# ASN RETRIEVAL
# ============================================================================

def get_asn(asn_id: str) -> Optional[ASNResponse]:
    """
    Retrieve an ASN by ID with all line items.

    Args:
        asn_id: ASN ID

    Returns:
        ASNResponse if found, None otherwise
    """
    # Get ASN header
    asn_header = db.execute_query(
        "SELECT * FROM asns WHERE asn_id = ?",
        (asn_id,)
    )

    if not asn_header:
        return None

    asn = row_to_dict(asn_header[0])

    # Get ASN lines
    asn_lines = db.execute_query(
        "SELECT * FROM asn_lines WHERE asn_id = ? ORDER BY line_number",
        (asn_id,)
    )

    lines = []
    for line_row in asn_lines:
        line = row_to_dict(line_row)
        lines.append(ASNLineResponse(
            line_id=line['line_id'],
            line_number=line['line_number'],
            product_sku=line['product_sku'],
            product_description=line['product_description'],
            quantity_shipped=line['quantity_shipped']
        ))

    return ASNResponse(
        asn_id=asn['asn_id'],
        po_id=asn['po_id'],
        vendor_name=asn['vendor_name'],
        ship_date=asn['ship_date'],
        expected_delivery=asn['expected_delivery'],
        status=asn['status'],
        tracking_number=asn['tracking_number'],
        notes=asn['notes'],
        lines=lines
    )


def list_asns() -> List[ASNListItem]:
    """
    List all ASNs with summary information.

    Returns:
        List of ASNListItem objects
    """
    query = """
        SELECT
            asn.asn_id,
            asn.po_id,
            asn.vendor_name,
            asn.status,
            asn.ship_date,
            asn.tracking_number,
            COUNT(lines.line_id) as line_count
        FROM asns asn
        LEFT JOIN asn_lines lines ON asn.asn_id = lines.asn_id
        GROUP BY asn.asn_id
        ORDER BY asn.ship_date DESC
    """

    results = db.execute_query(query)

    asn_list = []
    for row in results:
        asn_dict = row_to_dict(row)
        asn_list.append(ASNListItem(
            asn_id=asn_dict['asn_id'],
            po_id=asn_dict['po_id'],
            vendor_name=asn_dict['vendor_name'],
            status=asn_dict['status'],
            ship_date=asn_dict['ship_date'],
            tracking_number=asn_dict['tracking_number'],
            line_count=asn_dict['line_count'] or 0
        ))

    return asn_list


def get_asns_by_po(po_id: str) -> List[ASNListItem]:
    """
    Get all ASNs for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID

    Returns:
        List of ASNListItem objects for the PO
    """
    query = """
        SELECT
            asn.asn_id,
            asn.po_id,
            asn.vendor_name,
            asn.status,
            asn.ship_date,
            asn.tracking_number,
            COUNT(lines.line_id) as line_count
        FROM asns asn
        LEFT JOIN asn_lines lines ON asn.asn_id = lines.asn_id
        WHERE asn.po_id = ?
        GROUP BY asn.asn_id
        ORDER BY asn.ship_date DESC
    """

    results = db.execute_query(query, (po_id,))

    asn_list = []
    for row in results:
        asn_dict = row_to_dict(row)
        asn_list.append(ASNListItem(
            asn_id=asn_dict['asn_id'],
            po_id=asn_dict['po_id'],
            vendor_name=asn_dict['vendor_name'],
            status=asn_dict['status'],
            ship_date=asn_dict['ship_date'],
            tracking_number=asn_dict['tracking_number'],
            line_count=asn_dict['line_count'] or 0
        ))

    return asn_list


# ============================================================================
# ASN STATUS UPDATES
# ============================================================================

def update_asn_status(asn_id: str, new_status: str) -> bool:
    """
    Update the status of an ASN.

    This function is used by other services to update ASN status
    based on business events (e.g., 'in_transit', 'delivered').

    Args:
        asn_id: ASN ID
        new_status: New status value

    Returns:
        True if updated successfully, False otherwise
    """
    rows_affected = db.execute_update(
        "UPDATE asns SET status = ? WHERE asn_id = ?",
        (new_status, asn_id)
    )

    return rows_affected > 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_all_asn_ids() -> List[str]:
    """
    Get list of all existing ASN IDs.

    Used for generating unique ASN IDs.

    Returns:
        List of ASN ID strings
    """
    results = db.execute_query("SELECT asn_id FROM asns")
    return [row['asn_id'] for row in results]


def _validate_asn_quantities(asn_lines: list, po) -> None:
    """
    Validate that ASN quantities don't exceed PO quantities.

    This is a warning-level validation. In a real system, you might want
    to enforce stricter rules or block ASNs with over-shipments.

    Args:
        asn_lines: List of ASN line items
        po: Purchase Order response object

    Note:
        Currently logs warnings but doesn't block ASN creation.
        Future enhancement: Could return warnings to user interface.
    """
    # Build a map of PO quantities by SKU
    po_quantities = {}
    for po_line in po.lines:
        po_quantities[po_line.product_sku] = po_line.quantity_ordered

    # Check each ASN line against PO
    for asn_line in asn_lines:
        po_qty = po_quantities.get(asn_line.product_sku)

        if po_qty is None:
            # ASN contains SKU not in PO - warning
            print(f"WARNING: ASN contains SKU {asn_line.product_sku} not found in PO")
        elif asn_line.quantity_shipped > po_qty:
            # ASN ships more than ordered - warning
            print(f"WARNING: ASN ships {asn_line.quantity_shipped} of {asn_line.product_sku}, but PO only ordered {po_qty}")


def asn_exists(asn_id: str) -> bool:
    """
    Check if an ASN exists.

    Args:
        asn_id: ASN ID

    Returns:
        True if ASN exists, False otherwise
    """
    results = db.execute_query(
        "SELECT COUNT(*) as count FROM asns WHERE asn_id = ?",
        (asn_id,)
    )

    if results:
        return results[0]['count'] > 0

    return False
