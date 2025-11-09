/**
 * Status Tab Implementation
 * Displays real-time system health, component status, and operational metrics
 */

let statusRefreshInterval = null;

/**
 * Initialize Status Tab
 */
function initStatusTab() {
    renderStatusTab();
    setupStatusEventListeners();
    refreshAllStatus();
}

/**
 * Render Status Tab HTML
 */
function renderStatusTab() {
    const statusTab = document.getElementById('statusTab');
    statusTab.innerHTML = `
        <div class="row">
            <div class="col-12 mb-3">
                <button id="refreshStatusBtn" class="btn btn-primary btn-sm">
                    <i class="fas fa-sync-alt"></i> Refresh Status
                </button>
                <span id="lastUpdated" class="text-muted ms-3" style="font-size: 0.875rem;">
                    Last updated: Never
                </span>
            </div>
        </div>

        <!-- System Overview -->
        <div class="card status-card">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-server"></i> System Overview</h5>
            </div>
            <div class="card-body" id="systemOverview">
                ${createSkeleton('card')}
            </div>
        </div>

        <!-- Corpus Status -->
        <div class="card status-card">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-book"></i> Corpus Status</h5>
            </div>
            <div class="card-body" id="corpusStatus">
                ${createSkeleton('card')}
            </div>
        </div>

        <!-- Agent Status -->
        <div class="card status-card">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-robot"></i> Agent Status</h5>
            </div>
            <div class="card-body" id="agentStatus">
                ${createSkeleton('card')}
            </div>
        </div>

        <!-- Retrieval System Status -->
        <div class="card status-card">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-search"></i> Retrieval System</h5>
            </div>
            <div class="card-body" id="retrievalStatus">
                ${createSkeleton('card')}
            </div>
        </div>
    `;
}

/**
 * Setup event listeners for status tab
 */
function setupStatusEventListeners() {
    // Refresh button
    document.getElementById('refreshStatusBtn').addEventListener('click', refreshAllStatus);

    // Tab shown event - start auto-refresh
    const statusTabButton = document.getElementById('status-tab');
    statusTabButton.addEventListener('shown.bs.tab', () => {
        refreshAllStatus();
        startAutoRefresh();
    });

    // Tab hidden event - stop auto-refresh
    statusTabButton.addEventListener('hidden.bs.tab', stopAutoRefresh);
}

/**
 * Start auto-refresh of status
 */
function startAutoRefresh() {
    if (statusRefreshInterval) return;

    statusRefreshInterval = setInterval(() => {
        refreshAllStatus();
    }, 10000); // Refresh every 10 seconds
}

/**
 * Stop auto-refresh of status
 */
function stopAutoRefresh() {
    if (statusRefreshInterval) {
        clearInterval(statusRefreshInterval);
        statusRefreshInterval = null;
    }
}

/**
 * Refresh all status information
 */
async function refreshAllStatus() {
    await Promise.all([
        updateSystemOverview(),
        updateCorpusStatus(),
        updateAgentStatus(),
        updateRetrievalStatus(),
    ]);

    // Update last updated timestamp
    const now = new Date();
    document.getElementById('lastUpdated').textContent = `Last updated: ${formatTimestamp(now)}`;
}

/**
 * Update system overview section
 */
async function updateSystemOverview() {
    const container = document.getElementById('systemOverview');

    try {
        const systemStatus = await StatusAPI.getSystemStatus();

        const statusIcon = getStatusIcon(systemStatus.status);
        const uptimeStr = formatDuration(systemStatus.uptime_seconds || 0);

        container.innerHTML = `
            <div class="metric-row">
                <span class="metric-label">Status</span>
                <span class="metric-value ${statusIcon.color}">
                    <i class="fas ${statusIcon.icon}"></i> ${systemStatus.status || 'Unknown'}
                </span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Uptime</span>
                <span class="metric-value">${uptimeStr}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Active Sessions</span>
                <span class="metric-value">${systemStatus.active_sessions || 0}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Turns</span>
                <span class="metric-value">${systemStatus.total_turns || 0}</span>
            </div>
            ${systemStatus.memory_usage_mb ? `
            <div class="metric-row">
                <span class="metric-label">Memory Usage</span>
                <span class="metric-value">${systemStatus.memory_usage_mb.toFixed(1)} MB</span>
            </div>
            ` : ''}
            ${systemStatus.cpu_percent ? `
            <div class="metric-row">
                <span class="metric-label">CPU Usage</span>
                <span class="metric-value">${systemStatus.cpu_percent.toFixed(1)}%</span>
            </div>
            ` : ''}
        `;

        // Update footer
        document.getElementById('footerStatusText').textContent = systemStatus.status || 'Unknown';

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-circle"></i> Failed to load system status: ${error.message}
            </div>
        `;
    }
}

/**
 * Update corpus status section
 */
async function updateCorpusStatus() {
    const container = document.getElementById('corpusStatus');

    try {
        const corpusStatus = await StatusAPI.getCorpusStatus();

        const bm25Icon = getStatusIcon(corpusStatus.bm25_status);
        const vectorIcon = getStatusIcon(corpusStatus.vector_db_status);

        container.innerHTML = `
            <div class="metric-row">
                <span class="metric-label">Corpus File</span>
                <span class="metric-value">${escapeHtml(corpusStatus.corpus_name || corpusStatus.corpus_path || 'None')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Chunks</span>
                <span class="metric-value">${corpusStatus.total_chunks || 0}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">BM25 Index</span>
                <span class="metric-value ${bm25Icon.color}">
                    <i class="fas ${bm25Icon.icon}"></i> ${corpusStatus.bm25_status || 'Unknown'}
                </span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Vector DB</span>
                <span class="metric-value ${vectorIcon.color}">
                    <i class="fas ${vectorIcon.icon}"></i> ${corpusStatus.vector_db_status || 'Unknown'}
                </span>
            </div>
            ${corpusStatus.vector_db_provider ? `
            <div class="metric-row">
                <span class="metric-label">Vector DB Provider</span>
                <span class="metric-value">${escapeHtml(corpusStatus.vector_db_provider)}</span>
            </div>
            ` : ''}
            ${corpusStatus.collection_name ? `
            <div class="metric-row">
                <span class="metric-label">Collection</span>
                <span class="metric-value">${escapeHtml(corpusStatus.collection_name)}</span>
            </div>
            ` : ''}
            ${corpusStatus.embedding_model ? `
            <div class="metric-row">
                <span class="metric-label">Embedding Model</span>
                <span class="metric-value">${escapeHtml(corpusStatus.embedding_model)}</span>
            </div>
            ` : ''}
            ${corpusStatus.embedding_dimension ? `
            <div class="metric-row">
                <span class="metric-label">Embedding Dimension</span>
                <span class="metric-value">${corpusStatus.embedding_dimension}</span>
            </div>
            ` : ''}
        `;

        // Update footer
        document.getElementById('footerCorpusText').textContent = corpusStatus.corpus_name || corpusStatus.corpus_path || 'None';

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-circle"></i> Failed to load corpus status: ${error.message}
            </div>
        `;
    }
}

/**
 * Update agent status section
 */
async function updateAgentStatus() {
    const container = document.getElementById('agentStatus');

    try {
        const agents = await StatusAPI.getAgentsStatus();

        if (!agents || agents.length === 0) {
            container.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="fas fa-exclamation-triangle"></i> No agents configured
                </div>
            `;
            return;
        }

        let tableHtml = `
            <div class="table-responsive">
                <table class="table table-sm agent-status-table">
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>LLM</th>
                            <th>Status</th>
                            <th>Calls</th>
                            <th>Avg Time</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        for (const agent of agents) {
            const statusIcon = getStatusIcon(agent.llm_status || agent.status);
            const successRate = agent.total_calls > 0
                ? ((agent.successful_calls / agent.total_calls) * 100).toFixed(0)
                : 'N/A';

            tableHtml += `
                <tr>
                    <td><strong>${escapeHtml(agent.agent_name || agent.name)}</strong></td>
                    <td>
                        <span class="text-muted">${escapeHtml(agent.llm_provider || 'Unknown')}</span><br>
                        <small>${escapeHtml(agent.llm_model || 'Unknown')}</small>
                    </td>
                    <td>
                        <span class="${statusIcon.color}">
                            <i class="fas ${statusIcon.icon} agent-status-icon"></i>
                            ${agent.llm_status || agent.status || 'Unknown'}
                        </span>
                        ${agent.last_error ? `<br><small class="text-danger">${escapeHtml(agent.last_error.substring(0, 50))}...</small>` : ''}
                    </td>
                    <td>
                        ${agent.successful_calls || 0}/${agent.total_calls || 0}
                        <br><small class="text-muted">(${successRate}%)</small>
                    </td>
                    <td>
                        ${agent.average_response_time || agent.avg_response_time
                            ? `${(agent.average_response_time || agent.avg_response_time).toFixed(2)}s`
                            : 'N/A'}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary test-agent-btn" data-agent="${escapeHtml(agent.agent_name || agent.name)}">
                            <i class="fas fa-plug"></i> Test
                        </button>
                    </td>
                </tr>
            `;
        }

        tableHtml += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = tableHtml;

        // Add event listeners for test buttons
        document.querySelectorAll('.test-agent-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const agentName = e.currentTarget.getAttribute('data-agent');
                await testAgentConnection(agentName, e.currentTarget);
            });
        });

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-circle"></i> Failed to load agent status: ${error.message}
            </div>
        `;
    }
}

/**
 * Update retrieval system status section
 */
async function updateRetrievalStatus() {
    const container = document.getElementById('retrievalStatus');

    try {
        const retrievalStatus = await StatusAPI.getRetrievalStatus();

        const hybridIcon = getStatusIcon(retrievalStatus.hybrid_enabled ? 'active' : 'inactive');

        container.innerHTML = `
            <div class="metric-row">
                <span class="metric-label">Hybrid Retrieval</span>
                <span class="metric-value ${hybridIcon.color}">
                    <i class="fas ${hybridIcon.icon}"></i>
                    ${retrievalStatus.hybrid_enabled ? 'Active' : 'Inactive'}
                </span>
            </div>
            <div class="metric-row">
                <span class="metric-label">BM25 Retriever</span>
                <span class="metric-value">
                    ${retrievalStatus.bm25_status || 'Unknown'}
                    ${retrievalStatus.bm25_documents ? `(${retrievalStatus.bm25_documents} docs)` : ''}
                </span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Vector Retriever</span>
                <span class="metric-value">
                    ${retrievalStatus.vector_status || 'Unknown'}
                    ${retrievalStatus.vector_provider ? `(${retrievalStatus.vector_provider})` : ''}
                </span>
            </div>
            ${retrievalStatus.fusion_strategy ? `
            <div class="metric-row">
                <span class="metric-label">Fusion Strategy</span>
                <span class="metric-value">${retrievalStatus.fusion_strategy.toUpperCase()}</span>
            </div>
            ` : ''}
            ${retrievalStatus.query_rewriting !== undefined ? `
            <div class="metric-row">
                <span class="metric-label">Query Rewriting</span>
                <span class="metric-value">
                    ${retrievalStatus.query_rewriting ? 'Enabled' : 'Disabled'}
                </span>
            </div>
            ` : ''}
            ${retrievalStatus.cache_hit_rate !== undefined ? `
            <div class="metric-row">
                <span class="metric-label">Cache Hit Rate</span>
                <span class="metric-value">${(retrievalStatus.cache_hit_rate * 100).toFixed(1)}%</span>
            </div>
            ` : ''}
        `;

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-circle"></i> Failed to load retrieval status: ${error.message}
            </div>
        `;
    }
}

/**
 * Test connection to a specific agent
 * @param {string} agentName - Name of the agent to test
 * @param {HTMLElement} button - The button element that was clicked
 */
async function testAgentConnection(agentName, button) {
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';

    try {
        const result = await apiRequest(`/api/status/agents/${agentName}/test`, {
            method: 'POST',
        });

        if (result.success) {
            showToast(`Connection test successful for ${agentName}`, 'success');
            button.innerHTML = '<i class="fas fa-check"></i> Success';
            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.disabled = false;
            }, 2000);
        } else {
            showToast(`Connection test failed for ${agentName}: ${result.error}`, 'error');
            button.innerHTML = '<i class="fas fa-times"></i> Failed';
            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.disabled = false;
            }, 2000);
        }

        // Refresh agent status to show updated stats
        await updateAgentStatus();

    } catch (error) {
        showToast(`Error testing ${agentName}: ${error.message}`, 'error');
        button.innerHTML = '<i class="fas fa-times"></i> Error';
        setTimeout(() => {
            button.innerHTML = originalHtml;
            button.disabled = false;
        }, 2000);
    }
}
