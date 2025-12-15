"""
Database Schema Definitions for P2P Lifecycle Simulator

This module contains all CREATE TABLE statements for the SQLite database.
Tables are organized by business domain:
- Purchase Orders (POs)
- Advanced Shipment Notices (ASNs)
- Goods Receipts
- Invoices
- Match Records
- Exceptions
"""


# ============================================================================
# PURCHASE ORDER TABLES
# ============================================================================

CREATE_TABLE_PURCHASE_ORDERS = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_date TEXT NOT NULL,
    expected_delivery TEXT,
    total_amount REAL NOT NULL,
    notes TEXT
)
"""

CREATE_TABLE_PO_LINES = """
CREATE TABLE IF NOT EXISTS po_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    product_sku TEXT NOT NULL,
    product_description TEXT NOT NULL,
    quantity_ordered REAL NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    UNIQUE(po_id, line_number)
)
"""


# ============================================================================
# ADVANCED SHIPMENT NOTICE (ASN) TABLES
# ============================================================================

CREATE_TABLE_ASNS = """
CREATE TABLE IF NOT EXISTS asns (
    asn_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    ship_date TEXT NOT NULL,
    expected_delivery TEXT,
    status TEXT NOT NULL,
    tracking_number TEXT,
    notes TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
)
"""

CREATE_TABLE_ASN_LINES = """
CREATE TABLE IF NOT EXISTS asn_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asn_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    product_sku TEXT NOT NULL,
    product_description TEXT NOT NULL,
    quantity_shipped REAL NOT NULL,
    FOREIGN KEY (asn_id) REFERENCES asns(asn_id) ON DELETE CASCADE,
    UNIQUE(asn_id, line_number)
)
"""


# ============================================================================
# GOODS RECEIPT TABLES
# ============================================================================

CREATE_TABLE_RECEIPTS = """
CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    asn_id TEXT,
    received_date TEXT NOT NULL,
    warehouse_location TEXT,
    received_by TEXT,
    notes TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (asn_id) REFERENCES asns(asn_id)
)
"""

CREATE_TABLE_RECEIPT_LINES = """
CREATE TABLE IF NOT EXISTS receipt_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    product_sku TEXT NOT NULL,
    product_description TEXT NOT NULL,
    quantity_received REAL NOT NULL,
    condition TEXT,
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE,
    UNIQUE(receipt_id, line_number)
)
"""


# ============================================================================
# INVOICE TABLES
# ============================================================================

CREATE_TABLE_INVOICES = """
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL,
    payment_terms TEXT,
    notes TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
)
"""

CREATE_TABLE_INVOICE_LINES = """
CREATE TABLE IF NOT EXISTS invoice_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    product_sku TEXT NOT NULL,
    product_description TEXT NOT NULL,
    quantity_invoiced REAL NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    UNIQUE(invoice_id, line_number)
)
"""


# ============================================================================
# MATCH RECORDS TABLE
# ============================================================================

CREATE_TABLE_MATCH_RECORDS = """
CREATE TABLE IF NOT EXISTS match_records (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id TEXT NOT NULL,
    receipt_id TEXT,
    invoice_id TEXT NOT NULL,
    match_status TEXT NOT NULL,
    match_date TEXT NOT NULL,
    total_variance REAL NOT NULL DEFAULT 0.0,
    variance_details TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
)
"""


# ============================================================================
# EXCEPTIONS TABLE
# ============================================================================

CREATE_TABLE_EXCEPTIONS = """
CREATE TABLE IF NOT EXISTS exceptions (
    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    exception_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    po_id TEXT,
    invoice_id TEXT,
    product_sku TEXT,
    description TEXT NOT NULL,
    variance_amount REAL,
    created_date TEXT NOT NULL,
    resolved_date TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    FOREIGN KEY (match_id) REFERENCES match_records(match_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
)
"""


# ============================================================================
# SCHEMA RETRIEVAL FUNCTION
# ============================================================================

def get_create_table_statements() -> list:
    """
    Return list of all CREATE TABLE statements in proper order.

    The order matters due to foreign key constraints:
    - Parent tables (referenced by foreign keys) must be created first
    - Child tables (with foreign keys) must be created after

    Returns:
        List of SQL CREATE TABLE statements
    """
    return [
        # Parent tables first (no foreign key dependencies)
        CREATE_TABLE_PURCHASE_ORDERS,

        # Tables with FK to purchase_orders
        CREATE_TABLE_PO_LINES,
        CREATE_TABLE_ASNS,

        # Tables with FK to asns
        CREATE_TABLE_ASN_LINES,

        # Tables with FK to purchase_orders and asns
        CREATE_TABLE_RECEIPTS,

        # Tables with FK to receipts
        CREATE_TABLE_RECEIPT_LINES,

        # Tables with FK to purchase_orders
        CREATE_TABLE_INVOICES,

        # Tables with FK to invoices
        CREATE_TABLE_INVOICE_LINES,

        # Tables with FK to multiple parents
        CREATE_TABLE_MATCH_RECORDS,
        CREATE_TABLE_EXCEPTIONS,
    ]


# ============================================================================
# SCHEMA METADATA (for documentation and validation)
# ============================================================================

SCHEMA_VERSION = "1.0.0"

TABLE_DESCRIPTIONS = {
    "purchase_orders": "Purchase Order header records",
    "po_lines": "Purchase Order line items (products, quantities, prices)",
    "asns": "Advanced Shipment Notice header records",
    "asn_lines": "ASN line items (shipped products and quantities)",
    "receipts": "Goods Receipt header records",
    "receipt_lines": "Goods Receipt line items (received products and quantities)",
    "invoices": "Vendor Invoice header records",
    "invoice_lines": "Invoice line items (billed products, quantities, prices)",
    "match_records": "3-way match results (PO ↔ Receipt ↔ Invoice comparison)",
    "exceptions": "Detected variances and blocking issues",
}
