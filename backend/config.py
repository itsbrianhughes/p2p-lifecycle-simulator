"""
Configuration and Business Rules for P2P Lifecycle Simulator

This module contains all configurable business rules, tolerance thresholds,
and system constants used throughout the P2P workflow.
"""

# ============================================================================
# TOLERANCE THRESHOLDS (Financial Controls)
# ============================================================================

# Price variance tolerance as a percentage
# Example: 2.0 means ±2% variance is acceptable
# If PO price is $100, invoice price between $98-$102 will match
PRICE_TOLERANCE_PCT = 2.0

# Quantity variance tolerance as a percentage
# Example: 5.0 means ±5% variance is acceptable
# If receipt qty is 100, invoice qty between 95-105 will match
QUANTITY_TOLERANCE_PCT = 5.0


# ============================================================================
# DOCUMENT ID PREFIXES
# ============================================================================

PO_PREFIX = "PO"
ASN_PREFIX = "ASN"
RECEIPT_PREFIX = "GR"
INVOICE_PREFIX = "INV"


# ============================================================================
# STATUS VALUES
# ============================================================================

# Purchase Order Statuses
PO_STATUS_OPEN = "open"
PO_STATUS_PARTIALLY_RECEIVED = "partially_received"
PO_STATUS_RECEIVED = "received"
PO_STATUS_CLOSED = "closed"

# ASN Statuses
ASN_STATUS_CREATED = "created"
ASN_STATUS_IN_TRANSIT = "in_transit"
ASN_STATUS_DELIVERED = "delivered"

# Invoice Statuses
INVOICE_STATUS_PENDING = "pending"
INVOICE_STATUS_MATCHED = "matched"
INVOICE_STATUS_BLOCKED = "blocked"
INVOICE_STATUS_APPROVED = "approved"
INVOICE_STATUS_PAID = "paid"

# Match Statuses
MATCH_STATUS_MATCHED = "matched"
MATCH_STATUS_PRICE_VARIANCE = "price_variance"
MATCH_STATUS_QUANTITY_VARIANCE = "quantity_variance"

# Exception Statuses
EXCEPTION_STATUS_OPEN = "open"
EXCEPTION_STATUS_UNDER_REVIEW = "under_review"
EXCEPTION_STATUS_RESOLVED = "resolved"
EXCEPTION_STATUS_WAIVED = "waived"


# ============================================================================
# EXCEPTION TYPES
# ============================================================================

EXCEPTION_TYPE_PRICE_VARIANCE = "price_variance"
EXCEPTION_TYPE_QUANTITY_VARIANCE = "quantity_variance"
EXCEPTION_TYPE_MISSING_RECEIPT = "missing_receipt"
EXCEPTION_TYPE_MISSING_PO = "missing_po"
EXCEPTION_TYPE_OVER_INVOICED = "over_invoiced"


# ============================================================================
# EXCEPTION SEVERITY LEVELS
# ============================================================================

SEVERITY_WARNING = "warning"
SEVERITY_BLOCKING = "blocking"


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_PATH = "data/p2p.db"


# ============================================================================
# API CONFIGURATION
# ============================================================================

API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "P2P Lifecycle Simulator API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
Real-world Procure-to-Pay (P2P) lifecycle simulator demonstrating:
- Purchase Order management
- Advanced Shipment Notices (ASN)
- Goods Receipt processing
- Vendor Invoice verification
- 3-way matching engine
- Exception detection and resolution

Built for integration engineers, EDI consultants, and P2P analysts.
"""


# ============================================================================
# BUSINESS RULE HELPERS
# ============================================================================

def calculate_price_variance_pct(po_price: float, invoice_price: float) -> float:
    """
    Calculate percentage variance between PO price and invoice price.

    Args:
        po_price: Unit price from purchase order
        invoice_price: Unit price from vendor invoice

    Returns:
        Percentage variance (positive if invoice > PO, negative if invoice < PO)
    """
    if po_price == 0:
        return 0.0
    return ((invoice_price - po_price) / po_price) * 100


def calculate_quantity_variance_pct(received_qty: float, invoiced_qty: float) -> float:
    """
    Calculate percentage variance between received quantity and invoiced quantity.

    Args:
        received_qty: Quantity received in goods receipt
        invoiced_qty: Quantity on vendor invoice

    Returns:
        Percentage variance (positive if invoice > receipt, negative if invoice < receipt)
    """
    if received_qty == 0:
        return 0.0
    return ((invoiced_qty - received_qty) / received_qty) * 100


def is_price_within_tolerance(po_price: float, invoice_price: float) -> bool:
    """
    Check if invoice price is within acceptable tolerance of PO price.

    Args:
        po_price: Unit price from purchase order
        invoice_price: Unit price from vendor invoice

    Returns:
        True if variance is within tolerance, False otherwise
    """
    variance_pct = abs(calculate_price_variance_pct(po_price, invoice_price))
    return variance_pct <= PRICE_TOLERANCE_PCT


def is_quantity_within_tolerance(received_qty: float, invoiced_qty: float) -> bool:
    """
    Check if invoiced quantity is within acceptable tolerance of received quantity.

    Args:
        received_qty: Quantity received in goods receipt
        invoiced_qty: Quantity on vendor invoice

    Returns:
        True if variance is within tolerance, False otherwise
    """
    variance_pct = abs(calculate_quantity_variance_pct(received_qty, invoiced_qty))
    return variance_pct <= QUANTITY_TOLERANCE_PCT
