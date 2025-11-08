/**
 * Utility functions for Multi-Agent RAG RPG UI
 */

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type: success, error, warning, info
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toastContainer');
    const toastId = `toast-${Date.now()}`;

    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-secondary';

    const iconClass = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    }[type] || 'fa-info-circle';

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas ${iconClass} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: duration });
    toast.show();

    // Remove from DOM after hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Format a timestamp as a readable date/time string
 * @param {string|Date} timestamp - Timestamp to format
 * @returns {string} Formatted date/time string
 */
function formatTimestamp(timestamp) {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleString();
}

/**
 * Format seconds as HH:MM:SS
 * @param {number} seconds - Seconds to format
 * @returns {string} Formatted time string
 */
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Format bytes as human-readable size
 * @param {number} bytes - Number of bytes
 * @returns {string} Formatted size string
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Truncate string with ellipsis
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated string
 */
function truncate(str, maxLength) {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
}

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Generate star rating HTML
 * @param {number} rating - Rating value (1-5)
 * @returns {string} HTML string for star rating
 */
function generateStarRating(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<i class="fas fa-star text-warning"></i>';
        } else {
            stars += '<i class="far fa-star text-warning"></i>';
        }
    }
    return stars;
}

/**
 * Get status icon and color for agent/component status
 * @param {string} status - Status string (ready, error, processing, etc.)
 * @returns {object} Object with icon and color class
 */
function getStatusIcon(status) {
    const statusMap = {
        'ready': { icon: 'fa-check-circle', color: 'text-success' },
        'healthy': { icon: 'fa-check-circle', color: 'text-success' },
        'active': { icon: 'fa-check-circle', color: 'text-success' },
        'loaded': { icon: 'fa-check-circle', color: 'text-success' },
        'connected': { icon: 'fa-check-circle', color: 'text-success' },
        'processing': { icon: 'fa-spinner fa-spin', color: 'text-warning' },
        'error': { icon: 'fa-exclamation-circle', color: 'text-danger' },
        'failed': { icon: 'fa-times-circle', color: 'text-danger' },
        'not_loaded': { icon: 'fa-times-circle', color: 'text-danger' },
        'not_initialized': { icon: 'fa-exclamation-triangle', color: 'text-warning' },
        'degraded': { icon: 'fa-exclamation-triangle', color: 'text-warning' },
        'unknown': { icon: 'fa-question-circle', color: 'text-secondary' }
    };

    return statusMap[status] || statusMap['unknown'];
}

/**
 * Create a loading skeleton element
 * @param {string} type - Type of skeleton (text, card, table)
 * @returns {string} HTML string for skeleton
 */
function createSkeleton(type = 'text') {
    if (type === 'text') {
        return '<div class="skeleton" style="height: 20px; margin: 10px 0; border-radius: 4px;"></div>';
    } else if (type === 'card') {
        return `
            <div class="card">
                <div class="card-body">
                    <div class="skeleton" style="height: 20px; width: 60%; margin-bottom: 10px; border-radius: 4px;"></div>
                    <div class="skeleton" style="height: 15px; width: 90%; margin-bottom: 8px; border-radius: 4px;"></div>
                    <div class="skeleton" style="height: 15px; width: 80%; border-radius: 4px;"></div>
                </div>
            </div>
        `;
    }
    return '';
}

/**
 * Store data in localStorage
 * @param {string} key - Storage key
 * @param {any} value - Value to store (will be JSON stringified)
 */
function localStorageSet(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error('Error saving to localStorage:', e);
    }
}

/**
 * Get data from localStorage
 * @param {string} key - Storage key
 * @param {any} defaultValue - Default value if key doesn't exist
 * @returns {any} Retrieved value or default
 */
function localStorageGet(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.error('Error reading from localStorage:', e);
        return defaultValue;
    }
}

/**
 * Remove item from localStorage
 * @param {string} key - Storage key
 */
function localStorageRemove(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.error('Error removing from localStorage:', e);
    }
}

/**
 * Scroll element to bottom
 * @param {HTMLElement} element - Element to scroll
 */
function scrollToBottom(element) {
    if (element) {
        element.scrollTop = element.scrollHeight;
    }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success', 1500);
        return true;
    } catch (e) {
        console.error('Failed to copy to clipboard:', e);
        showToast('Failed to copy to clipboard', 'error');
        return false;
    }
}

/**
 * Download text as file
 * @param {string} filename - Filename
 * @param {string} content - File content
 * @param {string} mimeType - MIME type (default: text/plain)
 */
function downloadFile(filename, content, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
