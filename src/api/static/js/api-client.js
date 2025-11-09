/**
 * API Client for Multi-Agent RAG RPG
 * Provides wrapper functions for all API endpoints
 */

const API_BASE_URL = window.location.origin;

/**
 * Generic API request helper
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const fetchOptions = { ...defaultOptions, ...options };

    if (fetchOptions.body && typeof fetchOptions.body === 'object') {
        fetchOptions.body = JSON.stringify(fetchOptions.body);
    }

    try {
        const response = await fetch(url, fetchOptions);

        // Handle non-JSON responses (e.g., file downloads)
        const contentType = response.headers.get('content-type');
        if (contentType && !contentType.includes('application/json')) {
            if (response.ok) {
                return await response.blob();
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// ==================== GAME ENDPOINTS ====================

const GameAPI = {
    /**
     * Create a new game session
     * @param {string} initialContext - Optional initial context
     * @returns {Promise<object>} New session data
     */
    async newGame(initialContext = '') {
        return await apiRequest('/api/new_game', {
            method: 'POST',
            body: { initial_context: initialContext },
        });
    },

    /**
     * Submit a player turn
     * @param {string} sessionId - Session ID
     * @param {string} playerCommand - Player command
     * @returns {Promise<object>} Turn results
     */
    async submitTurn(sessionId, playerCommand) {
        return await apiRequest('/api/turn', {
            method: 'POST',
            body: {
                session_id: sessionId,
                player_command: playerCommand,
            },
        });
    },

    /**
     * Get game state for a session
     * @param {string} sessionId - Session ID
     * @returns {Promise<object>} Game state
     */
    async getState(sessionId) {
        return await apiRequest(`/api/state/${sessionId}`);
    },

    /**
     * Get turn progress for a session
     * @param {string} sessionId - Session ID
     * @returns {Promise<object>} Progress data
     */
    async getProgress(sessionId) {
        return await apiRequest(`/api/progress/${sessionId}`);
    },

    /**
     * Delete a game session
     * @param {string} sessionId - Session ID
     * @returns {Promise<object>} Deletion result
     */
    async deleteSession(sessionId) {
        return await apiRequest(`/api/session/${sessionId}`, {
            method: 'DELETE',
        });
    },
};

// ==================== STATUS ENDPOINTS ====================

const StatusAPI = {
    /**
     * Get overall system status
     * @returns {Promise<object>} System status
     */
    async getSystemStatus() {
        return await apiRequest('/api/status/system');
    },

    /**
     * Get corpus status
     * @returns {Promise<object>} Corpus status
     */
    async getCorpusStatus() {
        return await apiRequest('/api/status/corpus');
    },

    /**
     * Get agents status
     * @returns {Promise<object>} Agents status
     */
    async getAgentsStatus() {
        return await apiRequest('/api/status/agents');
    },

    /**
     * Get retrieval system status
     * @returns {Promise<object>} Retrieval status
     */
    async getRetrievalStatus() {
        return await apiRequest('/api/status/retrieval');
    },

    /**
     * Get health check
     * @returns {Promise<object>} Health data
     */
    async getHealth() {
        return await apiRequest('/health');
    },

    /**
     * Get full configuration
     * @returns {Promise<object>} Full configuration
     */
    async getConfig() {
        return await apiRequest('/api/status/config');
    },
};

// ==================== CONFIGURATION ENDPOINTS ====================

const ConfigAPI = {
    /**
     * Get all agents configuration
     * @returns {Promise<object>} Agents config
     */
    async getAgentsConfig() {
        return await apiRequest('/api/config/agents');
    },

    /**
     * Get specific agent configuration
     * @param {string} agentName - Agent name
     * @returns {Promise<object>} Agent config
     */
    async getAgentConfig(agentName) {
        return await apiRequest(`/api/config/agents/${agentName}`);
    },

    /**
     * Update agent configuration
     * @param {string} agentName - Agent name
     * @param {object} config - New configuration
     * @returns {Promise<object>} Update result
     */
    async updateAgentConfig(agentName, config) {
        return await apiRequest(`/api/config/agents/${agentName}`, {
            method: 'PUT',
            body: config,
        });
    },

    /**
     * Test agent connection
     * @param {string} agentName - Agent name
     * @returns {Promise<object>} Test result
     */
    async testAgentConnection(agentName) {
        return await apiRequest(`/api/config/agents/${agentName}/test`, {
            method: 'POST',
        });
    },

    /**
     * Get retrieval configuration
     * @returns {Promise<object>} Retrieval config
     */
    async getRetrievalConfig() {
        return await apiRequest('/api/config/retrieval');
    },

    /**
     * Update retrieval configuration
     * @param {object} config - New configuration
     * @returns {Promise<object>} Update result
     */
    async updateRetrievalConfig(config) {
        return await apiRequest('/api/config/retrieval', {
            method: 'PUT',
            body: config,
        });
    },

    /**
     * Test retrieval with a query
     * @param {string} query - Test query
     * @param {number} topK - Number of results
     * @returns {Promise<object>} Test results
     */
    async testRetrieval(query, topK = 10) {
        return await apiRequest('/api/config/retrieval/test', {
            method: 'POST',
            body: { query, top_k: topK },
        });
    },

    /**
     * Clear retrieval cache
     * @returns {Promise<object>} Clear result
     */
    async clearRetrievalCache() {
        return await apiRequest('/api/config/retrieval/cache/clear', {
            method: 'POST',
        });
    },

    /**
     * Get system configuration
     * @returns {Promise<object>} System config
     */
    async getSystemConfig() {
        return await apiRequest('/api/config/system');
    },

    /**
     * Update system configuration
     * @param {object} config - New configuration
     * @returns {Promise<object>} Update result
     */
    async updateSystemConfig(config) {
        return await apiRequest('/api/config/system', {
            method: 'PUT',
            body: config,
        });
    },

    /**
     * Export configuration
     * @returns {Promise<Blob>} Config file blob
     */
    async exportConfig() {
        return await apiRequest('/api/config/export');
    },

    /**
     * Import configuration
     * @param {File} file - Config file
     * @returns {Promise<object>} Import result
     */
    async importConfig(file) {
        const formData = new FormData();
        formData.append('file', file);

        return await apiRequest('/api/config/import', {
            method: 'POST',
            headers: {}, // Let browser set Content-Type for FormData
            body: formData,
        });
    },
};

// ==================== CORPUS ENDPOINTS ====================

const CorpusAPI = {
    /**
     * Upload corpus file
     * @param {File} file - Corpus file
     * @returns {Promise<object>} Upload result
     */
    async uploadCorpus(file) {
        const formData = new FormData();
        formData.append('file', file);

        return await apiRequest('/api/corpus/upload', {
            method: 'POST',
            headers: {}, // Let browser set Content-Type for FormData
            body: formData,
        });
    },

    /**
     * Get current corpus info
     * @returns {Promise<object>} Corpus info
     */
    async getCurrentCorpus() {
        return await apiRequest('/api/corpus/current');
    },

    /**
     * Preview corpus chunks
     * @param {number} limit - Number of chunks to preview
     * @returns {Promise<object>} Chunk preview
     */
    async previewCorpus(limit = 10) {
        return await apiRequest(`/api/corpus/preview?limit=${limit}`);
    },

    /**
     * Re-index current corpus
     * @param {object} settings - Ingestion settings
     * @returns {Promise<object>} Re-index result with task_id
     */
    async reIndexCorpus(settings) {
        return await apiRequest('/api/corpus/re-index', {
            method: 'POST',
            body: settings,
        });
    },

    /**
     * Get ingestion progress
     * @param {string} taskId - Task ID
     * @returns {Promise<object>} Progress data
     */
    async getIngestionProgress(taskId) {
        return await apiRequest(`/api/corpus/ingest/progress/${taskId}`);
    },

    /**
     * Ingest corpus
     * @param {object} params - Ingestion parameters
     * @returns {Promise<object>} Ingestion result
     */
    async ingestCorpus(params) {
        return await apiRequest('/ingest', {
            method: 'POST',
            body: params,
        });
    },
};

// ==================== FEEDBACK ENDPOINTS ====================

const FeedbackAPI = {
    /**
     * Submit feedback
     * @param {object} feedback - Feedback data
     * @returns {Promise<object>} Submission result
     */
    async submitFeedback(feedback) {
        return await apiRequest('/api/feedback', {
            method: 'POST',
            body: feedback,
        });
    },

    /**
     * Get feedback list
     * @param {object} filters - Filter parameters
     * @returns {Promise<object>} Feedback list
     */
    async getFeedbackList(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return await apiRequest(`/api/feedback${params ? '?' + params : ''}`);
    },

    /**
     * Get single feedback item
     * @param {string} feedbackId - Feedback ID
     * @returns {Promise<object>} Feedback data
     */
    async getFeedback(feedbackId) {
        return await apiRequest(`/api/feedback/${feedbackId}`);
    },

    /**
     * Update feedback
     * @param {string} feedbackId - Feedback ID
     * @param {object} updates - Update data
     * @returns {Promise<object>} Update result
     */
    async updateFeedback(feedbackId, updates) {
        return await apiRequest(`/api/feedback/${feedbackId}`, {
            method: 'PATCH',
            body: updates,
        });
    },

    /**
     * Delete feedback
     * @param {string} feedbackId - Feedback ID
     * @returns {Promise<object>} Deletion result
     */
    async deleteFeedback(feedbackId) {
        return await apiRequest(`/api/feedback/${feedbackId}`, {
            method: 'DELETE',
        });
    },

    /**
     * Search feedback
     * @param {string} query - Search query
     * @param {number} limit - Result limit
     * @returns {Promise<object>} Search results
     */
    async searchFeedback(query, limit = 20) {
        return await apiRequest('/api/feedback/search', {
            method: 'POST',
            body: { query, limit },
        });
    },

    /**
     * Export feedback
     * @param {object} filters - Filter parameters
     * @param {string} format - Export format (json, csv)
     * @returns {Promise<Blob>} Export file blob
     */
    async exportFeedback(filters = {}, format = 'json') {
        const params = new URLSearchParams({ ...filters, format }).toString();
        return await apiRequest(`/api/feedback/export?${params}`);
    },

    /**
     * Get feedback statistics
     * @param {object} filters - Filter parameters
     * @returns {Promise<object>} Statistics data
     */
    async getFeedbackStats(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        return await apiRequest(`/api/feedback/stats${params ? '?' + params : ''}`);
    },
};

// ==================== LOGGING ENDPOINTS ====================

const LoggingAPI = {
    /**
     * Get recent logs
     * @param {object} params - Log query parameters
     * @returns {Promise<object>} Logs data
     */
    async getLogs(params = {}) {
        const queryParams = new URLSearchParams(params).toString();
        return await apiRequest(`/api/logs${queryParams ? '?' + queryParams : ''}`);
    },
};

// ==================== SEARCH ENDPOINT ====================

const SearchAPI = {
    /**
     * Search corpus
     * @param {string} query - Search query
     * @param {number} topK - Number of results
     * @returns {Promise<object>} Search results
     */
    async search(query, topK = 10) {
        return await apiRequest('/search', {
            method: 'POST',
            body: { query, top_k: topK },
        });
    },
};
