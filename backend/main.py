"""
FastAPI Application for P2P Lifecycle Simulator

Main application entry point with:
- FastAPI app initialization
- Database initialization
- API route registration
- CORS configuration
- Static file serving
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from backend.database import init_database
from backend.config import (
    API_HOST,
    API_PORT,
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION
)
from backend.models import (
    CreatePORequest, PurchaseOrderResponse, POListItem,
    CreateASNRequest, ASNResponse, ASNListItem,
    CreateReceiptRequest, ReceiptResponse, ReceiptListItem,
    CreateInvoiceRequest, InvoiceResponse, InvoiceListItem,
    PerformMatchRequest, MatchResponse, MatchListItem,
    CreateExceptionRequest, ResolveExceptionRequest, ExceptionResponse, ExceptionListItem,
    DashboardStats, POLifecycleResponse
)
from backend.services import po_service, asn_service, receipt_service, invoice_service, match_engine, exception_service, dashboard_service


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# CORS MIDDLEWARE (for local development)
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize database on application startup.

    This creates all tables if they don't exist.
    """
    print("\n" + "="*60)
    print("P2P LIFECYCLE SIMULATOR - STARTING UP")
    print("="*60)
    init_database()
    print("="*60)
    print(f"API Documentation: http://{API_HOST}:{API_PORT}/docs")
    print(f"Frontend: http://{API_HOST}:{API_PORT}/")
    print("="*60 + "\n")


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status and version information
    """
    return {
        "status": "healthy",
        "service": "P2P Lifecycle Simulator",
        "version": API_VERSION
    }


# ============================================================================
# API ROUTES (to be added incrementally)
# ============================================================================

# Part 2: Purchase Order Routes
# ============================================================================

@app.post("/api/po", response_model=PurchaseOrderResponse, status_code=201)
async def create_po(request: CreatePORequest):
    """
    Create a new Purchase Order.

    Business Logic:
    - Validates vendor and line item data
    - Generates unique PO ID (format: PO-YYYY-NNN)
    - Calculates line and document totals
    - Sets initial status to 'open'

    Args:
        request: Purchase Order creation request

    Returns:
        Created Purchase Order with ID and calculated totals
    """
    try:
        po = po_service.create_purchase_order(request)
        return po
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PO: {str(e)}")


@app.get("/api/po", response_model=list[POListItem])
async def list_pos():
    """
    List all Purchase Orders with summary information.

    Returns:
        List of POs with basic info (no line items)
    """
    try:
        pos = po_service.list_purchase_orders()
        return pos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve POs: {str(e)}")


@app.get("/api/po/{po_id}", response_model=PurchaseOrderResponse)
async def get_po(po_id: str):
    """
    Get a specific Purchase Order by ID with all line items.

    Args:
        po_id: Purchase Order ID (e.g., "PO-2025-001")

    Returns:
        Complete Purchase Order details including all line items
    """
    try:
        po = po_service.get_purchase_order(po_id)
        if not po:
            raise HTTPException(status_code=404, detail=f"Purchase Order {po_id} not found")
        return po
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve PO: {str(e)}")


# Part 3: Advanced Shipment Notice (ASN) Routes
# ============================================================================

@app.post("/api/asn", response_model=ASNResponse, status_code=201)
async def create_asn(request: CreateASNRequest):
    """
    Create a new Advanced Shipment Notice (ASN).

    Business Logic:
    - Validates that referenced PO exists
    - Validates shipment data and line items
    - Generates unique ASN ID (format: ASN-YYYY-NNN)
    - Optionally validates quantities against PO
    - Sets initial status to 'created'

    Args:
        request: ASN creation request

    Returns:
        Created ASN with ID and line items
    """
    try:
        asn = asn_service.create_asn(request)
        return asn
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ASN: {str(e)}")


@app.get("/api/asn", response_model=list[ASNListItem])
async def list_asns():
    """
    List all Advanced Shipment Notices with summary information.

    Returns:
        List of ASNs with basic info (no line items)
    """
    try:
        asns = asn_service.list_asns()
        return asns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ASNs: {str(e)}")


@app.get("/api/asn/{asn_id}", response_model=ASNResponse)
async def get_asn(asn_id: str):
    """
    Get a specific ASN by ID with all line items.

    Args:
        asn_id: ASN ID (e.g., "ASN-2025-001")

    Returns:
        Complete ASN details including all line items
    """
    try:
        asn = asn_service.get_asn(asn_id)
        if not asn:
            raise HTTPException(status_code=404, detail=f"ASN {asn_id} not found")
        return asn
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ASN: {str(e)}")


@app.get("/api/po/{po_id}/asn", response_model=list[ASNListItem])
async def get_asns_for_po(po_id: str):
    """
    Get all ASNs for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID (e.g., "PO-2025-001")

    Returns:
        List of ASNs associated with the PO
    """
    try:
        asns = asn_service.get_asns_by_po(po_id)
        return asns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ASNs for PO: {str(e)}")


# Part 4: Goods Receipt Routes
# ============================================================================

@app.post("/api/receipt", response_model=ReceiptResponse, status_code=201)
async def create_receipt(request: CreateReceiptRequest):
    """
    Create a new Goods Receipt.

    Business Logic:
    - Validates that referenced PO exists
    - Optionally validates that ASN exists (if provided)
    - Generates unique Receipt ID (format: GR-YYYY-NNN)
    - Updates PO status based on cumulative received quantities
      * partially_received if some items received
      * received if all items fully received

    Args:
        request: Receipt creation request

    Returns:
        Created Receipt with ID and line items
    """
    try:
        receipt = receipt_service.create_receipt(request)
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Receipt: {str(e)}")


@app.get("/api/receipt", response_model=list[ReceiptListItem])
async def list_receipts():
    """
    List all Goods Receipts with summary information.

    Returns:
        List of Receipts with basic info (no line items)
    """
    try:
        receipts = receipt_service.list_receipts()
        return receipts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Receipts: {str(e)}")


@app.get("/api/receipt/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(receipt_id: str):
    """
    Get a specific Receipt by ID with all line items.

    Args:
        receipt_id: Receipt ID (e.g., "GR-2025-001")

    Returns:
        Complete Receipt details including all line items
    """
    try:
        receipt = receipt_service.get_receipt(receipt_id)
        if not receipt:
            raise HTTPException(status_code=404, detail=f"Receipt {receipt_id} not found")
        return receipt
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Receipt: {str(e)}")


@app.get("/api/po/{po_id}/receipt", response_model=list[ReceiptListItem])
async def get_receipts_for_po(po_id: str):
    """
    Get all Receipts for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID (e.g., "PO-2025-001")

    Returns:
        List of Receipts associated with the PO
    """
    try:
        receipts = receipt_service.get_receipts_by_po(po_id)
        return receipts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Receipts for PO: {str(e)}")


# Part 5: Invoice Routes
# ============================================================================

@app.post("/api/invoice", response_model=InvoiceResponse, status_code=201)
async def create_invoice(request: CreateInvoiceRequest):
    """
    Create a new Vendor Invoice.

    Business Logic:
    - Validates that referenced PO exists
    - Uses vendor's invoice number as ID (not auto-generated)
    - Validates that invoice_id doesn't already exist
    - Calculates line and document totals
    - Sets initial status to 'pending'
    - NOTE: 3-way matching will be triggered in Part 6

    Args:
        request: Invoice creation request

    Returns:
        Created Invoice with calculated totals
    """
    try:
        invoice = invoice_service.create_invoice(request)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Invoice: {str(e)}")


@app.get("/api/invoice", response_model=list[InvoiceListItem])
async def list_invoices():
    """
    List all Invoices with summary information.

    Returns:
        List of Invoices with basic info (no line items)
    """
    try:
        invoices = invoice_service.list_invoices()
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Invoices: {str(e)}")


@app.get("/api/invoice/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str):
    """
    Get a specific Invoice by ID with all line items.

    Args:
        invoice_id: Vendor Invoice ID (e.g., "INV-VENDOR-12345")

    Returns:
        Complete Invoice details including all line items
    """
    try:
        invoice = invoice_service.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Invoice: {str(e)}")


@app.get("/api/po/{po_id}/invoice", response_model=list[InvoiceListItem])
async def get_invoices_for_po(po_id: str):
    """
    Get all Invoices for a specific Purchase Order.

    Args:
        po_id: Purchase Order ID (e.g., "PO-2025-001")

    Returns:
        List of Invoices associated with the PO
    """
    try:
        invoices = invoice_service.get_invoices_by_po(po_id)
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Invoices for PO: {str(e)}")


# Part 6: Match Engine Routes
# ============================================================================

@app.post("/api/match", response_model=MatchResponse, status_code=201)
async def perform_match(request: PerformMatchRequest):
    """
    Performs 3-way match for an invoice.

    Business Logic:
    - Compares Invoice vs PO for price variance (±2% tolerance)
    - Compares Invoice vs cumulative Receipts for quantity variance (±5% tolerance)
    - Creates match record with detailed variance analysis
    - Updates invoice status to 'matched' or 'blocked'
    - Returns comprehensive variance report

    Match Status:
    - matched: All lines within tolerance
    - blocked: One or more lines outside tolerance

    Args:
        request: Match request with invoice_id

    Returns:
        Detailed match result with line-by-line variances
    """
    try:
        match_result = match_engine.perform_three_way_match(request)
        return match_result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match failed: {str(e)}")


@app.get("/api/match", response_model=list[MatchListItem])
async def list_matches():
    """
    Lists all match records.

    Returns:
        List of all match records ordered by match date (descending)
    """
    try:
        matches = match_engine.list_matches()
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve matches: {str(e)}")


@app.get("/api/match/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int):
    """
    Gets a specific match record by ID.

    Args:
        match_id: Match record ID

    Returns:
        Detailed match result with all variance information
    """
    try:
        match = match_engine.get_match(match_id)
        if not match:
            raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")
        return match
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve match: {str(e)}")


@app.get("/api/invoice/{invoice_id}/match", response_model=list[MatchListItem])
async def get_matches_for_invoice(invoice_id: str):
    """
    Gets all match records for a specific invoice.

    Args:
        invoice_id: Invoice ID

    Returns:
        List of match records for the invoice
    """
    try:
        matches = match_engine.get_matches_for_invoice(invoice_id)
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve matches for invoice: {str(e)}")


# Part 7: Exception Routes
# ============================================================================

@app.post("/api/exception", response_model=ExceptionResponse, status_code=201)
async def create_exception(request: CreateExceptionRequest):
    """
    Manually creates an exception.

    Note: Exceptions are automatically created by the match engine for blocked lines.
    This endpoint allows manual exception creation for edge cases.

    Args:
        request: Exception creation request

    Returns:
        Created exception
    """
    try:
        exception = exception_service.create_exception(request)
        return exception
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create exception: {str(e)}")


@app.get("/api/exception", response_model=list[ExceptionListItem])
async def list_exceptions(status: str = None):
    """
    Lists all exceptions, optionally filtered by status.

    Query Parameters:
        status: Optional status filter (open, in_review, resolved, closed)

    Returns:
        List of all exceptions ordered by creation date (descending)
    """
    try:
        exceptions = exception_service.list_exceptions(status_filter=status)
        return exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve exceptions: {str(e)}")


@app.get("/api/exception/{exception_id}", response_model=ExceptionResponse)
async def get_exception(exception_id: int):
    """
    Gets a specific exception by ID.

    Args:
        exception_id: Exception ID

    Returns:
        Exception with all details
    """
    try:
        exception = exception_service.get_exception(exception_id)
        if not exception:
            raise HTTPException(status_code=404, detail=f"Exception not found: {exception_id}")
        return exception
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve exception: {str(e)}")


@app.post("/api/exception/{exception_id}/resolve", response_model=ExceptionResponse)
async def resolve_exception(exception_id: int, request: ResolveExceptionRequest):
    """
    Resolves an exception.

    Args:
        exception_id: Exception ID
        request: Resolution request with notes and user

    Returns:
        Updated exception with resolved status
    """
    try:
        exception = exception_service.resolve_exception(exception_id, request)
        return exception
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve exception: {str(e)}")


@app.patch("/api/exception/{exception_id}/status")
async def update_exception_status(exception_id: int, status: str):
    """
    Updates exception status.

    Args:
        exception_id: Exception ID
        status: New status (open, in_review, resolved, closed)

    Returns:
        Success message
    """
    try:
        success = exception_service.update_exception_status(exception_id, status)
        if not success:
            raise HTTPException(status_code=404, detail=f"Exception not found: {exception_id}")
        return {"success": True, "message": f"Exception {exception_id} status updated to {status}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update exception status: {str(e)}")


@app.get("/api/match/{match_id}/exception", response_model=list[ExceptionListItem])
async def get_exceptions_for_match(match_id: int):
    """
    Gets all exceptions for a specific match.

    Args:
        match_id: Match record ID

    Returns:
        List of exceptions for the match
    """
    try:
        exceptions = exception_service.get_exceptions_for_match(match_id)
        return exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve exceptions for match: {str(e)}")


@app.get("/api/invoice/{invoice_id}/exception", response_model=list[ExceptionListItem])
async def get_exceptions_for_invoice(invoice_id: str):
    """
    Gets all exceptions for a specific invoice.

    Args:
        invoice_id: Invoice ID

    Returns:
        List of exceptions for the invoice
    """
    try:
        exceptions = exception_service.get_exceptions_for_invoice(invoice_id)
        return exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve exceptions for invoice: {str(e)}")


# Part 8: Dashboard and Lifecycle Routes
# ============================================================================

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Get aggregate dashboard statistics.

    Returns comprehensive statistics including:
    - Total counts for all P2P entities (POs, ASNs, Receipts, Invoices, Matches, Exceptions)
    - Status breakdowns for POs, Invoices, and Exceptions
    - Severity breakdown for Exceptions
    - Financial totals (PO amount, Invoice amount, Variance amount)

    Returns:
        Dashboard statistics with counts and financial summaries
    """
    try:
        stats = dashboard_service.get_dashboard_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard statistics: {str(e)}")


@app.get("/api/dashboard/lifecycle/{po_id}", response_model=POLifecycleResponse)
async def get_po_lifecycle(po_id: str):
    """
    Get complete lifecycle view for a Purchase Order.

    Provides end-to-end tracking of a PO including:
    - Purchase Order details
    - All associated ASNs
    - All Goods Receipts
    - All Vendor Invoices
    - All Match records
    - All Exceptions
    - Chronological timeline of all events

    Args:
        po_id: Purchase Order ID (e.g., "PO-2025-001")

    Returns:
        Complete PO lifecycle with all associated entities and timeline
    """
    try:
        lifecycle = dashboard_service.get_po_lifecycle(po_id)
        if not lifecycle:
            raise HTTPException(status_code=404, detail=f"Purchase Order {po_id} not found")
        return lifecycle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve PO lifecycle: {str(e)}")


# ============================================================================
# STATIC FILE SERVING (Frontend)
# ============================================================================

# Serve static frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    """
    Serve the main frontend page.

    Returns:
        index.html from frontend directory
    """
    return FileResponse("frontend/index.html")


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True  # Auto-reload on code changes (development only)
    )
