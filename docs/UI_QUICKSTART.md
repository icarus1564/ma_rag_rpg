# UI Quick Start Guide

## Overview

The Multi-Agent RAG RPG now includes a web-based user interface for interactive gameplay and system monitoring.

## Starting the UI

### 1. Start the Server

```bash
# From the project root directory
make run

# Or manually:
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open Your Browser

Navigate to: **http://localhost:8000**

The root URL automatically redirects to the UI at `/ui/index.html`

## UI Tabs Overview

### Game Tab (Default)

**Purpose:** Play the RPG game interactively

**Features:**
- Create new game sessions
- Load existing sessions
- Submit player commands
- View agent responses in real-time
- Track turn progress
- Export game history

**Getting Started:**
1. Click **"New Game"** button
2. Optionally enter initial context
3. Click **"Start Game"**
4. Enter your first command
5. Click **"Submit Turn"**
6. Watch the progress bar as agents process your turn
7. Review agent outputs (Narrator, Scene Planner, NPC Manager, Rules Referee)

**Tips:**
- Commands are limited to 2000 characters
- Use Ctrl+Enter to submit quickly
- Your session ID is saved automatically in browser storage
- You can load a previous session by clicking "Load Session"

### Status Tab

**Purpose:** Monitor system health and component status

**Features:**
- System overview (uptime, active sessions, total turns)
- Corpus status (file, chunks, indices)
- Agent status table (health, call stats, response times)
- Retrieval system metrics
- Auto-refresh every 10 seconds

**What to Check:**
- **System Status:** Should show "Ready" or "Healthy"
- **Corpus Status:** Verify BM25 and Vector DB are "Loaded"/"Connected"
- **Agent Status:** All agents should show "Ready" status
- **Retrieval System:** Check hybrid retrieval is "Active"

**Troubleshooting:**
- If corpus shows "Not Loaded", run ingestion first
- If agents show "Error", check configuration files
- Click "Refresh Status" for manual update

### Configuration Tab

**Purpose:** View configuration and manage corpus

**Features:**
- Agent configuration overview
- Retrieval settings display
- Corpus upload and ingestion
- Links to configuration files

**Common Tasks:**

**Upload Corpus:**
1. Navigate to Configuration tab
2. Click "Choose File" under Corpus Management
3. Select a .txt file from your computer
4. Click "Upload & Ingest Corpus"
5. Wait for progress bar to complete
6. Check Status tab to verify ingestion

**View Configuration:**
- Agent list shows which agents are configured
- Retrieval settings display current fusion strategy
- Configuration files section links to YAML files

**Note:** Full configuration editing is done via YAML files:
- `config/config.yaml` - Main system configuration
- `config/agents.yaml` - Agent configurations

### Feedback Tab

**Purpose:** Submit feedback about the system

**Features:**
- Feedback submission form
- Type selection (Bug Report, Feature Request, etc.)
- Star rating (1-5)
- Session and agent context
- Character counter (0/5000)

**How to Submit:**
1. Select feedback type
2. Optionally enter session ID and select agent
3. Drag rating slider for star rating
4. Write your feedback
5. Click "Submit Feedback"

**Note:** Feedback is currently logged to browser console. Check DevTools Console to see submitted feedback.

## Common Workflows

### Playing a Full Game Session

1. **Start Server:** `make run`
2. **Open Browser:** http://localhost:8000
3. **Create Game:** Click "New Game", enter optional context
4. **Play Turns:**
   - Enter command: "Look around"
   - Submit turn
   - Read agent responses
   - Continue with next command
5. **Monitor:** Switch to Status tab to check system health
6. **Export:** Click "Export" to download game history

### Setting Up a New Corpus

1. **Prepare File:** Create or obtain a .txt corpus file
2. **Upload:** Configuration Tab → Choose File → Select corpus
3. **Ingest:** Click "Upload & Ingest Corpus"
4. **Wait:** Monitor progress bar (may take 1-5 minutes)
5. **Verify:** Status Tab → Corpus Status should show chunk count
6. **Test:** Game Tab → Start a new game to test retrieval

### Monitoring System During Gameplay

1. **Start Game:** Create session in Game tab
2. **Submit Turn:** Enter command and submit
3. **Switch Tabs:** While turn processes, check Status tab
4. **View Progress:** Game tab shows progress bar
5. **Check Metrics:** Status tab shows updated agent call stats
6. **Review Output:** Return to Game tab to see results

## Keyboard Shortcuts

- **Ctrl+Enter** (Game Tab): Submit turn
- **Tab**: Navigate between form fields
- **Escape**: Close modals

## Browser Requirements

**Supported Browsers:**
- Chrome 120+
- Firefox 120+
- Safari 17+
- Edge 120+

**Required:**
- JavaScript enabled
- localStorage available
- Modern ES6+ support

## Troubleshooting

### UI Won't Load

**Problem:** Browser shows "Cannot GET /" or blank page

**Solution:**
1. Check server is running: `ps aux | grep uvicorn`
2. Verify port 8000 is not in use: `lsof -i :8000`
3. Check browser console for errors (F12)
4. Try clearing browser cache

### "No Corpus Loaded" Error

**Problem:** Status tab shows corpus not loaded

**Solution:**
1. Navigate to Configuration tab
2. Upload a corpus file
3. Wait for ingestion to complete
4. Refresh Status tab

### Agents Show "Error" Status

**Problem:** Agent status table shows errors

**Solution:**
1. Check `config/agents.yaml` exists and is valid
2. Verify LLM provider is accessible (Ollama running, API key set)
3. Check server logs: `tail -f logs/app.log`
4. Restart server after fixing configuration

### Turn Submission Hangs

**Problem:** Progress bar stuck at 0% or specific agent

**Solution:**
1. Check browser console for errors
2. Verify LLM provider is responding
3. Check server logs for agent errors
4. Refresh page and try again
5. If persistent, check LLM configuration

### Session Not Persisting

**Problem:** Lose session when refreshing page

**Solution:**
1. Check browser allows localStorage
2. Verify not in private/incognito mode
3. Check browser settings for site data
4. Try a different browser

## Advanced Usage

### Multiple Sessions

Each browser tab maintains its own session via localStorage. To run multiple sessions:
1. Open new browser window (not tab)
2. Navigate to http://localhost:8000
3. Create new game session
4. Sessions are isolated per browser

### Exporting Game History

1. Game Tab → Click "Export" button
2. Choose location to save .txt file
3. File contains all turn history
4. Can be shared or archived

### API Access

The UI is built on top of the REST API. You can still access endpoints directly:

- **Health:** http://localhost:8000/health
- **New Game:** POST http://localhost:8000/api/new_game
- **Submit Turn:** POST http://localhost:8000/api/turn
- **System Status:** http://localhost:8000/api/status/system

See [README.md](../README.md) for full API documentation.

### Browser DevTools

**Console:** View API calls, errors, and feedback submissions
- Open: F12 → Console tab
- Shows: API requests, responses, errors

**Network:** Debug API requests
- Open: F12 → Network tab
- Filter: "api" or "ui"
- Shows: Request/response details, timing

**Application:** View localStorage
- Open: F12 → Application tab
- Storage → Local Storage
- Shows: currentSessionId and other stored data

## Performance Tips

1. **Auto-Refresh:** Status tab only refreshes when visible
2. **Session Storage:** Keep 1-2 active sessions max
3. **Large Corpus:** Ingestion may take several minutes
4. **Progress Polling:** Runs every 500ms during turns
5. **Browser Cache:** CSS/JS cached after first load

## Security Notes

**Development Mode:**
- CORS allows all origins
- No authentication required
- Runs on HTTP (not HTTPS)

**Production Deployment:**
- Use HTTPS
- Configure CORS properly
- Add authentication
- Use environment variables for secrets
- Enable rate limiting

## Getting Help

**Documentation:**
- [README.md](../README.md) - Full project documentation
- [PHASE_5_UI_DESIGN.md](PHASE_5_UI_DESIGN.md) - UI design document
- [PHASE_5_IMPLEMENTATION_SUMMARY.md](PHASE_5_IMPLEMENTATION_SUMMARY.md) - Implementation details

**Issues:**
- Check browser console (F12)
- Check server logs
- Review configuration files
- Test API endpoints directly

**Support:**
- GitHub Issues: Report bugs or request features
- Feedback Tab: Submit in-app feedback

## Next Steps

1. **Phase 6:** Metrics and evaluation visualization
2. **Future:** Advanced configuration editing in UI
3. **Future:** WebSocket for real-time updates
4. **Future:** Feedback backend with BM25 search

---

**Quick Reference:**

| Action | Location | Steps |
|--------|----------|-------|
| Start Game | Game Tab | New Game → Enter Context → Start |
| Submit Turn | Game Tab | Type Command → Submit Turn |
| Check Status | Status Tab | View metrics, click Refresh |
| Upload Corpus | Config Tab | Choose File → Upload & Ingest |
| Give Feedback | Feedback Tab | Fill Form → Submit |
| Export History | Game Tab | Click Export button |

**Default Port:** 8000
**UI URL:** http://localhost:8000
**API Docs:** http://localhost:8000/docs
