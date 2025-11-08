/**
 * Config Tab Implementation
 * Simplified configuration management interface
 */

/**
 * Initialize Config Tab
 */
function initConfigTab() {
    renderConfigTab();
}

/**
 * Render Config Tab HTML
 */
function renderConfigTab() {
    const configTab = document.getElementById('configTab');
    configTab.innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            <strong>Configuration Management</strong>
            <p class="mb-0 mt-2">
                The configuration tab provides management of agent settings, corpus ingestion,
                retrieval parameters, and system settings. This is a simplified interface showing
                current configuration status.
            </p>
        </div>

        <!-- Quick Status -->
        <div class="card mb-3">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-cogs"></i> Configuration Overview</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Agents Configured</h6>
                        <ul id="agentsList">
                            <li>Loading...</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6>Retrieval Settings</h6>
                        <div id="retrievalSettings">
                            <p class="text-muted">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Corpus Management -->
        <div class="card mb-3">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-book"></i> Corpus Management</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="corpusFileInput" class="form-label">Upload New Corpus File:</label>
                    <input type="file" id="corpusFileInput" class="form-control" accept=".txt">
                    <div class="form-text">Select a text file to upload and ingest as the game corpus.</div>
                </div>
                <button id="uploadCorpusBtn" class="btn btn-primary" disabled>
                    <i class="fas fa-upload"></i> Upload & Ingest Corpus
                </button>
                <div id="uploadProgress" class="mt-3" style="display: none;">
                    <div class="progress">
                        <div id="uploadProgressBar" class="progress-bar progress-bar-striped progress-bar-animated"
                            role="progressbar" style="width: 0%"></div>
                    </div>
                    <div id="uploadProgressText" class="text-muted mt-2 text-center">Uploading...</div>
                </div>
            </div>
        </div>

        <!-- Configuration Files -->
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0"><i class="fas fa-file-code"></i> Configuration Files</h5>
            </div>
            <div class="card-body">
                <p class="text-muted">
                    Agent and system configurations are managed via YAML files located in the
                    <code>config/</code> directory:
                </p>
                <ul>
                    <li><code>config/config.yaml</code> - Main system configuration</li>
                    <li><code>config/agents.yaml</code> - Agent configurations</li>
                </ul>
                <p class="text-muted mb-0">
                    To modify configurations, edit these files and restart the API server.
                </p>
            </div>
        </div>
    `;

    setupConfigEventListeners();
    loadConfigOverview();
}

/**
 * Setup event listeners
 */
function setupConfigEventListeners() {
    // File input change
    const fileInput = document.getElementById('corpusFileInput');
    fileInput.addEventListener('change', (e) => {
        const uploadBtn = document.getElementById('uploadCorpusBtn');
        uploadBtn.disabled = !e.target.files || e.target.files.length === 0;
    });

    // Upload button
    document.getElementById('uploadCorpusBtn').addEventListener('click', uploadAndIngestCorpus);
}

/**
 * Load configuration overview
 */
async function loadConfigOverview() {
    try {
        // Load agents status
        const agentsStatus = await StatusAPI.getAgentsStatus();
        const agentsList = document.getElementById('agentsList');

        if (agentsStatus.agents && agentsStatus.agents.length > 0) {
            agentsList.innerHTML = agentsStatus.agents.map(agent => `
                <li>${escapeHtml(agent.name)} - ${escapeHtml(agent.llm_provider)} / ${escapeHtml(agent.llm_model)}</li>
            `).join('');
        } else {
            agentsList.innerHTML = '<li class="text-muted">No agents configured</li>';
        }

        // Load retrieval settings
        const retrievalStatus = await StatusAPI.getRetrievalStatus();
        const retrievalSettings = document.getElementById('retrievalSettings');

        retrievalSettings.innerHTML = `
            <p class="mb-1">Hybrid Retrieval: <strong>${retrievalStatus.hybrid_enabled ? 'Enabled' : 'Disabled'}</strong></p>
            <p class="mb-1">Fusion Strategy: <strong>${retrievalStatus.fusion_strategy ? retrievalStatus.fusion_strategy.toUpperCase() : 'N/A'}</strong></p>
            <p class="mb-0">Query Rewriting: <strong>${retrievalStatus.query_rewriting ? 'Enabled' : 'Disabled'}</strong></p>
        `;

    } catch (error) {
        console.error('Failed to load config overview:', error);
    }
}

/**
 * Upload and ingest corpus
 */
async function uploadAndIngestCorpus() {
    const fileInput = document.getElementById('corpusFileInput');
    const file = fileInput.files[0];

    if (!file) {
        showToast('Please select a file', 'warning');
        return;
    }

    try {
        // Show progress
        document.getElementById('uploadProgress').style.display = 'block';
        document.getElementById('uploadProgressText').textContent = 'Uploading file...';
        document.getElementById('uploadProgressBar').style.width = '30%';

        showToast('Starting corpus ingestion...', 'info');

        // Ingest corpus using the existing /ingest endpoint
        const ingestionResult = await CorpusAPI.ingestCorpus({
            corpus_path: `data/${file.name}`,
            chunk_size: 500,
            chunk_overlap: 50,
            embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
        });

        // Update progress
        document.getElementById('uploadProgressText').textContent = 'Ingestion complete!';
        document.getElementById('uploadProgressBar').style.width = '100%';

        showToast('Corpus ingested successfully! Refresh the Status tab to see updates.', 'success', 5000);

        // Clear file input
        fileInput.value = '';
        document.getElementById('uploadCorpusBtn').disabled = true;

        // Hide progress after a delay
        setTimeout(() => {
            document.getElementById('uploadProgress').style.display = 'none';
            document.getElementById('uploadProgressBar').style.width = '0%';
        }, 2000);

    } catch (error) {
        document.getElementById('uploadProgress').style.display = 'none';
        showToast(`Failed to ingest corpus: ${error.message}`, 'error');
    }
}
