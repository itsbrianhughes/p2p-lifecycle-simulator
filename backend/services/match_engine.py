"""
3-Way Match Engine - Core Business Logic

This module implements the 3-way matching algorithm that compares:
1. Purchase Order (what was ordered)
2. Goods Receipt (what was received)
3. Vendor Invoice (what was billed)

The match engine:
- Compares prices (Invoice vs PO) with tolerance thresholds
- Compares quantities (Invoice vs Receipt) with tolerance thresholds
- Creates match records with variance details
- Updates invoice status (matched, blocked)
- Identifies exceptions for further investigation
"""

from typing import Optional, List, Dict
from datetime import datetime

from backend.database import db
from backend.config import (
    PRICE_TOLERANCE_PCT,
    QUANTITY_TOLERANCE_PCT,
    INVOICE_STATUS_MATCHED,
    INVOICE_STATUS_BLOCKED
)
from backend.models import (
    PerformMatchRequest,
    MatchResponse,
    MatchLineVariance,
    MatchListItem
)
from backend.services import po_service, receipt_service, invoice_service


# ============================================================================
# CORE MATCHING LOGIC
# ============================================================================

def perform_three_way_match(request: PerformMatchRequest) -> MatchResponse:
    """
    Performs 3-way match for an invoice.

    Process:
    1. Fetch Invoice, PO, and cumulative Receipts
    2. Compare line-by-line:
       - Price: Invoice vs PO (±2% tolerance)
       - Quantity: Invoice vs cumulative Receipts (±5% tolerance)
    3. Create match record
    4. Update invoice status (matched or blocked)
    5. Return detailed variance report

    Args:
        request: Match request containing invoice_id

    Returns:
        MatchResponse with variance details and match status

    Raises:
        ValueError: If invoice, PO, or receipts not found
    """
    invoice_id = request.invoice_id

    # 1. Fetch Invoice
    invoice = invoice_service.get_invoice(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice not found: {invoice_id}")

    # 2. Fetch related PO
    po = po_service.get_purchase_order(invoice.po_id)
    if not po:
        raise ValueError(f"Purchase Order not found for invoice: {invoice.po_id}")

    # 3. Fetch cumulative receipts for PO
    cumulative_receipts = _get_cumulative_receipts_for_po(invoice.po_id)

    # Get the most recent receipt ID for record keeping
    receipt_id = _get_most_recent_receipt_id(invoice.po_id)

    # 4. Build PO and Receipt lookup maps (by SKU)
    po_lines_map = {line.product_sku: line for line in po.lines}
    receipt_map = cumulative_receipts  # Already SKU-based

    # 5. Perform line-by-line variance analysis
    line_variances = []
    total_variance_amount = 0.0
    all_lines_matched = True

    for inv_line in invoice.lines:
        sku = inv_line.product_sku

        # Get corresponding PO line
        po_line = po_lines_map.get(sku)
        if not po_line:
            raise ValueError(
                f"Product {sku} on invoice not found in PO {invoice.po_id}"
            )

        # Get cumulative received quantity
        receipt_qty = receipt_map.get(sku, 0.0)

        # Calculate variances
        variance = _calculate_line_variance(
            inv_line=inv_line,
            po_line=po_line,
            receipt_qty=receipt_qty
        )

        line_variances.append(variance)
        total_variance_amount += abs(variance.price_variance_amount)

        if variance.line_status == "blocked":
            all_lines_matched = False

    # 6. Determine overall match status
    match_status = INVOICE_STATUS_MATCHED if all_lines_matched else INVOICE_STATUS_BLOCKED

    # 7. Create match record in database
    match_id = _create_match_record(
        invoice_id=invoice_id,
        po_id=invoice.po_id,
        receipt_id=receipt_id,
        match_status=match_status,
        total_variance=total_variance_amount,
        line_variances=line_variances
    )

    # 8. Update invoice status
    invoice_service.update_invoice_status(invoice_id, match_status)

    # 9. Create exceptions for blocked line items
    if match_status == INVOICE_STATUS_BLOCKED:
        from backend.services import exception_service
        exception_service.create_exceptions_from_match(
            match_id=match_id,
            invoice_id=invoice_id,
            po_id=invoice.po_id,
            line_variances=line_variances
        )

    # 10. Build summary
    summary = {
        "total_lines": len(line_variances),
        "matched_lines": sum(1 for v in line_variances if v.line_status == "matched"),
        "blocked_lines": sum(1 for v in line_variances if v.line_status == "blocked")
    }

    # 11. Return match response
    return MatchResponse(
        match_id=match_id,
        invoice_id=invoice_id,
        po_id=invoice.po_id,
        receipt_id=receipt_id,
        match_status=match_status,
        match_date=datetime.utcnow().isoformat(),
        total_variance_amount=total_variance_amount,
        line_variances=line_variances,
        summary=summary
    )


# ============================================================================
# VARIANCE CALCULATION
# ============================================================================

def _calculate_line_variance(
    inv_line,
    po_line,
    receipt_qty: float
) -> MatchLineVariance:
    """
    Calculates variance for a single line item.

    Compares:
    - Price: Invoice vs PO (±2% tolerance)
    - Quantity: Invoice vs cumulative Receipt (±5% tolerance)

    Args:
        inv_line: Invoice line item
        po_line: PO line item
        receipt_qty: Cumulative received quantity

    Returns:
        MatchLineVariance with all variance calculations
    """
    # Price variance (Invoice vs PO)
    price_variance_amount = (inv_line.unit_price - po_line.unit_price) * inv_line.quantity_invoiced
    price_variance_pct = (
        ((inv_line.unit_price - po_line.unit_price) / po_line.unit_price) * 100
        if po_line.unit_price > 0 else 0.0
    )
    price_match = abs(price_variance_pct) <= PRICE_TOLERANCE_PCT

    # Quantity variance (Invoice vs Receipt)
    quantity_variance = inv_line.quantity_invoiced - receipt_qty
    quantity_variance_pct = (
        (quantity_variance / receipt_qty) * 100
        if receipt_qty > 0 else 0.0
    )
    quantity_match = abs(quantity_variance_pct) <= QUANTITY_TOLERANCE_PCT

    # Overall line status
    line_status = "matched" if (price_match and quantity_match) else "blocked"

    return MatchLineVariance(
        product_sku=inv_line.product_sku,
        product_description=inv_line.product_description,
        po_quantity=po_line.quantity_ordered,
        po_unit_price=po_line.unit_price,
        receipt_quantity=receipt_qty,
        invoice_quantity=inv_line.quantity_invoiced,
        invoice_unit_price=inv_line.unit_price,
        price_variance_pct=round(price_variance_pct, 2),
        price_variance_amount=round(price_variance_amount, 2),
        quantity_variance=round(quantity_variance, 2),
        quantity_variance_pct=round(quantity_variance_pct, 2),
        price_match=price_match,
        quantity_match=quantity_match,
        line_status=line_status
    )


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def _create_match_record(
    invoice_id: str,
    po_id: str,
    receipt_id: Optional[str],
    match_status: str,
    total_variance: float,
    line_variances: List[MatchLineVariance]
) -> int:
    """
    Creates a match record in the database.

    Args:
        invoice_id: Invoice ID
        po_id: Purchase Order ID
        receipt_id: Receipt ID (if available)
        match_status: Overall match status (matched, blocked)
        total_variance: Total variance amount
        line_variances: List of line variances (for JSON storage)

    Returns:
        match_id: Database ID of created match record
    """
    # Convert line variances to JSON-serializable format
    import json
    variances_json = json.dumps([v.model_dump() for v in line_variances])

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO match_records (
                po_id, invoice_id, receipt_id, match_status,
                match_date, total_variance, variance_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            po_id,
            invoice_id,
            receipt_id,
            match_status,
            datetime.utcnow().isoformat(),
            total_variance,
            variances_json
        ))

        match_id = cursor.lastrowid

    return match_id


def _get_cumulative_receipts_for_po(po_id: str) -> Dict[str, float]:
    """
    Gets cumulative received quantities for all SKUs on a PO.

    Args:
        po_id: Purchase Order ID

    Returns:
        Dictionary mapping SKU -> cumulative quantity received
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT rl.product_sku, SUM(rl.quantity_received) as total_received
            FROM receipt_lines rl
            JOIN receipts r ON rl.receipt_id = r.receipt_id
            WHERE r.po_id = ?
            GROUP BY rl.product_sku
        """, (po_id,))

        results = cursor.fetchall()

        cumulative_map = {}
        for row in results:
            sku = row[0]
            total_received = row[1]
            cumulative_map[sku] = total_received

    return cumulative_map


def _get_most_recent_receipt_id(po_id: str) -> Optional[str]:
    """
    Gets the most recent receipt ID for a PO.

    Args:
        po_id: Purchase Order ID

    Returns:
        Receipt ID or None if no receipts exist
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT receipt_id
            FROM receipts
            WHERE po_id = ?
            ORDER BY received_date DESC
            LIMIT 1
        """, (po_id,))

        result = cursor.fetchone()
        return result[0] if result else None


# ============================================================================
# QUERY OPERATIONS
# ============================================================================

def get_match(match_id: int) -> Optional[MatchResponse]:
    """
    Gets a match record by ID.

    Args:
        match_id: Match record ID

    Returns:
        MatchResponse or None if not found
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT match_id, po_id, invoice_id, receipt_id,
                   match_status, match_date, total_variance, variance_details
            FROM match_records
            WHERE match_id = ?
        """, (match_id,))

        result = cursor.fetchone()
        if not result:
            return None

        # Parse variance details from JSON
        import json
        variance_details = json.loads(result[7])
        line_variances = [MatchLineVariance(**v) for v in variance_details]

        # Build summary
        summary = {
            "total_lines": len(line_variances),
            "matched_lines": sum(1 for v in line_variances if v.line_status == "matched"),
            "blocked_lines": sum(1 for v in line_variances if v.line_status == "blocked")
        }

        return MatchResponse(
            match_id=result[0],
            po_id=result[1],
            invoice_id=result[2],
            receipt_id=result[3],
            match_status=result[4],
            match_date=result[5],
            total_variance_amount=result[6],
            line_variances=line_variances,
            summary=summary
        )


def list_matches() -> List[MatchListItem]:
    """
    Lists all match records.

    Returns:
        List of MatchListItem
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT match_id, po_id, invoice_id, receipt_id,
                   match_status, match_date, total_variance
            FROM match_records
            ORDER BY match_date DESC
        """)

        results = cursor.fetchall()

        matches = []
        for row in results:
            matches.append(MatchListItem(
                match_id=row[0],
                po_id=row[1],
                invoice_id=row[2],
                receipt_id=row[3],
                match_status=row[4],
                match_date=row[5],
                total_variance_amount=row[6]
            ))

    return matches


def get_matches_for_invoice(invoice_id: str) -> List[MatchListItem]:
    """
    Gets all match records for a specific invoice.

    Args:
        invoice_id: Invoice ID

    Returns:
        List of MatchListItem
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT match_id, po_id, invoice_id, receipt_id,
                   match_status, match_date, total_variance
            FROM match_records
            WHERE invoice_id = ?
            ORDER BY match_date DESC
        """, (invoice_id,))

        results = cursor.fetchall()

        matches = []
        for row in results:
            matches.append(MatchListItem(
                match_id=row[0],
                po_id=row[1],
                invoice_id=row[2],
                receipt_id=row[3],
                match_status=row[4],
                match_date=row[5],
                total_variance_amount=row[6]
            ))

    return matches
