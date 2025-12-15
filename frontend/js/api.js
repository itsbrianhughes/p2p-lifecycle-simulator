/**
 * API Client for P2P Lifecycle Simulator
 *
 * This module provides a clean interface for making API calls to the backend.
 * Functions will be added incrementally as each Part is implemented.
 */

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============================================================================
// HEALTH CHECK
// ============================================================================

async function checkHealth() {
    return await apiFetch('/health');
}

// ============================================================================
// PURCHASE ORDER API (Part 2)
// ============================================================================

/**
 * Create a new Purchase Order
 * @param {Object} poData - PO data with vendor_name, vendor_id, lines, etc.
 * @returns {Promise<Object>} Created PO with generated ID
 */
async function createPO(poData) {
    return await apiFetch('/po', {
        method: 'POST',
        body: JSON.stringify(poData)
    });
}

/**
 * List all Purchase Orders
 * @returns {Promise<Array>} Array of PO summary objects
 */
async function listPOs() {
    return await apiFetch('/po');
}

/**
 * Get a specific Purchase Order by ID
 * @param {string} poId - Purchase Order ID (e.g., "PO-2025-001")
 * @returns {Promise<Object>} Complete PO with line items
 */
async function getPO(poId) {
    return await apiFetch(`/po/${poId}`);
}

// ============================================================================
// ASN API (Part 3)
// ============================================================================

/**
 * Create a new Advanced Shipment Notice
 * @param {Object} asnData - ASN data with po_id, vendor_name, ship_date, lines, etc.
 * @returns {Promise<Object>} Created ASN with generated ID
 */
async function createASN(asnData) {
    return await apiFetch('/asn', {
        method: 'POST',
        body: JSON.stringify(asnData)
    });
}

/**
 * List all ASNs
 * @returns {Promise<Array>} Array of ASN summary objects
 */
async function listASNs() {
    return await apiFetch('/asn');
}

/**
 * Get a specific ASN by ID
 * @param {string} asnId - ASN ID (e.g., "ASN-2025-001")
 * @returns {Promise<Object>} Complete ASN with line items
 */
async function getASN(asnId) {
    return await apiFetch(`/asn/${asnId}`);
}

/**
 * Get all ASNs for a specific Purchase Order
 * @param {string} poId - Purchase Order ID (e.g., "PO-2025-001")
 * @returns {Promise<Array>} Array of ASNs for the PO
 */
async function getASNsForPO(poId) {
    return await apiFetch(`/po/${poId}/asn`);
}

// ============================================================================
// GOODS RECEIPT API (Part 4)
// ============================================================================

/**
 * Create a new Goods Receipt
 * @param {Object} receiptData - Receipt data with po_id, received_date, lines, etc.
 * @returns {Promise<Object>} Created Receipt with generated ID
 */
async function createReceipt(receiptData) {
    return await apiFetch('/receipt', {
        method: 'POST',
        body: JSON.stringify(receiptData)
    });
}

/**
 * List all Goods Receipts
 * @returns {Promise<Array>} Array of Receipt summary objects
 */
async function listReceipts() {
    return await apiFetch('/receipt');
}

/**
 * Get a specific Receipt by ID
 * @param {string} receiptId - Receipt ID (e.g., "GR-2025-001")
 * @returns {Promise<Object>} Complete Receipt with line items
 */
async function getReceipt(receiptId) {
    return await apiFetch(`/receipt/${receiptId}`);
}

/**
 * Get all Receipts for a specific Purchase Order
 * @param {string} poId - Purchase Order ID (e.g., "PO-2025-001")
 * @returns {Promise<Array>} Array of Receipts for the PO
 */
async function getReceiptsForPO(poId) {
    return await apiFetch(`/po/${poId}/receipt`);
}

// ============================================================================
// INVOICE API (Part 5)
// ============================================================================

/**
 * Create a new Vendor Invoice
 * @param {Object} invoiceData - Invoice data with invoice_id, po_id, vendor_name, lines, etc.
 * @returns {Promise<Object>} Created Invoice with calculated totals
 */
async function createInvoice(invoiceData) {
    return await apiFetch('/invoice', {
        method: 'POST',
        body: JSON.stringify(invoiceData)
    });
}

/**
 * List all Invoices
 * @returns {Promise<Array>} Array of Invoice summary objects
 */
async function listInvoices() {
    return await apiFetch('/invoice');
}

/**
 * Get a specific Invoice by ID
 * @param {string} invoiceId - Vendor Invoice ID (e.g., "INV-VENDOR-12345")
 * @returns {Promise<Object>} Complete Invoice with line items
 */
async function getInvoice(invoiceId) {
    return await apiFetch(`/invoice/${invoiceId}`);
}

/**
 * Get all Invoices for a specific Purchase Order
 * @param {string} poId - Purchase Order ID (e.g., "PO-2025-001")
 * @returns {Promise<Array>} Array of Invoices for the PO
 */
async function getInvoicesForPO(poId) {
    return await apiFetch(`/po/${poId}/invoice`);
}

// ============================================================================
// MATCH API (Part 6)
// ============================================================================

/**
 * Performs 3-way match for an invoice
 * @param {Object} matchData - Match request with invoice_id
 * @returns {Promise<Object>} Match result with variance details
 */
async function performMatch(matchData) {
    return await apiFetch('/match', {
        method: 'POST',
        body: JSON.stringify(matchData)
    });
}

/**
 * List all match records
 * @returns {Promise<Array>} Array of match record summary objects
 */
async function listMatches() {
    return await apiFetch('/match');
}

/**
 * Get a specific match record by ID
 * @param {number} matchId - Match record ID
 * @returns {Promise<Object>} Complete match record with variance details
 */
async function getMatch(matchId) {
    return await apiFetch(`/match/${matchId}`);
}

/**
 * Get all match records for a specific invoice
 * @param {string} invoiceId - Invoice ID
 * @returns {Promise<Array>} Array of match records for the invoice
 */
async function getMatchesForInvoice(invoiceId) {
    return await apiFetch(`/invoice/${invoiceId}/match`);
}

// ============================================================================
// EXCEPTION API (Part 7)
// ============================================================================

/**
 * Create an exception manually
 * @param {Object} exceptionData - Exception creation data
 * @returns {Promise<Object>} Created exception
 */
async function createException(exceptionData) {
    return await apiFetch('/exception', {
        method: 'POST',
        body: JSON.stringify(exceptionData)
    });
}

/**
 * List all exceptions (optionally filtered by status)
 * @param {string|null} status - Optional status filter
 * @returns {Promise<Array>} Array of exception summary objects
 */
async function listExceptions(status = null) {
    const url = status ? `/exception?status=${status}` : '/exception';
    return await apiFetch(url);
}

/**
 * Get a specific exception by ID
 * @param {number} exceptionId - Exception ID
 * @returns {Promise<Object>} Complete exception with all details
 */
async function getException(exceptionId) {
    return await apiFetch(`/exception/${exceptionId}`);
}

/**
 * Resolve an exception
 * @param {number} exceptionId - Exception ID
 * @param {Object} resolutionData - Resolution data (resolved_by, resolution_notes)
 * @returns {Promise<Object>} Updated exception
 */
async function resolveException(exceptionId, resolutionData) {
    return await apiFetch(`/exception/${exceptionId}/resolve`, {
        method: 'POST',
        body: JSON.stringify(resolutionData)
    });
}

/**
 * Update exception status
 * @param {number} exceptionId - Exception ID
 * @param {string} status - New status (open, in_review, resolved, closed)
 * @returns {Promise<Object>} Success message
 */
async function updateExceptionStatus(exceptionId, status) {
    return await apiFetch(`/exception/${exceptionId}/status?status=${status}`, {
        method: 'PATCH'
    });
}

/**
 * Get all exceptions for a specific match
 * @param {number} matchId - Match record ID
 * @returns {Promise<Array>} Array of exceptions for the match
 */
async function getExceptionsForMatch(matchId) {
    return await apiFetch(`/match/${matchId}/exception`);
}

/**
 * Get all exceptions for a specific invoice
 * @param {string} invoiceId - Invoice ID
 * @returns {Promise<Array>} Array of exceptions for the invoice
 */
async function getExceptionsForInvoice(invoiceId) {
    return await apiFetch(`/invoice/${invoiceId}/exception`);
}

// ============================================================================
// DASHBOARD API (Part 8)
// ============================================================================

/**
 * Get dashboard statistics
 * @returns {Promise<Object>} Dashboard statistics with counts and financial summaries
 */
async function getDashboardStats() {
    return await apiFetch('/dashboard/stats');
}

/**
 * Get complete lifecycle for a Purchase Order
 * @param {string} poId - Purchase Order ID (e.g., "PO-2025-001")
 * @returns {Promise<Object>} Complete PO lifecycle with all associated entities and timeline
 */
async function getPOLifecycle(poId) {
    return await apiFetch(`/dashboard/lifecycle/${poId}`);
}

// Alias for consistency with dashboard.html
async function listPurchaseOrders() {
    return await listPOs();
}
