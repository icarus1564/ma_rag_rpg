/**
 * Game Tab Implementation
 * Handles game session management, turn submission, and output display
 */

let currentSessionId = null;
let isProcessingTurn = false;
let progressPollInterval = null;
let isGameOver = false; // Track if current game has ended

/**
 * Initialize Game Tab
 */
function initGameTab() {
    renderGameTab();
    loadSavedSession();
    setupGameEventListeners();
}

/**
 * Update UI state when game ends or restarts
 * @param {boolean} isOver - Whether the game is over
 */
function updateGameOverState(isOver) {
    isGameOver = isOver;

    if (isOver) {
        // Hide the Submit Turn section entirely
        document.getElementById('playerInputSection').style.display = 'none';

        // Highlight the "New Game" button
        const newGameBtn = document.getElementById('newGameBtn');
        newGameBtn.classList.add('btn-success', 'pulse-animation');
        newGameBtn.classList.remove('btn-primary');

        // Add "Start new game?" message
        const sessionInfo = document.getElementById('sessionInfo');
        sessionInfo.innerHTML = `
            <span class="text-success">
                <i class="fas fa-redo"></i> Start new game?
            </span>
        `;
    } else {
        // Show Submit Turn section
        document.getElementById('playerInputSection').style.display = 'block';

        // Reset "New Game" button styling
        const newGameBtn = document.getElementById('newGameBtn');
        newGameBtn.classList.add('btn-primary');
        newGameBtn.classList.remove('btn-success', 'pulse-animation');
    }
}

/**
 * Render Game Tab HTML
 */
function renderGameTab() {
    const gameTab = document.getElementById('gameTab');
    gameTab.innerHTML = `
        <!-- Session Controls -->
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <button id="newGameBtn" class="btn btn-primary">
                            <i class="fas fa-plus"></i> New Game
                        </button>
                        <button id="loadSessionBtn" class="btn btn-secondary">
                            <i class="fas fa-folder-open"></i> Load Session
                        </button>
                    </div>
                    <div class="col-md-6 text-md-end mt-2 mt-md-0">
                        <span id="sessionInfo" class="text-muted">No active session</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Initial Context (shown only for new game) -->
        <div id="initialContextSection" class="card mb-3" style="display: none;">
            <div class="card-header">
                <h5 class="mb-0">New Game - Initial Context (Optional)</h5>
            </div>
            <div class="card-body">
                <textarea id="initialContextInput" class="form-control" rows="3"
                    placeholder="Enter optional starting context for the game..."></textarea>
                <div class="mt-2">
                    <button id="startGameBtn" class="btn btn-success">Start Game</button>
                    <button id="cancelNewGameBtn" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        </div>

        <!-- Player Input -->
        <div id="playerInputSection" class="card mb-3">
            <div class="card-header">
                <h5 class="mb-0">Your Command</h5>
            </div>
            <div class="card-body">
                <textarea id="playerCommandInput" class="form-control" rows="3"
                    placeholder="Enter your command..." maxlength="2000"></textarea>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div class="char-counter">
                        <span id="charCount">0</span>/2000
                    </div>
                    <div>
                        <button id="clearCommandBtn" class="btn btn-sm btn-secondary">
                            <i class="fas fa-eraser"></i> Clear
                        </button>
                        <button id="submitTurnBtn" class="btn btn-sm btn-primary" disabled>
                            <i class="fas fa-paper-plane"></i> Submit Turn
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Turn Progress -->
        <div id="turnProgressSection" class="card mb-3" style="display: none;">
            <div class="card-body">
                <div class="progress-container">
                    <div class="progress">
                        <div id="turnProgressBar" class="progress-bar progress-bar-striped progress-bar-animated"
                            role="progressbar" style="width: 0%"></div>
                    </div>
                    <div id="turnProgressText" class="progress-text text-center">Processing...</div>
                </div>
            </div>
        </div>

        <!-- Game Output -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Game Output</h5>
                <div>
                    <button id="exportHistoryBtn" class="btn btn-sm btn-outline-secondary" disabled>
                        <i class="fas fa-download"></i> Export
                    </button>
                    <button id="clearHistoryBtn" class="btn btn-sm btn-outline-danger" disabled>
                        <i class="fas fa-trash"></i> Clear
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="gameOutput" class="mb-0">
                    <div class="text-center text-muted py-5">
                        <i class="fas fa-gamepad fa-3x mb-3"></i>
                        <p>Start a new game or load an existing session to begin playing</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Load Session Modal -->
        <div class="modal fade" id="loadSessionModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Load Session</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <label for="sessionIdInput" class="form-label">Session ID:</label>
                        <input type="text" id="sessionIdInput" class="form-control"
                            placeholder="Enter session ID...">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" id="loadSessionConfirmBtn" class="btn btn-primary">Load</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Setup event listeners for game tab
 */
function setupGameEventListeners() {
    // New Game button
    document.getElementById('newGameBtn').addEventListener('click', () => {
        document.getElementById('initialContextSection').style.display = 'block';
        document.getElementById('initialContextInput').value = '';
        document.getElementById('initialContextInput').focus();
    });

    // Start Game button
    document.getElementById('startGameBtn').addEventListener('click', startNewGame);

    // Cancel New Game button
    document.getElementById('cancelNewGameBtn').addEventListener('click', () => {
        document.getElementById('initialContextSection').style.display = 'none';
    });

    // Load Session button
    document.getElementById('loadSessionBtn').addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('loadSessionModal'));
        modal.show();
    });

    // Load Session Confirm button
    document.getElementById('loadSessionConfirmBtn').addEventListener('click', async () => {
        const sessionId = document.getElementById('sessionIdInput').value.trim();
        if (sessionId) {
            await loadSession(sessionId);
            bootstrap.Modal.getInstance(document.getElementById('loadSessionModal')).hide();
        }
    });

    // Player command input
    const commandInput = document.getElementById('playerCommandInput');
    commandInput.addEventListener('input', updateCharCount);
    commandInput.addEventListener('keydown', (e) => {
        // Submit on Ctrl+Enter
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            submitTurn();
        }
    });

    // Submit Turn button
    document.getElementById('submitTurnBtn').addEventListener('click', submitTurn);

    // Clear Command button
    document.getElementById('clearCommandBtn').addEventListener('click', () => {
        document.getElementById('playerCommandInput').value = '';
        updateCharCount();
    });

    // Export History button
    document.getElementById('exportHistoryBtn').addEventListener('click', exportGameHistory);

    // Clear History button
    document.getElementById('clearHistoryBtn').addEventListener('click', clearGameHistory);
}

/**
 * Update character count for player command
 */
function updateCharCount() {
    const input = document.getElementById('playerCommandInput');
    const count = input.value.length;
    const charCountEl = document.getElementById('charCount');
    const submitBtn = document.getElementById('submitTurnBtn');

    charCountEl.textContent = count;

    // Update UI based on length
    if (count > 2000) {
        charCountEl.parentElement.classList.add('over-limit');
        submitBtn.disabled = true;
    } else if (count > 0 && !isProcessingTurn && currentSessionId) {
        charCountEl.parentElement.classList.remove('over-limit');
        submitBtn.disabled = false;
    } else {
        charCountEl.parentElement.classList.remove('over-limit');
        submitBtn.disabled = true;
    }
}

/**
 * Start a new game session
 */
async function startNewGame() {
    const initialContext = document.getElementById('initialContextInput').value.trim();

    try {
        showToast('Creating new game session...', 'info');

        const response = await GameAPI.newGame(initialContext);
        currentSessionId = response.session_id;

        // Save to localStorage
        localStorageSet('currentSessionId', currentSessionId);

        // Clear any previous game-over state
        localStorageRemove(`gameOver_${currentSessionId}`);

        // Hide initial context section
        document.getElementById('initialContextSection').style.display = 'none';

        // Reset game-over state
        updateGameOverState(false);

        // Update UI
        updateSessionInfo();
        clearGameOutput();

        // Display welcome message
        if (response.message) {
            appendToGameOutput({
                type: 'system',
                content: response.message,
                timestamp: response.created_at || new Date().toISOString(),
            });
        }

        showToast('Game session created successfully!', 'success');
        updateCharCount();

    } catch (error) {
        showToast(`Failed to create game session: ${error.message}`, 'error');
    }
}

/**
 * Load an existing session
 * @param {string} sessionId - Session ID to load
 */
async function loadSession(sessionId) {
    try {
        showToast('Loading session...', 'info');

        const state = await GameAPI.getState(sessionId);
        currentSessionId = sessionId;

        // Save to localStorage
        localStorageSet('currentSessionId', currentSessionId);

        // Update UI
        updateSessionInfo();
        clearGameOutput();

        // Display session info
        appendToGameOutput({
            type: 'system',
            content: `Loaded session: ${sessionId}\nTurn count: ${state.turn_count}`,
            timestamp: new Date().toISOString(),
        });

        showToast('Session loaded successfully!', 'success');
        updateCharCount();

        // Check if this session ended (game over)
        const isOver = localStorageGet(`gameOver_${sessionId}`);
        if (isOver) {
            updateGameOverState(true);
        }

    } catch (error) {
        showToast(`Failed to load session: ${error.message}`, 'error');
        currentSessionId = null;
        localStorageRemove('currentSessionId');
        updateSessionInfo();
    }
}

/**
 * Load saved session from localStorage
 */
async function loadSavedSession() {
    const savedSessionId = localStorageGet('currentSessionId');
    if (savedSessionId) {
        await loadSession(savedSessionId);
    }
}

/**
 * Update session info display
 */
function updateSessionInfo() {
    const sessionInfoEl = document.getElementById('sessionInfo');
    const footerSessionEl = document.getElementById('footerSessionText');

    if (currentSessionId) {
        const truncatedId = truncate(currentSessionId, 20);
        sessionInfoEl.innerHTML = `
            <i class="fas fa-check-circle text-success"></i>
            Session: <code>${truncatedId}</code>
        `;
        footerSessionEl.textContent = truncatedId;

        // Enable buttons
        document.getElementById('exportHistoryBtn').disabled = false;
        document.getElementById('clearHistoryBtn').disabled = false;
    } else {
        sessionInfoEl.textContent = 'No active session';
        footerSessionEl.textContent = 'None';

        // Disable buttons
        document.getElementById('exportHistoryBtn').disabled = true;
        document.getElementById('clearHistoryBtn').disabled = true;
    }
}

/**
 * Submit a player turn
 */
async function submitTurn() {
    if (!currentSessionId || isProcessingTurn) return;

    const commandInput = document.getElementById('playerCommandInput');
    const playerCommand = commandInput.value.trim();

    if (!playerCommand) {
        showToast('Please enter a command', 'warning');
        return;
    }

    try {
        isProcessingTurn = true;
        updateInputState(false);

        // Show player command
        appendToGameOutput({
            type: 'player',
            content: playerCommand,
            timestamp: new Date().toISOString(),
        });

        // Clear input
        commandInput.value = '';
        updateCharCount();

        // Show progress
        showTurnProgress();

        // Start polling progress
        startProgressPolling();

        // Submit turn
        const turnResult = await GameAPI.submitTurn(currentSessionId, playerCommand);

        // Stop polling
        stopProgressPolling();
        hideTurnProgress();

        // Display turn results
        displayTurnResults(turnResult);

        showToast('Turn completed successfully', 'success');

    } catch (error) {
        stopProgressPolling();
        hideTurnProgress();
        showToast(`Turn failed: ${error.message}`, 'error');

        appendToGameOutput({
            type: 'error',
            content: `Error: ${error.message}`,
            timestamp: new Date().toISOString(),
        });

    } finally {
        isProcessingTurn = false;
        updateInputState(true);
    }
}

/**
 * Start polling turn progress
 */
function startProgressPolling() {
    if (progressPollInterval) return;

    progressPollInterval = setInterval(async () => {
        try {
            const progress = await GameAPI.getProgress(currentSessionId);
            updateTurnProgress(progress);
        } catch (error) {
            console.error('Progress polling error:', error);
        }
    }, 500);
}

/**
 * Stop polling turn progress
 */
function stopProgressPolling() {
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
    }
}

/**
 * Update turn progress display
 * @param {object} progress - Progress data
 */
function updateTurnProgress(progress) {
    const progressBar = document.getElementById('turnProgressBar');
    const progressText = document.getElementById('turnProgressText');

    const percentage = Math.round((progress.progress || 0) * 100);
    progressBar.style.width = `${percentage}%`;

    let text = 'Processing...';
    if (progress.current_phase) {
        text = progress.current_phase;
        if (progress.current_agent) {
            text += ` - ${progress.current_agent}`;
        }
    }
    progressText.textContent = text;
}

/**
 * Show turn progress section
 */
function showTurnProgress() {
    document.getElementById('turnProgressSection').style.display = 'block';
    document.getElementById('turnProgressBar').style.width = '0%';
    document.getElementById('turnProgressText').textContent = 'Starting...';
}

/**
 * Hide turn progress section
 */
function hideTurnProgress() {
    document.getElementById('turnProgressSection').style.display = 'none';
}

/**
 * Update input state (enabled/disabled)
 * @param {boolean} enabled - Whether input should be enabled
 */
function updateInputState(enabled) {
    document.getElementById('playerCommandInput').disabled = !enabled;
    document.getElementById('submitTurnBtn').disabled = !enabled || !currentSessionId;
    document.getElementById('clearCommandBtn').disabled = !enabled;
}

/**
 * Display turn results in game output
 * @param {object} turnResult - Turn result data
 */
function displayTurnResults(turnResult) {
    // Turn separator
    const turnNumber = turnResult.turn_number || '?';
    appendToGameOutput({
        type: 'turn_separator',
        turnNumber: turnNumber,
    });

    // Check for player win/loss status - handle as game-ending events
    if (turnResult.player_loses) {
        // Display large red banner for player loss
        appendToGameOutput({
            type: 'player_loses_banner',
            content: 'Player Loses!',
        });

        // Display disqualification with content and reason
        let disqualificationContent = 'You\'re disqualified!\n\n';
        disqualificationContent += 'Disqualifying Response: ' + turnResult.player_command + '\n';
        if (turnResult.user_validation && turnResult.user_validation.reason) {
            disqualificationContent += 'Reason: ' + turnResult.user_validation.reason;
        }

        appendToGameOutput({
            type: 'player_loses',
            content: disqualificationContent,
            validation: turnResult.user_validation,
        });

        /*
        // Display the disqualification message from narrator (if available)
        if (turnResult.narrator_output && turnResult.narrator_output.content) {
            appendToGameOutput({
                type: 'disqualification_message',
                content: turnResult.narrator_output.content,
                citations: turnResult.narrator_output.citations,
            });
        } else if (turnResult.metadata?.disqualification_reason) {
            // Fallback to metadata if narrator output not available
            appendToGameOutput({
                type: 'disqualification_message',
                content: turnResult.metadata.disqualification_reason,
                citations: [],
            });
        }
            */

        // Show game over message
        appendToGameOutput({
            type: 'game_over',
            content: 'Game Over! Click \'New Game\' if you\'d like to play again.',
        });

        // Disable input - game is over
        updateInputState(false);
        document.getElementById('submitTurnBtn').disabled = true;

        // Update game-over state in UI
        updateGameOverState(true);

        // Save game-over state to localStorage
        localStorageSet(`gameOver_${currentSessionId}`, true);

        return; // Don't display other outputs
    } else if (turnResult.player_wins) {
        // Display large green banner for player win
        appendToGameOutput({
            type: 'player_wins_banner',
            content: 'Player Wins!',
        });

        // Get agent name from NPC output if available
        let agentName = 'Agent';
        if (turnResult.npc_output?.metadata?.npc_name) {
            agentName = turnResult.npc_output.metadata.npc_name;
        } else if (turnResult.narrator_output) {
            agentName = 'Narrator';
        }

        // Display disqualification with content and reason
        let disqualificationContent = `${agentName} is disqualified!\n\n`;
        let foundResponse = false;
        if (turnResult.metadata?.original_agent_response) {
            disqualificationContent += 'metadata.Original Agent Response: ' + turnResult.metadata.original_agent_response + '\n\n';
            foundResponse = true;
        } 
        if (turnResult.narrator_output?.content) {
            disqualificationContent += 'Narrator Response: ' + turnResult.narrator_output.content + '\n\n';  
            foundResponse = true;         
        }
        if (foundResponse == false) {
            disqualificationContent += 'No response found in turnResult';

        }

        if (turnResult.agent_validation && turnResult.agent_validation.reason) {
            disqualificationContent += 'Reason: ' + turnResult.agent_validation.reason;
        }

        appendToGameOutput({
            type: 'player_wins',
            content: disqualificationContent,
            validation: turnResult.agent_validation,
        });

        // Display the correction message from narrator (if available)
        if (turnResult.narrator_output && turnResult.narrator_output.content) {
            appendToGameOutput({
                type: 'correction_message',
                content: turnResult.narrator_output.content,
                citations: turnResult.narrator_output.citations,
            });
        } else if (turnResult.metadata?.disqualification_reason) {
            // Fallback to metadata if narrator output not available
            appendToGameOutput({
                type: 'correction_message',
                content: turnResult.metadata.disqualification_reason,
                citations: [],
            });
        }

        // Show game over message
        appendToGameOutput({
            type: 'game_over',
            content: 'Game Over! Click \'New Game\' if you\'d like to play again.',
        });

        // Disable input - game is over
        updateInputState(false);
        document.getElementById('submitTurnBtn').disabled = true;

        // Update game-over state in UI
        updateGameOverState(true);

        // Save game-over state to localStorage
        localStorageSet(`gameOver_${currentSessionId}`, true);

        return; // Don't display other outputs
    }

    // Normal game flow - no disqualification

    // Narrator output
    if (turnResult.narrator_output) {
        appendAgentOutput('Narrator', turnResult.narrator_output, 'narrator');
    }

    // Scene Planner output
    if (turnResult.scene_planner_output) {
        appendAgentOutput('Scene Planner', turnResult.scene_planner_output, 'scene-planner');
    }

    // NPC output
    if (turnResult.npc_output) {
        const npcName = turnResult.npc_output.metadata?.npc_name || 'NPC';
        appendAgentOutput(npcName, turnResult.npc_output, 'npc-manager');
    }

    // Rules Referee output (legacy)
    if (turnResult.rules_validation) {
        appendAgentOutput('Rules Referee', turnResult.rules_validation, 'rules-referee');
    }

    // Display validation results if present (for debugging/transparency)
    if (turnResult.user_validation && !turnResult.player_loses) {
        appendValidationInfo('User Prompt Validation', turnResult.user_validation);
    }
    if (turnResult.agent_validation && !turnResult.player_wins) {
        appendValidationInfo('Agent Response Validation', turnResult.agent_validation);
    }

    // Scroll to bottom
    scrollToBottom(document.getElementById('gameOutput'));
}

/**
 * Append agent output to game display
 * @param {string} agentName - Agent name
 * @param {object} output - Agent output data
 * @param {string} agentClass - CSS class for agent
 */
function appendAgentOutput(agentName, output, agentClass) {
    if (!output || !output.content) return;

    const content = escapeHtml(output.content);
    let citationsHtml = '';

    if (output.citations && output.citations.length > 0) {
        const citationsList = output.citations.map(c => `passage_${c}`).join(', ');
        citationsHtml = `
            <div class="citation mt-2">
                <i class="fas fa-quote-left"></i> Citations: ${citationsList}
            </div>
        `;
    }

    const errorHtml = output.error ? `
        <div class="alert alert-danger alert-sm mt-2 mb-0">
            <i class="fas fa-exclamation-triangle"></i> Error: ${escapeHtml(output.error)}
        </div>
    ` : '';

    const html = `
        <div class="card agent-output-card ${agentClass} mb-3">
            <div class="card-body">
                <h6 class="card-title">${agentName}</h6>
                <div class="card-text">${content.replace(/\n/g, '<br>')}</div>
                ${citationsHtml}
                ${errorHtml}
            </div>
        </div>
    `;

    document.getElementById('gameOutput').insertAdjacentHTML('beforeend', html);
}

/**
 * Append content to game output
 * @param {object} data - Output data
 */
function appendToGameOutput(data) {
    const gameOutput = document.getElementById('gameOutput');

    // Clear empty state
    if (gameOutput.querySelector('.text-muted.py-5')) {
        gameOutput.innerHTML = '';
    }

    if (data.type === 'system') {
        const html = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> ${escapeHtml(data.content).replace(/\n/g, '<br>')}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'player') {
        const html = `
            <div class="player-command">
                <strong><i class="fas fa-user"></i> You:</strong> ${escapeHtml(data.content)}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'error') {
        const html = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i> ${escapeHtml(data.content)}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'player_loses_banner') {
        const html = `
            <div class="alert alert-danger text-center" style="font-size: 1.5rem; font-weight: bold; padding: 1.5rem; margin: 1rem 0;">
                <i class="fas fa-times-circle"></i> ${escapeHtml(data.content)}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'player_wins_banner') {
        const html = `
            <div class="alert alert-success text-center" style="font-size: 1.5rem; font-weight: bold; padding: 1.5rem; margin: 1rem 0;">
                <i class="fas fa-trophy"></i> ${escapeHtml(data.content)}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'player_loses') {
        let suggestionsHtml = '';
        if (data.validation && data.validation.suggestions && data.validation.suggestions.length > 0) {
            const suggestionsList = data.validation.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('');
            suggestionsHtml = `
                <div class="mt-2">
                    <strong>Try instead:</strong>
                    <ul class="mb-0">${suggestionsList}</ul>
                </div>
            `;
        }
        const html = `
            <div class="alert alert-warning">
                <i class="fas fa-ban"></i> <div style="white-space: pre-line;">${escapeHtml(data.content)}</div>
                ${suggestionsHtml}
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'player_wins') {
        const html = `
            <div class="alert alert-success">
                <i class="fas fa-trophy"></i> <div style="white-space: pre-line;">${escapeHtml(data.content)}</div>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'disqualification_message') {
        let citationsHtml = '';
        if (data.citations && data.citations.length > 0) {
            const citationsList = data.citations.map(c => `passage_${c}`).join(', ');
            citationsHtml = `
                <div class="mt-2 small">
                    <i class="fas fa-quote-left"></i> Citations: ${citationsList}
                </div>
            `;
        }
        const html = `
            <div class="card mb-3 border-warning">
                <div class="card-body">
                    <h6 class="card-title text-warning">
                        <i class="fas fa-exclamation-triangle"></i> Disqualification Explanation
                    </h6>
                    <div class="card-text">${escapeHtml(data.content).replace(/\n/g, '<br>')}</div>
                    ${citationsHtml}
                </div>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'invalid_response') {
        const html = `
            <div class="card mb-3 border-danger">
                <div class="card-body">
                    <h6 class="card-title text-danger">
                        <i class="fas fa-times-circle"></i> Invalid Agent Response (Rejected)
                    </h6>
                    <div class="card-text text-muted">${escapeHtml(data.content).replace(/\n/g, '<br>')}</div>
                    <div class="mt-2 small">
                        <strong>Rejection reason:</strong> ${escapeHtml(data.reason)}
                    </div>
                </div>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'correction_message') {
        let citationsHtml = '';
        if (data.citations && data.citations.length > 0) {
            const citationsList = data.citations.map(c => `passage_${c}`).join(', ');
            citationsHtml = `
                <div class="mt-2 small">
                    <i class="fas fa-quote-left"></i> Citations: ${citationsList}
                </div>
            `;
        }
        const html = `
            <div class="card mb-3 border-info">
                <div class="card-body">
                    <h6 class="card-title text-info">
                        <i class="fas fa-info-circle"></i> Correction
                    </h6>
                    <div class="card-text">${escapeHtml(data.content).replace(/\n/g, '<br>')}</div>
                    ${citationsHtml}
                </div>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'game_over') {
        const html = `
            <div class="alert alert-primary text-center">
                <h5><i class="fas fa-flag-checkered"></i> ${escapeHtml(data.content)}</h5>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    } else if (data.type === 'turn_separator') {
        const html = `
            <div class="turn-separator">
                <h5><i class="fas fa-dice"></i> Turn ${data.turnNumber}</h5>
            </div>
        `;
        gameOutput.insertAdjacentHTML('beforeend', html);
    }

    scrollToBottom(gameOutput);
}

/**
 * Append validation info to game output
 * @param {string} title - Validation title
 * @param {object} validation - Validation data
 */
function appendValidationInfo(title, validation) {
    if (!validation) return;

    const statusClass = validation.approved ? 'success' : 'danger';
    const statusIcon = validation.approved ? 'check-circle' : 'times-circle';
    const statusText = validation.approved ? 'Approved' : 'Rejected';

    const html = `
        <div class="card validation-info mb-3">
            <div class="card-body">
                <h6 class="card-title">
                    <i class="fas fa-${statusIcon} text-${statusClass}"></i> ${title}: ${statusText}
                </h6>
                <p class="mb-1"><strong>Reason:</strong> ${escapeHtml(validation.reason)}</p>
                <p class="mb-0"><strong>Confidence:</strong> ${(validation.confidence * 100).toFixed(0)}%</p>
            </div>
        </div>
    `;

    document.getElementById('gameOutput').insertAdjacentHTML('beforeend', html);
}

/**
 * Clear game output
 */
function clearGameOutput() {
    const gameOutput = document.getElementById('gameOutput');
    gameOutput.innerHTML = '';
}

/**
 * Clear game history
 */
function clearGameHistory() {
    if (confirm('Are you sure you want to clear the game history? This cannot be undone.')) {
        clearGameOutput();
        showToast('Game history cleared', 'info');
    }
}

/**
 * Export game history
 */
function exportGameHistory() {
    const gameOutput = document.getElementById('gameOutput');
    const textContent = gameOutput.innerText || gameOutput.textContent;

    const filename = `game-history-${currentSessionId || 'unknown'}-${Date.now()}.txt`;
    downloadFile(filename, textContent, 'text/plain');

    showToast('Game history exported', 'success');
}
