"""
Invoice Service

Business logic for Vendor Invoice operations:
- Create Invoice linked to Purchase Order
- Retrieve Invoice by ID
- List all Invoices
- Calculate totals
- Update Invoice status (used by match engine in Part 6)
"""

from typing import List, Optional
from backend.database import db, row_to_dict, rows_to_dict_list
from backend.models import CreateInvoiceRequest, InvoiceResponse, InvoiceListItem, InvoiceLineResponse
from backend.config import INVOICE_STATUS_PENDING
from backend.utils import (
    validate_required_field,
    validate_positive_number,
    calculate_line_total,
    calculate_document_total
)
from backend.services.po_service import po_exists


# ============================================================================
# INVOICE CREATION
# ============================================================================

def create_invoice(request: CreateInvoiceRequest) -> InvoiceResponse:
    """
    Create a new Vendor Invoice linked to a Purchase Order.

    Business Logic:
    1. Validate that PO exists
    2. Validate request data
    3. Calculate line totals and document total
    4. Insert Invoice header
    5. Insert Invoice lines
    6. Set initial status to 'pending'
    7. NOTE: 3-way matching will be triggered in Part 6 (Match Engine)

    Args:
        request: CreateInvoiceRequest with PO reference and line items

    Returns:
        InvoiceResponse with created Invoice data

    Raises:
        ValueError: If validation fails or invoice_id already exists
        Exception: If database operation fails
    """
    # Validate that PO exists
    if not po_exists(request.po_id):
        raise ValueError(f"Purchase Order {request.po_id} does not exist")

    # Check if invoice_id already exists
    if invoice_exists(request.invoice_id):
        raise ValueError(f"Invoice {request.invoice_id} already exists")

    # Validate request
    validate_required_field(request.invoice_id, "Invoice ID")
    validate_required_field(request.vendor_name, "Vendor name")
    validate_required_field(request.invoice_date, "Invoice date")

    if not request.lines or len(request.lines) == 0:
        raise ValueError("Invoice must have at least one line item")

    # Validate each line
    for line in request.lines:
        validate_positive_number(line.quantity_invoiced, f"Quantity on line {line.line_number}")
        validate_positive_number(line.unit_price, f"Unit price on line {line.line_number}")

    # Calculate totals
    line_totals = []
    for line in request.lines:
        line_total = calculate_line_total(line.quantity_invoiced, line.unit_price)
        line.line_total = line_total
        line_totals.append(line_total)

    total_amount = calculate_document_total(line_totals)

    # Insert Invoice header
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Insert invoices record
        cursor.execute("""
            INSERT INTO invoices (
                invoice_id, po_id, vendor_name, invoice_date,
                due_date, total_amount, status, payment_terms, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.invoice_id,
            request.po_id,
            request.vendor_name,
            request.invoice_date,
            request.due_date,
            total_amount,
            INVOICE_STATUS_PENDING,
            request.payment_terms,
            request.notes
        ))

        # Insert Invoice lines
        line_responses = []
        for line in request.lines:
            cursor.execute("""
                INSERT INTO invoice_lines (
                    invoice_id, line_number, product_sku, product_description,
                    quantity_invoiced, unit_price, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.invoice_id,
                line.line_number,
                line.product_sku,
                line.product_description,
                line.quantity_invoiced,
                line.unit_price,
                line.line_total
            ))

            line_id = cursor.lastrowid

            line_responses.append(InvoiceLineResponse(
                line_id=line_id,
                line_number=line.line_number,
                product_sku=line.product_sku,
                product_description=line.product_description,
                quantity_invoiced=line.quantity_invoiced,
                unit_price=line.unit_price,
                line_total=line.line_total
            ))

    # Return created Invoice
    return InvoiceResponse(
        invoice_id=request.invoice_id,
        po_id=request.po_id,
        vendor_name=request.vendor_name,
        invoice_date=request.invoice_date,
        due_date=request.due_date,
        total_amount=total_amount,
        status=INVOICE_STATUS_PENDING,
        payment_terms=request.payment_terms,
        notes=request.notes,
        lines=line_responses
    )


# ============================================================================
# INVOICE RETRIEVAL
# ============================================================================

def get_invoice(invoice_id: str) -> Optional[InvoiceResponse]:
    """
    Retrieve an Invoice by ID with all line items.

    Args:
        invoice_id: Vendor Invoice ID

    Returns:
        InvoiceResponse if found, None otherwise
    """
    # Get Invoice header
    invoice_header = db.execute_query(
        "SELECT * FROM invoices WHERE invoice_id = ?",
        (invoice_id,)
    )

    if not invoice_header:
        return None

    invoice = row_to_dict(invoice_header[0])

    # Get Invoice lines
    invoice_lines = db.execute_query(
        "SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY line_number",
        (invoice_id,)
    )

    lines = []
    for line_row in invoice_lines:
        line = row_to_dict(line_row)
        lines.append(InvoiceLineResponse(
            line_id=line['line_id'],
            line_number=line['line_number'],
            product_sku=line['product_sku'],
            product_description=line['product_description'],
            quantity_invoiced=line['quantity_invoiced'],
            unit_price=line['unit_price'],
            line_total=line['line_total']
        ))

    return InvoiceResponse(
        invoice_id=invoice['invoice_id'],
        po_id=invoice['po_id'],
        vendor_name=invoice['vendor_name'],
        invoice_date=invoice['invoice_date'],
        due_date=invoice['due_date'],
        total_amount=invoice['total_amount'],
        status=invoice['status'],
        payment_terms=invoice['payment_terms'],
        notes=invoice['notes'],
        lines=lines
    )


def list_invoices() -> List[InvoiceListItem]:
    """
    List all Invoices with summary information.

    Returns:
        List of InvoiceListItem objects
    """
    query = """
        SELECT
            inv.invoice_id,
            inv.po_id,
            inv.vendor_name,
            inv.status,
            inv.invoice_date,
            inv.total_amount,
            COUNT(lines.line_id) as line_count
        FROM invoices inv
        LEFT JOIN invoice_lines lines ON inv.invoice_id = lines.invoice_id
        GROUP BY inv.invoice_id
        ORDER BY inv.invoice_date DESC
    """

    results = db.execute_query(query)

    invoice_list = []
    for row in results:
        invoice_dict = row_to_dict(row)
        invoice_list.append(InvoiceListItem(
            invoice_id=invoice_dict['invoice_id'],
            po_id=invoice_dict['po_id'],
            vendor_name=invoice_dict['vendor_name'],
            status=invoice_dict['status'],
            invoice_date=invoice_dict['invoice_date'],
            total_amount=invoice_dict['total_amount'],
            line_count=invoice_dict['line_count'] or 0
        ))

    return invoice_list


def get_invoices_by_po(po_id: str) -> List[InvoiceListItem]:
    """
    Get all Invoices for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID

    Returns:
        List of InvoiceListItem objects for the PO
    """
    query = """
        SELECT
            inv.invoice_id,
            inv.po_id,
            inv.vendor_name,
            inv.status,
            inv.invoice_date,
            inv.total_amount,
            COUNT(lines.line_id) as line_count
        FROM invoices inv
        LEFT JOIN invoice_lines lines ON inv.invoice_id = lines.invoice_id
        WHERE inv.po_id = ?
        GROUP BY inv.invoice_id
        ORDER BY inv.invoice_date DESC
    """

    results = db.execute_query(query, (po_id,))

    invoice_list = []
    for row in results:
        invoice_dict = row_to_dict(row)
        invoice_list.append(InvoiceListItem(
            invoice_id=invoice_dict['invoice_id'],
            po_id=invoice_dict['po_id'],
            vendor_name=invoice_dict['vendor_name'],
            status=invoice_dict['status'],
            invoice_date=invoice_dict['invoice_date'],
            total_amount=invoice_dict['total_amount'],
            line_count=invoice_dict['line_count'] or 0
        ))

    return invoice_list


# ============================================================================
# INVOICE STATUS UPDATES
# ============================================================================

def update_invoice_status(invoice_id: str, new_status: str) -> bool:
    """
    Update the status of an Invoice.

    This function will be used by the match engine (Part 6) to update
    invoice status based on match results:
    - 'matched' if all lines pass 3-way match
    - 'blocked' if any exceptions detected
    - 'approved' if exceptions resolved/waived
    - 'paid' when payment processed

    Args:
        invoice_id: Invoice ID
        new_status: New status value

    Returns:
        True if updated successfully, False otherwise
    """
    rows_affected = db.execute_update(
        "UPDATE invoices SET status = ? WHERE invoice_id = ?",
        (new_status, invoice_id)
    )

    return rows_affected > 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def invoice_exists(invoice_id: str) -> bool:
    """
    Check if an Invoice exists.

    Args:
        invoice_id: Invoice ID

    Returns:
        True if Invoice exists, False otherwise
    """
    results = db.execute_query(
        "SELECT COUNT(*) as count FROM invoices WHERE invoice_id = ?",
        (invoice_id,)
    )

    if results:
        return results[0]['count'] > 0

    return False


def get_invoice_lines_by_sku(invoice_id: str, product_sku: str) -> List[dict]:
    """
    Get invoice lines for a specific product SKU.

    Used by match engine (Part 6) to find invoice prices/quantities
    for verification against PO and receipts.

    Args:
        invoice_id: Invoice ID
        product_sku: Product SKU to search for

    Returns:
        List of matching invoice line dictionaries
    """
    results = db.execute_query(
        "SELECT * FROM invoice_lines WHERE invoice_id = ? AND product_sku = ?",
        (invoice_id, product_sku)
    )

    return rows_to_dict_list(results)
