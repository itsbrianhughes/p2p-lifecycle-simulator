/**
 * Shared UI Utilities for P2P Lifecycle Simulator
 *
 * Common functions for:
 * - Date formatting
 * - Currency formatting
 * - Status badges
 * - Alert messages
 * - Table rendering
 */

// ============================================================================
// DATE FORMATTING
// ============================================================================

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================================================
// CURRENCY FORMATTING
// ============================================================================

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// ============================================================================
// PERCENTAGE FORMATTING
// ============================================================================

function formatPercentage(value) {
    if (value === null || value === undefined) return '0.00%';
    return `${value.toFixed(2)}%`;
}

// ============================================================================
// STATUS BADGES
// ============================================================================

function getStatusBadgeClass(status) {
    const statusClasses = {
        // PO statuses
        'open': 'bg-blue-100 text-blue-800',
        'partially_received': 'bg-yellow-100 text-yellow-800',
        'received': 'bg-green-100 text-green-800',
        'closed': 'bg-gray-100 text-gray-800',

        // Invoice statuses
        'pending': 'bg-yellow-100 text-yellow-800',
        'matched': 'bg-green-100 text-green-800',
        'blocked': 'bg-red-100 text-red-800',
        'approved': 'bg-green-100 text-green-800',
        'paid': 'bg-gray-100 text-gray-800',

        // Exception statuses
        'under_review': 'bg-yellow-100 text-yellow-800',
        'resolved': 'bg-green-100 text-green-800',
        'waived': 'bg-blue-100 text-blue-800'
    };

    return statusClasses[status] || 'bg-gray-100 text-gray-800';
}

function createStatusBadge(status) {
    const classes = getStatusBadgeClass(status);
    const displayText = status.replace(/_/g, ' ').toUpperCase();
    return `<span class="px-2 py-1 text-xs font-semibold rounded ${classes}">${displayText}</span>`;
}

// ============================================================================
// ALERT MESSAGES
// ============================================================================

function showAlert(message, type = 'info') {
    const alertColors = {
        'success': 'bg-green-100 border-green-400 text-green-700',
        'error': 'bg-red-100 border-red-400 text-red-700',
        'warning': 'bg-yellow-100 border-yellow-400 text-yellow-700',
        'info': 'bg-blue-100 border-blue-400 text-blue-700'
    };

    const color = alertColors[type] || alertColors.info;

    const alertHtml = `
        <div class="border px-4 py-3 rounded relative mb-4 ${color}" role="alert">
            <span class="block sm:inline">${message}</span>
        </div>
    `;

    // Insert at top of main container
    const container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = container.querySelector('[role="alert"]');
            if (alert) alert.remove();
        }, 5000);
    }
}

// ============================================================================
// LOADING SPINNER
// ============================================================================

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="flex justify-center items-center py-8">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        `;
    }
}

// ============================================================================
// TABLE HELPERS
// ============================================================================

function createEmptyState(message) {
    return `
        <div class="text-center py-8 text-gray-500">
            <p>${message}</p>
        </div>
    `;
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

function validateRequired(value, fieldName) {
    if (!value || value.toString().trim() === '') {
        throw new Error(`${fieldName} is required`);
    }
}

function validatePositiveNumber(value, fieldName) {
    if (value <= 0) {
        throw new Error(`${fieldName} must be greater than 0`);
    }
}
