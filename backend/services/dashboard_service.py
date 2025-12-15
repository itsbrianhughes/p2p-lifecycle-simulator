"""
Dashboard Service - Aggregate Statistics and Lifecycle Views

This module provides:
- Dashboard statistics across all P2P entities
- End-to-end PO lifecycle tracking
- Aggregate financial data
"""

from typing import Optional
from datetime import datetime

from backend.database import db
from backend.models import DashboardStats, POLifecycleResponse, POLifecycleStep
from backend.services import po_service, asn_service, receipt_service, invoice_service, match_engine, exception_service


# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================

def get_dashboard_stats() -> DashboardStats:
    """
    Gets aggregate dashboard statistics.

    Returns:
        DashboardStats with counts, status breakdowns, and financial totals
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Count totals
        cursor.execute("SELECT COUNT(*) FROM purchase_orders")
        total_pos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM asns")
        total_asns = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM receipts")
        total_receipts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM invoices")
        total_invoices = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM match_records")
        total_matches = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM exceptions")
        total_exceptions = cursor.fetchone()[0]

        # PO status breakdown
        cursor.execute("SELECT status, COUNT(*) FROM purchase_orders GROUP BY status")
        pos_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Invoice status breakdown
        cursor.execute("SELECT status, COUNT(*) FROM invoices GROUP BY status")
        invoices_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Exception status breakdown
        cursor.execute("SELECT status, COUNT(*) FROM exceptions GROUP BY status")
        exceptions_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Exception severity breakdown
        cursor.execute("SELECT severity, COUNT(*) FROM exceptions GROUP BY severity")
        exceptions_by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        # Financial totals
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders")
        total_po_amount = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices")
        total_invoice_amount = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(total_variance), 0) FROM match_records")
        total_variance_amount = cursor.fetchone()[0]

    return DashboardStats(
        total_pos=total_pos,
        total_asns=total_asns,
        total_receipts=total_receipts,
        total_invoices=total_invoices,
        total_matches=total_matches,
        total_exceptions=total_exceptions,
        pos_by_status=pos_by_status,
        invoices_by_status=invoices_by_status,
        exceptions_by_status=exceptions_by_status,
        exceptions_by_severity=exceptions_by_severity,
        total_po_amount=total_po_amount,
        total_invoice_amount=total_invoice_amount,
        total_variance_amount=total_variance_amount
    )


# ============================================================================
# PO LIFECYCLE VIEW
# ============================================================================

def get_po_lifecycle(po_id: str) -> Optional[POLifecycleResponse]:
    """
    Gets complete lifecycle view for a PO.

    Includes: PO → ASNs → Receipts → Invoices → Matches → Exceptions

    Args:
        po_id: Purchase Order ID

    Returns:
        POLifecycleResponse or None if PO not found
    """
    # Get PO
    po = po_service.get_purchase_order(po_id)
    if not po:
        return None

    # Get associated entities
    asns = asn_service.get_asns_by_po(po_id)
    receipts = receipt_service.get_receipts_by_po(po_id)
    invoices = invoice_service.get_invoices_by_po(po_id)

    # Get matches (from invoices)
    matches = []
    for invoice in invoices:
        invoice_matches = match_engine.get_matches_for_invoice(invoice.invoice_id)
        matches.extend(invoice_matches)

    # Get exceptions (from invoices)
    exceptions = []
    for invoice in invoices:
        invoice_exceptions = exception_service.get_exceptions_for_invoice(invoice.invoice_id)
        exceptions.extend(invoice_exceptions)

    # Build timeline
    timeline = []

    # Add PO
    timeline.append(POLifecycleStep(
        step_type="po",
        step_id=po.po_id,
        step_date=po.created_date,
        status=po.status,
        details={"total_amount": po.total_amount, "vendor": po.vendor_name}
    ))

    # Add ASNs
    for asn in asns:
        timeline.append(POLifecycleStep(
            step_type="asn",
            step_id=asn.asn_id,
            step_date=asn.ship_date,
            status=asn.status,
            details={"tracking": asn.tracking_number}
        ))

    # Add Receipts
    for receipt in receipts:
        timeline.append(POLifecycleStep(
            step_type="receipt",
            step_id=receipt.receipt_id,
            step_date=receipt.received_date,
            status=None,
            details={"warehouse": receipt.warehouse_location}
        ))

    # Add Invoices
    for invoice in invoices:
        timeline.append(POLifecycleStep(
            step_type="invoice",
            step_id=invoice.invoice_id,
            step_date=invoice.invoice_date,
            status=invoice.status,
            details={"total_amount": invoice.total_amount}
        ))

    # Add Matches
    for match in matches:
        timeline.append(POLifecycleStep(
            step_type="match",
            step_id=f"MATCH-{match.match_id}",
            step_date=match.match_date,
            status=match.match_status,
            details={"variance": match.total_variance_amount}
        ))

    # Add Exceptions
    for exception in exceptions:
        timeline.append(POLifecycleStep(
            step_type="exception",
            step_id=f"EXC-{exception.exception_id}",
            step_date=exception.created_date,
            status=exception.status,
            details={"type": exception.exception_type, "severity": exception.severity}
        ))

    # Sort timeline by date
    timeline.sort(key=lambda x: x.step_date)

    return POLifecycleResponse(
        po_id=po.po_id,
        vendor_name=po.vendor_name,
        total_amount=po.total_amount,
        status=po.status,
        purchase_order=po.model_dump(),
        asns=[asn.model_dump() for asn in asns],
        receipts=[receipt.model_dump() for receipt in receipts],
        invoices=[invoice.model_dump() for invoice in invoices],
        matches=[match.model_dump() for match in matches],
        exceptions=[exception.model_dump() for exception in exceptions],
        timeline=timeline
    )
