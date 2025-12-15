"""
Shared utility functions for P2P Lifecycle Simulator

This module contains helper functions used across multiple services:
- Date/time formatting
- ID generation
- Data validation
- Common calculations
"""

from datetime import datetime
from typing import Optional


# ============================================================================
# DATE/TIME UTILITIES
# ============================================================================

def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO 8601 format.

    Returns:
        Current datetime as ISO 8601 string (e.g., "2024-01-15T14:30:00")
    """
    return datetime.now().isoformat()


def format_date(date_string: Optional[str]) -> Optional[str]:
    """
    Format a date string to ISO 8601 format.

    Args:
        date_string: Input date string (various formats accepted)

    Returns:
        ISO 8601 formatted date string, or None if input is None
    """
    if not date_string:
        return None

    try:
        # If already in ISO format, return as-is
        if "T" in date_string:
            return date_string

        # Try to parse and convert to ISO
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        # If parsing fails, return original string
        return date_string


# ============================================================================
# ID GENERATION
# ============================================================================

def generate_document_id(prefix: str, existing_ids: list = None) -> str:
    """
    Generate a unique document ID with format: PREFIX-YYYY-NNN

    Args:
        prefix: Document type prefix (e.g., "PO", "ASN", "GR", "INV")
        existing_ids: List of existing IDs (to avoid collisions)

    Returns:
        Unique document ID (e.g., "PO-2024-001")

    Example:
        >>> generate_document_id("PO", ["PO-2024-001", "PO-2024-002"])
        "PO-2024-003"
    """
    current_year = datetime.now().year
    base_id = f"{prefix}-{current_year}"

    # If no existing IDs provided, start with 001
    if not existing_ids:
        return f"{base_id}-001"

    # Find highest sequence number for current year
    max_sequence = 0
    for existing_id in existing_ids:
        if existing_id.startswith(base_id):
            try:
                # Extract sequence number (e.g., "001" from "PO-2024-001")
                sequence = int(existing_id.split("-")[-1])
                max_sequence = max(max_sequence, sequence)
            except (ValueError, IndexError):
                continue

    # Increment and format with leading zeros
    next_sequence = max_sequence + 1
    return f"{base_id}-{next_sequence:03d}"


# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_positive_number(value: float, field_name: str) -> None:
    """
    Validate that a number is positive.

    Args:
        value: Number to validate
        field_name: Name of field (for error messages)

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")


def validate_non_negative_number(value: float, field_name: str) -> None:
    """
    Validate that a number is non-negative.

    Args:
        value: Number to validate
        field_name: Name of field (for error messages)

    Raises:
        ValueError: If value is negative
    """
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")


def validate_required_field(value: any, field_name: str) -> None:
    """
    Validate that a required field is not None or empty.

    Args:
        value: Value to validate
        field_name: Name of field (for error messages)

    Raises:
        ValueError: If value is None or empty string
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field_name} is required")


# ============================================================================
# CALCULATION UTILITIES
# ============================================================================

def calculate_line_total(quantity: float, unit_price: float) -> float:
    """
    Calculate line total amount.

    Args:
        quantity: Item quantity
        unit_price: Price per unit

    Returns:
        Line total (quantity × unit_price) rounded to 2 decimal places
    """
    return round(quantity * unit_price, 2)


def calculate_document_total(line_totals: list) -> float:
    """
    Calculate total amount for a document from line totals.

    Args:
        line_totals: List of line total amounts

    Returns:
        Document total (sum of all line totals) rounded to 2 decimal places
    """
    return round(sum(line_totals), 2)


# ============================================================================
# DATA FORMATTING
# ============================================================================

def format_currency(amount: float) -> str:
    """
    Format amount as currency string.

    Args:
        amount: Numeric amount

    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage string.

    Args:
        value: Numeric percentage (e.g., 2.5 for 2.5%)

    Returns:
        Formatted percentage string (e.g., "2.50%")
    """
    return f"{value:.2f}%"


# ============================================================================
# RESPONSE UTILITIES
# ============================================================================

def create_success_response(data: any, message: str = "Success") -> dict:
    """
    Create standardized success response.

    Args:
        data: Response data
        message: Success message

    Returns:
        Standardized success response dictionary
    """
    return {
        "success": True,
        "message": message,
        "data": data
    }


def create_error_response(error: str, details: any = None) -> dict:
    """
    Create standardized error response.

    Args:
        error: Error message
        details: Additional error details

    Returns:
        Standardized error response dictionary
    """
    response = {
        "success": False,
        "error": error
    }

    if details:
        response["details"] = details

    return response
