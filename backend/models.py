"""
Pydantic Data Models for P2P Lifecycle Simulator

This module contains all Pydantic models for request/response validation:
- Purchase Orders
- ASNs (Advanced Shipment Notices)
- Goods Receipts
- Invoices
- Match Records
- Exceptions

Models will be added incrementally as each Part is implemented.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# BASE RESPONSE MODELS
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response wrapper."""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    success: bool = False
    error: str
    details: Optional[dict] = None


# ============================================================================
# PURCHASE ORDER MODELS (Part 2)
# ============================================================================

class POLineItem(BaseModel):
    """Purchase Order line item model."""
    line_number: int = Field(..., gt=0, description="Line number (1-based)")
    product_sku: str = Field(..., min_length=1, description="Product SKU/code")
    product_description: str = Field(..., min_length=1, description="Product description")
    quantity_ordered: float = Field(..., gt=0, description="Quantity ordered")
    unit_price: float = Field(..., gt=0, description="Unit price")
    line_total: Optional[float] = Field(None, description="Line total (auto-calculated)")

    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "product_sku": "SKU-12345",
                "product_description": "Widget Pro 2000",
                "quantity_ordered": 100,
                "unit_price": 10.50,
                "line_total": 1050.00
            }
        }


class POLineResponse(POLineItem):
    """Purchase Order line item response (includes database ID)."""
    line_id: int = Field(..., description="Database line ID")


class CreatePORequest(BaseModel):
    """Request model for creating a new Purchase Order."""
    vendor_name: str = Field(..., min_length=1, description="Vendor name")
    vendor_id: str = Field(..., min_length=1, description="Vendor ID/code")
    expected_delivery: Optional[str] = Field(None, description="Expected delivery date (ISO 8601)")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[POLineItem] = Field(..., min_items=1, description="PO line items")

    class Config:
        json_schema_extra = {
            "example": {
                "vendor_name": "Acme Supplies Inc.",
                "vendor_id": "VEND-001",
                "expected_delivery": "2025-01-20",
                "notes": "Urgent order - expedited shipping",
                "lines": [
                    {
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_ordered": 100,
                        "unit_price": 10.50
                    },
                    {
                        "line_number": 2,
                        "product_sku": "SKU-67890",
                        "product_description": "Gadget Ultra",
                        "quantity_ordered": 50,
                        "unit_price": 25.00
                    }
                ]
            }
        }


class PurchaseOrderResponse(BaseModel):
    """Purchase Order response model."""
    po_id: str = Field(..., description="Purchase Order ID")
    vendor_name: str = Field(..., description="Vendor name")
    vendor_id: str = Field(..., description="Vendor ID/code")
    status: str = Field(..., description="PO status")
    created_date: str = Field(..., description="Creation date (ISO 8601)")
    expected_delivery: Optional[str] = Field(None, description="Expected delivery date")
    total_amount: float = Field(..., description="Total PO amount")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[POLineResponse] = Field(..., description="PO line items")

    class Config:
        json_schema_extra = {
            "example": {
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "vendor_id": "VEND-001",
                "status": "open",
                "created_date": "2025-01-15T10:30:00",
                "expected_delivery": "2025-01-20",
                "total_amount": 2300.00,
                "notes": "Urgent order - expedited shipping",
                "lines": [
                    {
                        "line_id": 1,
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_ordered": 100,
                        "unit_price": 10.50,
                        "line_total": 1050.00
                    }
                ]
            }
        }


class POListItem(BaseModel):
    """Simplified PO model for list views."""
    po_id: str
    vendor_name: str
    status: str
    created_date: str
    total_amount: float
    line_count: int = Field(..., description="Number of line items")

    class Config:
        json_schema_extra = {
            "example": {
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "status": "open",
                "created_date": "2025-01-15T10:30:00",
                "total_amount": 2300.00,
                "line_count": 2
            }
        }


# ============================================================================
# ASN MODELS (Part 3)
# ============================================================================

class ASNLineItem(BaseModel):
    """ASN (Advanced Shipment Notice) line item model."""
    line_number: int = Field(..., gt=0, description="Line number (1-based)")
    product_sku: str = Field(..., min_length=1, description="Product SKU/code")
    product_description: str = Field(..., min_length=1, description="Product description")
    quantity_shipped: float = Field(..., gt=0, description="Quantity shipped")

    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "product_sku": "SKU-12345",
                "product_description": "Widget Pro 2000",
                "quantity_shipped": 100
            }
        }


class ASNLineResponse(ASNLineItem):
    """ASN line item response (includes database ID)."""
    line_id: int = Field(..., description="Database line ID")


class CreateASNRequest(BaseModel):
    """Request model for creating a new Advanced Shipment Notice."""
    po_id: str = Field(..., min_length=1, description="Related Purchase Order ID")
    vendor_name: str = Field(..., min_length=1, description="Vendor name")
    ship_date: str = Field(..., description="Ship date (ISO 8601)")
    expected_delivery: Optional[str] = Field(None, description="Expected delivery date (ISO 8601)")
    tracking_number: Optional[str] = Field(None, description="Shipment tracking number")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[ASNLineItem] = Field(..., min_items=1, description="ASN line items")

    class Config:
        json_schema_extra = {
            "example": {
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "ship_date": "2025-01-15",
                "expected_delivery": "2025-01-20",
                "tracking_number": "TRACK-123456",
                "notes": "Shipment via FedEx",
                "lines": [
                    {
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_shipped": 100
                    },
                    {
                        "line_number": 2,
                        "product_sku": "SKU-67890",
                        "product_description": "Gadget Ultra",
                        "quantity_shipped": 50
                    }
                ]
            }
        }


class ASNResponse(BaseModel):
    """ASN response model."""
    asn_id: str = Field(..., description="ASN ID")
    po_id: str = Field(..., description="Related Purchase Order ID")
    vendor_name: str = Field(..., description="Vendor name")
    ship_date: str = Field(..., description="Ship date")
    expected_delivery: Optional[str] = Field(None, description="Expected delivery date")
    status: str = Field(..., description="ASN status")
    tracking_number: Optional[str] = Field(None, description="Shipment tracking number")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[ASNLineResponse] = Field(..., description="ASN line items")

    class Config:
        json_schema_extra = {
            "example": {
                "asn_id": "ASN-2025-001",
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "ship_date": "2025-01-15",
                "expected_delivery": "2025-01-20",
                "status": "created",
                "tracking_number": "TRACK-123456",
                "notes": "Shipment via FedEx",
                "lines": [
                    {
                        "line_id": 1,
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_shipped": 100
                    }
                ]
            }
        }


class ASNListItem(BaseModel):
    """Simplified ASN model for list views."""
    asn_id: str
    po_id: str
    vendor_name: str
    status: str
    ship_date: str
    tracking_number: Optional[str]
    line_count: int = Field(..., description="Number of line items")

    class Config:
        json_schema_extra = {
            "example": {
                "asn_id": "ASN-2025-001",
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "status": "created",
                "ship_date": "2025-01-15",
                "tracking_number": "TRACK-123456",
                "line_count": 2
            }
        }


# ============================================================================
# GOODS RECEIPT MODELS (Part 4)
# ============================================================================

class ReceiptLineItem(BaseModel):
    """Goods Receipt line item model."""
    line_number: int = Field(..., gt=0, description="Line number (1-based)")
    product_sku: str = Field(..., min_length=1, description="Product SKU/code")
    product_description: str = Field(..., min_length=1, description="Product description")
    quantity_received: float = Field(..., gt=0, description="Quantity received")
    condition: Optional[str] = Field("good", description="Condition of goods (good, damaged, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "product_sku": "SKU-12345",
                "product_description": "Widget Pro 2000",
                "quantity_received": 100,
                "condition": "good"
            }
        }


class ReceiptLineResponse(ReceiptLineItem):
    """Goods Receipt line item response (includes database ID)."""
    line_id: int = Field(..., description="Database line ID")


class CreateReceiptRequest(BaseModel):
    """Request model for creating a new Goods Receipt."""
    po_id: str = Field(..., min_length=1, description="Related Purchase Order ID")
    asn_id: Optional[str] = Field(None, description="Related ASN ID (optional)")
    received_date: str = Field(..., description="Receipt date (ISO 8601)")
    warehouse_location: Optional[str] = Field(None, description="Warehouse location")
    received_by: Optional[str] = Field(None, description="Person who received goods")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[ReceiptLineItem] = Field(..., min_items=1, description="Receipt line items")

    class Config:
        json_schema_extra = {
            "example": {
                "po_id": "PO-2025-001",
                "asn_id": "ASN-2025-001",
                "received_date": "2025-01-20",
                "warehouse_location": "DOCK-A",
                "received_by": "John Smith",
                "notes": "All items in good condition",
                "lines": [
                    {
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_received": 100,
                        "condition": "good"
                    },
                    {
                        "line_number": 2,
                        "product_sku": "SKU-67890",
                        "product_description": "Gadget Ultra",
                        "quantity_received": 50,
                        "condition": "good"
                    }
                ]
            }
        }


class ReceiptResponse(BaseModel):
    """Goods Receipt response model."""
    receipt_id: str = Field(..., description="Receipt ID")
    po_id: str = Field(..., description="Related Purchase Order ID")
    asn_id: Optional[str] = Field(None, description="Related ASN ID")
    received_date: str = Field(..., description="Receipt date")
    warehouse_location: Optional[str] = Field(None, description="Warehouse location")
    received_by: Optional[str] = Field(None, description="Person who received goods")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[ReceiptLineResponse] = Field(..., description="Receipt line items")

    class Config:
        json_schema_extra = {
            "example": {
                "receipt_id": "GR-2025-001",
                "po_id": "PO-2025-001",
                "asn_id": "ASN-2025-001",
                "received_date": "2025-01-20",
                "warehouse_location": "DOCK-A",
                "received_by": "John Smith",
                "notes": "All items in good condition",
                "lines": [
                    {
                        "line_id": 1,
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_received": 100,
                        "condition": "good"
                    }
                ]
            }
        }


class ReceiptListItem(BaseModel):
    """Simplified Receipt model for list views."""
    receipt_id: str
    po_id: str
    asn_id: Optional[str]
    received_date: str
    warehouse_location: Optional[str]
    line_count: int = Field(..., description="Number of line items")

    class Config:
        json_schema_extra = {
            "example": {
                "receipt_id": "GR-2025-001",
                "po_id": "PO-2025-001",
                "asn_id": "ASN-2025-001",
                "received_date": "2025-01-20",
                "warehouse_location": "DOCK-A",
                "line_count": 2
            }
        }


# ============================================================================
# INVOICE MODELS (Part 5)
# ============================================================================

class InvoiceLineItem(BaseModel):
    """Vendor Invoice line item model."""
    line_number: int = Field(..., gt=0, description="Line number (1-based)")
    product_sku: str = Field(..., min_length=1, description="Product SKU/code")
    product_description: str = Field(..., min_length=1, description="Product description")
    quantity_invoiced: float = Field(..., gt=0, description="Quantity invoiced")
    unit_price: float = Field(..., gt=0, description="Unit price")
    line_total: Optional[float] = Field(None, description="Line total (auto-calculated)")

    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "product_sku": "SKU-12345",
                "product_description": "Widget Pro 2000",
                "quantity_invoiced": 100,
                "unit_price": 10.50,
                "line_total": 1050.00
            }
        }


class InvoiceLineResponse(InvoiceLineItem):
    """Invoice line item response (includes database ID)."""
    line_id: int = Field(..., description="Database line ID")


class CreateInvoiceRequest(BaseModel):
    """Request model for creating a new Vendor Invoice."""
    invoice_id: str = Field(..., min_length=1, description="Vendor invoice number")
    po_id: str = Field(..., min_length=1, description="Related Purchase Order ID")
    vendor_name: str = Field(..., min_length=1, description="Vendor name")
    invoice_date: str = Field(..., description="Invoice date (ISO 8601)")
    due_date: Optional[str] = Field(None, description="Payment due date (ISO 8601)")
    payment_terms: Optional[str] = Field(None, description="Payment terms (e.g., Net 30)")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[InvoiceLineItem] = Field(..., min_items=1, description="Invoice line items")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-VENDOR-12345",
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "invoice_date": "2025-01-25",
                "due_date": "2025-02-24",
                "payment_terms": "Net 30",
                "notes": "Standard invoice",
                "lines": [
                    {
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_invoiced": 100,
                        "unit_price": 10.50
                    },
                    {
                        "line_number": 2,
                        "product_sku": "SKU-67890",
                        "product_description": "Gadget Ultra",
                        "quantity_invoiced": 50,
                        "unit_price": 25.00
                    }
                ]
            }
        }


class InvoiceResponse(BaseModel):
    """Invoice response model."""
    invoice_id: str = Field(..., description="Vendor invoice number")
    po_id: str = Field(..., description="Related Purchase Order ID")
    vendor_name: str = Field(..., description="Vendor name")
    invoice_date: str = Field(..., description="Invoice date")
    due_date: Optional[str] = Field(None, description="Payment due date")
    total_amount: float = Field(..., description="Total invoice amount")
    status: str = Field(..., description="Invoice status")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    lines: List[InvoiceLineResponse] = Field(..., description="Invoice line items")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-VENDOR-12345",
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "invoice_date": "2025-01-25",
                "due_date": "2025-02-24",
                "total_amount": 2300.00,
                "status": "pending",
                "payment_terms": "Net 30",
                "notes": "Standard invoice",
                "lines": [
                    {
                        "line_id": 1,
                        "line_number": 1,
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "quantity_invoiced": 100,
                        "unit_price": 10.50,
                        "line_total": 1050.00
                    }
                ]
            }
        }


class InvoiceListItem(BaseModel):
    """Simplified Invoice model for list views."""
    invoice_id: str
    po_id: str
    vendor_name: str
    status: str
    invoice_date: str
    total_amount: float
    line_count: int = Field(..., description="Number of line items")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-VENDOR-12345",
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supplies Inc.",
                "status": "pending",
                "invoice_date": "2025-01-25",
                "total_amount": 2300.00,
                "line_count": 2
            }
        }


# ============================================================================
# MATCH MODELS (Part 6)
# ============================================================================

class MatchLineVariance(BaseModel):
    """Variance details for a single line item in 3-way match."""
    product_sku: str = Field(..., description="Product SKU")
    product_description: str = Field(..., description="Product description")

    # PO Quantities
    po_quantity: float = Field(..., description="Quantity ordered (from PO)")
    po_unit_price: float = Field(..., description="Unit price (from PO)")

    # Receipt Quantities
    receipt_quantity: float = Field(..., description="Quantity received (cumulative)")

    # Invoice Quantities
    invoice_quantity: float = Field(..., description="Quantity invoiced")
    invoice_unit_price: float = Field(..., description="Unit price invoiced")

    # Variance Calculations
    price_variance_pct: float = Field(..., description="Price variance percentage")
    price_variance_amount: float = Field(..., description="Price variance amount")
    quantity_variance: float = Field(..., description="Quantity variance (invoice - receipt)")
    quantity_variance_pct: float = Field(..., description="Quantity variance percentage")

    # Match Results
    price_match: bool = Field(..., description="Price within tolerance")
    quantity_match: bool = Field(..., description="Quantity within tolerance")
    line_status: str = Field(..., description="matched or blocked")


class PerformMatchRequest(BaseModel):
    """Request model for performing 3-way match."""
    invoice_id: str = Field(..., min_length=1, description="Invoice ID to match")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-VENDOR-12345"
            }
        }


class MatchResponse(BaseModel):
    """3-Way Match result response."""
    match_id: int = Field(..., description="Match record ID")
    invoice_id: str = Field(..., description="Invoice ID")
    po_id: str = Field(..., description="Purchase Order ID")
    receipt_id: Optional[str] = Field(None, description="Receipt ID (if available)")

    match_status: str = Field(..., description="Overall match status (matched, blocked, partial)")
    match_date: str = Field(..., description="Match execution timestamp")

    total_variance_amount: float = Field(..., description="Total variance amount")

    line_variances: List[MatchLineVariance] = Field(..., description="Line-by-line variance details")

    summary: dict = Field(..., description="Match summary statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "match_id": 1,
                "invoice_id": "INV-VENDOR-12345",
                "po_id": "PO-2025-001",
                "receipt_id": "GR-2025-001",
                "match_status": "matched",
                "match_date": "2025-01-25T10:30:00",
                "total_variance_amount": 0.0,
                "line_variances": [
                    {
                        "product_sku": "SKU-12345",
                        "product_description": "Widget Pro 2000",
                        "po_quantity": 100.0,
                        "po_unit_price": 10.50,
                        "receipt_quantity": 100.0,
                        "invoice_quantity": 100.0,
                        "invoice_unit_price": 10.50,
                        "price_variance_pct": 0.0,
                        "price_variance_amount": 0.0,
                        "quantity_variance": 0.0,
                        "quantity_variance_pct": 0.0,
                        "price_match": True,
                        "quantity_match": True,
                        "line_status": "matched"
                    }
                ],
                "summary": {
                    "total_lines": 2,
                    "matched_lines": 2,
                    "blocked_lines": 0
                }
            }
        }


class MatchListItem(BaseModel):
    """Simplified Match Record for list views."""
    match_id: int
    invoice_id: str
    po_id: str
    receipt_id: Optional[str]
    match_status: str
    match_date: str
    total_variance_amount: float

    class Config:
        json_schema_extra = {
            "example": {
                "match_id": 1,
                "invoice_id": "INV-VENDOR-12345",
                "po_id": "PO-2025-001",
                "receipt_id": "GR-2025-001",
                "match_status": "matched",
                "match_date": "2025-01-25T10:30:00",
                "total_variance_amount": 0.0
            }
        }


# ============================================================================
# EXCEPTION MODELS (Part 7)
# ============================================================================

class CreateExceptionRequest(BaseModel):
    """Request model for manually creating an exception."""
    match_id: int = Field(..., description="Related match record ID")
    invoice_id: str = Field(..., min_length=1, description="Invoice ID")
    po_id: str = Field(..., min_length=1, description="Purchase Order ID")
    exception_type: str = Field(..., description="Type of exception (price_variance, quantity_variance, etc.)")
    severity: str = Field(..., description="Severity level (low, medium, high, critical)")
    product_sku: Optional[str] = Field(None, description="Product SKU (if line-specific)")
    variance_amount: Optional[float] = Field(None, description="Variance amount")
    description: str = Field(..., min_length=1, description="Exception description")

    class Config:
        json_schema_extra = {
            "example": {
                "match_id": 1,
                "invoice_id": "INV-TEST-001",
                "po_id": "PO-2025-001",
                "exception_type": "price_variance",
                "severity": "medium",
                "product_sku": "SKU-12345",
                "variance_amount": 50.00,
                "description": "Price variance exceeds 2% tolerance threshold"
            }
        }


class ResolveExceptionRequest(BaseModel):
    """Request model for resolving an exception."""
    resolution_notes: str = Field(..., min_length=1, description="Resolution notes")
    resolved_by: str = Field(..., min_length=1, description="User who resolved the exception")

    class Config:
        json_schema_extra = {
            "example": {
                "resolution_notes": "Vendor corrected pricing - approved for payment",
                "resolved_by": "john.doe@company.com"
            }
        }


class ExceptionResponse(BaseModel):
    """Exception response model."""
    exception_id: int = Field(..., description="Exception ID")
    match_id: int = Field(..., description="Related match record ID")
    invoice_id: str = Field(..., description="Invoice ID")
    po_id: str = Field(..., description="Purchase Order ID")
    exception_type: str = Field(..., description="Exception type")
    severity: str = Field(..., description="Severity level")
    product_sku: Optional[str] = Field(None, description="Product SKU")
    variance_amount: Optional[float] = Field(None, description="Variance amount")
    description: str = Field(..., description="Exception description")
    status: str = Field(..., description="Exception status (open, in_review, resolved, closed)")
    created_date: str = Field(..., description="Creation timestamp")
    resolved_date: Optional[str] = Field(None, description="Resolution timestamp")
    resolved_by: Optional[str] = Field(None, description="User who resolved")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "exception_id": 1,
                "match_id": 1,
                "invoice_id": "INV-TEST-001",
                "po_id": "PO-2025-001",
                "exception_type": "price_variance",
                "severity": "medium",
                "product_sku": "SKU-12345",
                "variance_amount": 50.00,
                "description": "Price variance exceeds 2% tolerance threshold",
                "status": "open",
                "created_date": "2025-01-25T10:30:00",
                "resolved_date": None,
                "resolved_by": None,
                "resolution_notes": None
            }
        }


class ExceptionListItem(BaseModel):
    """Simplified Exception model for list views."""
    exception_id: int
    invoice_id: str
    po_id: str
    exception_type: str
    severity: str
    status: str
    variance_amount: Optional[float]
    created_date: str

    class Config:
        json_schema_extra = {
            "example": {
                "exception_id": 1,
                "invoice_id": "INV-TEST-001",
                "po_id": "PO-2025-001",
                "exception_type": "price_variance",
                "severity": "medium",
                "status": "open",
                "variance_amount": 50.00,
                "created_date": "2025-01-25T10:30:00"
            }
        }


# ============================================================================
# DASHBOARD MODELS (Part 8)
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    total_pos: int = Field(..., description="Total Purchase Orders")
    total_asns: int = Field(..., description="Total ASNs")
    total_receipts: int = Field(..., description="Total Goods Receipts")
    total_invoices: int = Field(..., description="Total Invoices")
    total_matches: int = Field(..., description="Total Match Records")
    total_exceptions: int = Field(..., description="Total Exceptions")

    # PO Statistics
    pos_by_status: dict = Field(..., description="PO counts by status")

    # Invoice Statistics
    invoices_by_status: dict = Field(..., description="Invoice counts by status")

    # Exception Statistics
    exceptions_by_status: dict = Field(..., description="Exception counts by status")
    exceptions_by_severity: dict = Field(..., description="Exception counts by severity")

    # Financial Statistics
    total_po_amount: float = Field(..., description="Total PO amount")
    total_invoice_amount: float = Field(..., description="Total invoice amount")
    total_variance_amount: float = Field(..., description="Total variance amount")

    class Config:
        json_schema_extra = {
            "example": {
                "total_pos": 10,
                "total_asns": 8,
                "total_receipts": 9,
                "total_invoices": 7,
                "total_matches": 5,
                "total_exceptions": 3,
                "pos_by_status": {"open": 2, "partially_received": 3, "received": 5},
                "invoices_by_status": {"pending": 2, "matched": 3, "blocked": 2},
                "exceptions_by_status": {"open": 2, "resolved": 1},
                "exceptions_by_severity": {"critical": 1, "high": 1, "medium": 1},
                "total_po_amount": 50000.00,
                "total_invoice_amount": 48500.00,
                "total_variance_amount": 1500.00
            }
        }


class POLifecycleStep(BaseModel):
    """Single step in PO lifecycle."""
    step_type: str = Field(..., description="Step type (po, asn, receipt, invoice, match, exception)")
    step_id: str = Field(..., description="Step ID")
    step_date: str = Field(..., description="Step date")
    status: Optional[str] = Field(None, description="Status")
    details: dict = Field(..., description="Additional details")


class POLifecycleResponse(BaseModel):
    """Complete PO lifecycle view."""
    po_id: str = Field(..., description="Purchase Order ID")
    vendor_name: str = Field(..., description="Vendor name")
    total_amount: float = Field(..., description="Total PO amount")
    status: str = Field(..., description="Current PO status")

    # Lifecycle steps
    purchase_order: dict = Field(..., description="PO details")
    asns: List[dict] = Field(..., description="Associated ASNs")
    receipts: List[dict] = Field(..., description="Associated Receipts")
    invoices: List[dict] = Field(..., description="Associated Invoices")
    matches: List[dict] = Field(..., description="Match records")
    exceptions: List[dict] = Field(..., description="Exceptions")

    # Timeline
    timeline: List[POLifecycleStep] = Field(..., description="Chronological timeline")

    class Config:
        json_schema_extra = {
            "example": {
                "po_id": "PO-2025-001",
                "vendor_name": "Acme Supply Co.",
                "total_amount": 2000.00,
                "status": "received",
                "purchase_order": {},
                "asns": [],
                "receipts": [],
                "invoices": [],
                "matches": [],
                "exceptions": [],
                "timeline": []
            }
        }
