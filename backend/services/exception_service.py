"""
Exception Management Service - Business Logic

This module handles exception detection, creation, and management:
- Automatically creates exceptions from blocked match results
- Manual exception creation
- Exception status management (open, in_review, resolved, closed)
- Exception resolution tracking
- Exception queries and reporting
"""

from typing import Optional, List
from datetime import datetime

from backend.database import db
from backend.models import (
    CreateExceptionRequest,
    ResolveExceptionRequest,
    ExceptionResponse,
    ExceptionListItem,
    MatchLineVariance
)


# ============================================================================
# EXCEPTION CREATION (Automatic from Match Engine)
# ============================================================================

def create_exceptions_from_match(
    match_id: int,
    invoice_id: str,
    po_id: str,
    line_variances: List[MatchLineVariance]
) -> List[int]:
    """
    Automatically creates exceptions for blocked line items.

    Called by match engine when variances exceed tolerance.

    Args:
        match_id: Match record ID
        invoice_id: Invoice ID
        po_id: Purchase Order ID
        line_variances: List of line variances from match

    Returns:
        List of created exception IDs
    """
    exception_ids = []

    for variance in line_variances:
        # Only create exceptions for blocked lines
        if variance.line_status != "blocked":
            continue

        # Determine exception type and severity
        exceptions_to_create = []

        # Price variance exception
        if not variance.price_match:
            exception_type = "price_variance"
            severity = _determine_severity(abs(variance.price_variance_pct), "price")
            description = (
                f"Price variance of {variance.price_variance_pct:.2f}% "
                f"(${abs(variance.price_variance_amount):.2f}) exceeds 2% tolerance. "
                f"PO price: ${variance.po_unit_price:.2f}, "
                f"Invoice price: ${variance.invoice_unit_price:.2f}"
            )
            exceptions_to_create.append((exception_type, severity, variance.price_variance_amount, description))

        # Quantity variance exception
        if not variance.quantity_match:
            exception_type = "quantity_variance"
            severity = _determine_severity(abs(variance.quantity_variance_pct), "quantity")
            description = (
                f"Quantity variance of {variance.quantity_variance_pct:.2f}% "
                f"({abs(variance.quantity_variance):.0f} units) exceeds 5% tolerance. "
                f"Received: {variance.receipt_quantity:.0f}, "
                f"Invoiced: {variance.invoice_quantity:.0f}"
            )
            exceptions_to_create.append((exception_type, severity, variance.quantity_variance, description))

        # Create exceptions
        for exc_type, sev, var_amt, desc in exceptions_to_create:
            exc_id = _create_exception_record(
                match_id=match_id,
                invoice_id=invoice_id,
                po_id=po_id,
                exception_type=exc_type,
                severity=sev,
                product_sku=variance.product_sku,
                variance_amount=var_amt,
                description=desc
            )
            exception_ids.append(exc_id)

    return exception_ids


def _determine_severity(variance_pct: float, variance_type: str) -> str:
    """
    Determines exception severity based on variance percentage.

    Args:
        variance_pct: Variance percentage (absolute value)
        variance_type: 'price' or 'quantity'

    Returns:
        Severity level: low, medium, high, critical
    """
    if variance_type == "price":
        # Price variance thresholds
        if variance_pct <= 5:
            return "low"
        elif variance_pct <= 10:
            return "medium"
        elif variance_pct <= 20:
            return "high"
        else:
            return "critical"
    else:
        # Quantity variance thresholds
        if variance_pct <= 10:
            return "low"
        elif variance_pct <= 20:
            return "medium"
        elif variance_pct <= 50:
            return "high"
        else:
            return "critical"


# ============================================================================
# MANUAL EXCEPTION CREATION
# ============================================================================

def create_exception(request: CreateExceptionRequest) -> ExceptionResponse:
    """
    Manually creates an exception.

    Args:
        request: Exception creation request

    Returns:
        Created exception

    Raises:
        ValueError: If validation fails
    """
    # Validate exception type
    valid_types = ["price_variance", "quantity_variance", "missing_receipt", "missing_po", "other"]
    if request.exception_type not in valid_types:
        raise ValueError(f"Invalid exception type. Must be one of: {', '.join(valid_types)}")

    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if request.severity not in valid_severities:
        raise ValueError(f"Invalid severity. Must be one of: {', '.join(valid_severities)}")

    # Create exception
    exception_id = _create_exception_record(
        match_id=request.match_id,
        invoice_id=request.invoice_id,
        po_id=request.po_id,
        exception_type=request.exception_type,
        severity=request.severity,
        product_sku=request.product_sku,
        variance_amount=request.variance_amount,
        description=request.description
    )

    # Retrieve and return created exception
    exception = get_exception(exception_id)
    if not exception:
        raise ValueError(f"Failed to retrieve created exception: {exception_id}")

    return exception


def _create_exception_record(
    match_id: int,
    invoice_id: str,
    po_id: str,
    exception_type: str,
    severity: str,
    product_sku: Optional[str],
    variance_amount: Optional[float],
    description: str
) -> int:
    """
    Creates an exception record in the database.

    Args:
        match_id: Match record ID
        invoice_id: Invoice ID
        po_id: Purchase Order ID
        exception_type: Exception type
        severity: Severity level
        product_sku: Product SKU (optional)
        variance_amount: Variance amount (optional)
        description: Exception description

    Returns:
        exception_id: Database ID of created exception
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO exceptions (
                match_id, po_id, invoice_id, product_sku,
                exception_type, severity, variance_amount,
                description, status, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            po_id,
            invoice_id,
            product_sku,
            exception_type,
            severity,
            variance_amount,
            description,
            "open",
            datetime.utcnow().isoformat()
        ))

        exception_id = cursor.lastrowid

    return exception_id


# ============================================================================
# EXCEPTION RESOLUTION
# ============================================================================

def resolve_exception(exception_id: int, request: ResolveExceptionRequest) -> ExceptionResponse:
    """
    Resolves an exception.

    Args:
        exception_id: Exception ID
        request: Resolution request with notes and user

    Returns:
        Updated exception

    Raises:
        ValueError: If exception not found or already resolved
    """
    # Check if exception exists
    exception = get_exception(exception_id)
    if not exception:
        raise ValueError(f"Exception not found: {exception_id}")

    # Check if already resolved
    if exception.status == "resolved":
        raise ValueError(f"Exception already resolved: {exception_id}")

    # Update exception
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE exceptions
            SET status = ?,
                resolved_date = ?,
                resolved_by = ?,
                resolution_notes = ?
            WHERE exception_id = ?
        """, (
            "resolved",
            datetime.utcnow().isoformat(),
            request.resolved_by,
            request.resolution_notes,
            exception_id
        ))

    # Return updated exception
    updated_exception = get_exception(exception_id)
    if not updated_exception:
        raise ValueError(f"Failed to retrieve updated exception: {exception_id}")

    return updated_exception


def update_exception_status(exception_id: int, new_status: str) -> bool:
    """
    Updates exception status.

    Args:
        exception_id: Exception ID
        new_status: New status (open, in_review, resolved, closed)

    Returns:
        True if updated successfully

    Raises:
        ValueError: If invalid status
    """
    valid_statuses = ["open", "in_review", "resolved", "closed"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE exceptions
            SET status = ?
            WHERE exception_id = ?
        """, (new_status, exception_id))

        return cursor.rowcount > 0


# ============================================================================
# QUERY OPERATIONS
# ============================================================================

def get_exception(exception_id: int) -> Optional[ExceptionResponse]:
    """
    Gets an exception by ID.

    Args:
        exception_id: Exception ID

    Returns:
        ExceptionResponse or None if not found
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT exception_id, match_id, po_id, invoice_id, product_sku,
                   exception_type, severity, variance_amount, description,
                   status, created_date, resolved_date, resolved_by, resolution_notes
            FROM exceptions
            WHERE exception_id = ?
        """, (exception_id,))

        result = cursor.fetchone()
        if not result:
            return None

        return ExceptionResponse(
            exception_id=result[0],
            match_id=result[1],
            po_id=result[2],
            invoice_id=result[3],
            product_sku=result[4],
            exception_type=result[5],
            severity=result[6],
            variance_amount=result[7],
            description=result[8],
            status=result[9],
            created_date=result[10],
            resolved_date=result[11],
            resolved_by=result[12],
            resolution_notes=result[13]
        )


def list_exceptions(status_filter: Optional[str] = None) -> List[ExceptionListItem]:
    """
    Lists all exceptions, optionally filtered by status.

    Args:
        status_filter: Optional status to filter by (open, in_review, resolved, closed)

    Returns:
        List of ExceptionListItem
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        if status_filter:
            cursor.execute("""
                SELECT exception_id, po_id, invoice_id, exception_type,
                       severity, variance_amount, status, created_date
                FROM exceptions
                WHERE status = ?
                ORDER BY created_date DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT exception_id, po_id, invoice_id, exception_type,
                       severity, variance_amount, status, created_date
                FROM exceptions
                ORDER BY created_date DESC
            """)

        results = cursor.fetchall()

        exceptions = []
        for row in results:
            exceptions.append(ExceptionListItem(
                exception_id=row[0],
                po_id=row[1],
                invoice_id=row[2],
                exception_type=row[3],
                severity=row[4],
                variance_amount=row[5],
                status=row[6],
                created_date=row[7]
            ))

        return exceptions


def get_exceptions_for_match(match_id: int) -> List[ExceptionListItem]:
    """
    Gets all exceptions for a specific match.

    Args:
        match_id: Match record ID

    Returns:
        List of ExceptionListItem
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT exception_id, po_id, invoice_id, exception_type,
                   severity, variance_amount, status, created_date
            FROM exceptions
            WHERE match_id = ?
            ORDER BY created_date DESC
        """, (match_id,))

        results = cursor.fetchall()

        exceptions = []
        for row in results:
            exceptions.append(ExceptionListItem(
                exception_id=row[0],
                po_id=row[1],
                invoice_id=row[2],
                exception_type=row[3],
                severity=row[4],
                variance_amount=row[5],
                status=row[6],
                created_date=row[7]
            ))

        return exceptions


def get_exceptions_for_invoice(invoice_id: str) -> List[ExceptionListItem]:
    """
    Gets all exceptions for a specific invoice.

    Args:
        invoice_id: Invoice ID

    Returns:
        List of ExceptionListItem
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT exception_id, po_id, invoice_id, exception_type,
                   severity, variance_amount, status, created_date
            FROM exceptions
            WHERE invoice_id = ?
            ORDER BY created_date DESC
        """, (invoice_id,))

        results = cursor.fetchall()

        exceptions = []
        for row in results:
            exceptions.append(ExceptionListItem(
                exception_id=row[0],
                po_id=row[1],
                invoice_id=row[2],
                exception_type=row[3],
                severity=row[4],
                variance_amount=row[5],
                status=row[6],
                created_date=row[7]
            ))

        return exceptions
