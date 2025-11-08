/**
 * Main Application Entry Point
 * Initializes all tabs and manages global state
 */

// Global state
let appInitialized = false;

/**
 * Initialize the application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

/**
 * Initialize the application
 */
async function initializeApp() {
    if (appInitialized) return;

    console.log('Initializing Multi-Agent RAG RPG UI...');

    try {
        // Initialize all tabs
        initGameTab();
        initStatusTab();
        initConfigTab();
        initFeedbackTab();

        // Check system health
        await checkSystemHealth();

        // Mark as initialized
        appInitialized = true;

        console.log('Application initialized successfully');

    } catch (error) {
        console.error('Application initialization error:', error);
        showToast('Application initialization failed. Please refresh the page.', 'error', 5000);
    }
}

/**
 * Check system health and update header status
 */
async function checkSystemHealth() {
    const headerStatus = document.getElementById('headerStatus');

    try {
        const health = await StatusAPI.getHealth();

        const isHealthy = health.status === 'healthy';
        const statusClass = isHealthy ? 'text-success' : 'text-warning';
        const statusIcon = isHealthy ? 'fa-check-circle' : 'fa-exclamation-triangle';
        const statusText = isHealthy ? 'Healthy' : 'Degraded';

        headerStatus.innerHTML = `
            <i class="fas ${statusIcon} ${statusClass}"></i> ${statusText}
        `;

        // Update footer
        document.getElementById('footerStatusText').textContent = statusText;

    } catch (error) {
        console.error('Health check failed:', error);

        headerStatus.innerHTML = `
            <i class="fas fa-times-circle text-danger"></i> Error
        `;

        document.getElementById('footerStatusText').textContent = 'Error';
    }
}

/**
 * Refresh system health periodically
 */
setInterval(() => {
    checkSystemHealth();
}, 30000); // Check every 30 seconds

/**
 * Handle unhandled promise rejections
 */
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred. Check console for details.', 'error');
});

/**
 * Handle general errors
 */
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

/**
 * Warn user before leaving if there's an active session
 */
window.addEventListener('beforeunload', (event) => {
    if (currentSessionId && isProcessingTurn) {
        event.preventDefault();
        event.returnValue = 'A turn is currently being processed. Are you sure you want to leave?';
        return event.returnValue;
    }
});
