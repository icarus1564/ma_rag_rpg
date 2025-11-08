/**
 * Feedback Tab Implementation
 * Simplified feedback collection and display interface
 */

/**
 * Initialize Feedback Tab
 */
function initFeedbackTab() {
    renderFeedbackTab();
}

/**
 * Render Feedback Tab HTML
 */
function renderFeedbackTab() {
    const feedbackTab = document.getElementById('feedbackTab');
    feedbackTab.innerHTML = `
        <div class="row">
            <div class="col-md-8">
                <!-- Submit Feedback Form -->
                <div class="card mb-3">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-comment-dots"></i> Submit Feedback</h5>
                    </div>
                    <div class="card-body">
                        <form id="feedbackForm">
                            <div class="mb-3">
                                <label for="feedbackType" class="form-label">Feedback Type:</label>
                                <select id="feedbackType" class="form-select" required>
                                    <option value="general">General Feedback</option>
                                    <option value="bug_report">Bug Report</option>
                                    <option value="feature_request">Feature Request</option>
                                    <option value="agent_behavior">Agent Behavior</option>
                                    <option value="performance">Performance Issue</option>
                                </select>
                            </div>

                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="feedbackSessionId" class="form-label">Session ID (Optional):</label>
                                    <input type="text" id="feedbackSessionId" class="form-control"
                                        placeholder="Leave empty if not session-specific">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label for="feedbackAgent" class="form-label">Related Agent (Optional):</label>
                                    <select id="feedbackAgent" class="form-select">
                                        <option value="">All/General</option>
                                        <option value="narrator">Narrator</option>
                                        <option value="scene_planner">Scene Planner</option>
                                        <option value="npc_manager">NPC Manager</option>
                                        <option value="rules_referee">Rules Referee</option>
                                    </select>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="feedbackRating" class="form-label">
                                    Rating (Optional):
                                    <span id="ratingDisplay" class="ms-2"></span>
                                </label>
                                <input type="range" id="feedbackRating" class="form-range"
                                    min="1" max="5" value="3">
                            </div>

                            <div class="mb-3">
                                <label for="feedbackText" class="form-label">Feedback:</label>
                                <textarea id="feedbackText" class="form-control" rows="5"
                                    placeholder="Enter your feedback here..." maxlength="5000" required></textarea>
                                <div class="text-end">
                                    <small class="text-muted">
                                        <span id="feedbackCharCount">0</span>/5000
                                    </small>
                                </div>
                            </div>

                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-paper-plane"></i> Submit Feedback
                            </button>
                            <button type="reset" class="btn btn-secondary">
                                <i class="fas fa-undo"></i> Reset
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <!-- Feedback Summary -->
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-bar"></i> Feedback Summary</h5>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">
                            Thank you for providing feedback! Your input helps improve the Multi-Agent RAG RPG system.
                        </p>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i>
                            <p class="mb-0 mt-2" style="font-size: 0.875rem;">
                                <strong>Note:</strong> Feedback storage is currently simplified.
                                Submitted feedback will be logged to the console for this phase.
                                Full feedback storage with BM25 indexing will be implemented in a future update.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    setupFeedbackEventListeners();
}

/**
 * Setup event listeners
 */
function setupFeedbackEventListeners() {
    // Rating slider
    const ratingSlider = document.getElementById('feedbackRating');
    const ratingDisplay = document.getElementById('ratingDisplay');

    ratingSlider.addEventListener('input', () => {
        ratingDisplay.innerHTML = generateStarRating(parseInt(ratingSlider.value));
    });

    // Initialize rating display
    ratingDisplay.innerHTML = generateStarRating(3);

    // Feedback text character count
    const feedbackText = document.getElementById('feedbackText');
    const charCount = document.getElementById('feedbackCharCount');

    feedbackText.addEventListener('input', () => {
        charCount.textContent = feedbackText.value.length;
    });

    // Form submission
    document.getElementById('feedbackForm').addEventListener('submit', submitFeedback);

    // Auto-fill session ID if available
    if (currentSessionId) {
        document.getElementById('feedbackSessionId').value = currentSessionId;
    }
}

/**
 * Submit feedback
 * @param {Event} e - Form submit event
 */
async function submitFeedback(e) {
    e.preventDefault();

    const feedbackData = {
        type: document.getElementById('feedbackType').value,
        session_id: document.getElementById('feedbackSessionId').value.trim() || null,
        agent: document.getElementById('feedbackAgent').value || null,
        rating: parseInt(document.getElementById('feedbackRating').value),
        feedback_text: document.getElementById('feedbackText').value.trim(),
        timestamp: new Date().toISOString(),
    };

    try {
        // Log feedback to console (simplified implementation)
        console.log('Feedback submitted:', feedbackData);

        showToast('Feedback submitted successfully! Thank you.', 'success', 3000);

        // Reset form
        document.getElementById('feedbackForm').reset();
        document.getElementById('feedbackCharCount').textContent = '0';
        document.getElementById('ratingDisplay').innerHTML = generateStarRating(3);

        // Update badge count
        const currentCount = parseInt(document.getElementById('feedbackCount').textContent) || 0;
        document.getElementById('feedbackCount').textContent = currentCount + 1;

        // Note: In full implementation, this would call FeedbackAPI.submitFeedback()
        // For now, we're just logging it

    } catch (error) {
        showToast(`Failed to submit feedback: ${error.message}`, 'error');
    }
}
