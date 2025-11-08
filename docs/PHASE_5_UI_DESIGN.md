# Phase 5: Simple UI Design Document

**Status:** ✅ APPROVED
**Date Created:** 2025-11-08
**Date Approved:** 2025-11-08
**Target Implementation:** Phase 5

---

## Executive Summary

This document outlines a comprehensive UI design for the Multi-Agent RAG RPG system. The UI provides a clean, intuitive interface for playing the game, monitoring system status, managing configuration, and collecting user feedback. The design leverages existing API endpoints and follows modern web development best practices.

### Key Design Goals

1. **User-Friendly Game Experience** - Simple interface for playing the game with real-time feedback
2. **Comprehensive Monitoring** - Clear visibility into system health and component status
3. **Flexible Configuration** - Easy-to-use interfaces for managing agents, corpus, and system settings
4. **Feedback Collection** - Structured mechanism for capturing and storing user feedback
5. **Responsive Design** - Works seamlessly on desktop and tablet devices
6. **Real-Time Updates** - Live progress tracking during turn processing

---

## Technology Stack

### Frontend Framework
**Choice:** Plain HTML/CSS/JavaScript with minimal dependencies

**Rationale:**
- No build toolchain required (faster development, easier deployment)
- Minimal dependencies reduces security surface area
- Easy to understand and maintain
- Compatible with all browsers
- Can be served directly by FastAPI static files

**Alternative Considered:** React/Vue
- Rejected due to complexity overhead for this use case
- Build process adds deployment complexity
- Not needed for this scale of UI

### UI Libraries

1. **Bootstrap 5.3** (via CDN)
   - Responsive grid system
   - Pre-built components (tabs, forms, cards, modals)
   - Professional look with minimal custom CSS
   - Excellent documentation

2. **Font Awesome 6** (via CDN)
   - Icon library for status indicators, buttons
   - Visual feedback for system states

3. **CodeMirror 6** (via CDN)
   - Syntax highlighting for configuration editing (YAML)
   - Line numbers and validation
   - Better UX than plain textarea

4. **Chart.js 4** (via CDN)
   - Future metrics visualization (Phase 6)
   - Lightweight charting library

### Backend Integration
- **FastAPI Static Files** - Serve HTML/CSS/JS
- **Existing REST API** - All endpoints already implemented
- **WebSocket** (Optional Enhancement) - Real-time progress updates

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser UI                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │   Game   │  Status  │  Config  │ Feedback │  Admin   │  │
│  │   Tab    │   Tab    │   Tab    │   Tab    │   Tab    │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│                           │                                  │
│                           │ (HTTP/WebSocket)                 │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           JavaScript API Client Layer                 │  │
│  │  - API wrapper functions                              │  │
│  │  - Error handling                                     │  │
│  │  - State management                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Existing API Endpoints                   │  │
│  │  /api/new_game, /api/turn, /api/state/...           │  │
│  │  /api/status/*, /ingest, /search                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              New API Endpoints                        │  │
│  │  /api/config/*, /api/feedback/*                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  - Game Sessions (in-memory)                                 │
│  - Configuration Files (YAML)                                │
│  - Feedback Database (BM25 index)                            │
│  - Corpus & Indices                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## UI Layout & Navigation

### Main Layout Structure

```html
┌────────────────────────────────────────────────────────────┐
│                    Header / Navigation                      │
│  Multi-Agent RAG RPG    [Game][Status][Config][Feedback]   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│                                                             │
│                    Tab Content Area                         │
│                   (Active Tab Displayed)                    │
│                                                             │
│                                                             │
├────────────────────────────────────────────────────────────┤
│                    Footer / Status Bar                      │
│  System: ● Ready   |   Corpus: h2g2.txt   |   Session: xyz │
└────────────────────────────────────────────────────────────┘
```

### Tab Navigation
- **Bootstrap Tabs** - Clean tab switching
- **Active State Indicators** - Show which tab is active
- **Badges** - Show notifications (e.g., "3 Feedback Items")
- **Responsive** - Stacks vertically on mobile

---

## Tab 1: Game Tab

### Purpose
Allow users to play the RPG game, submit commands, and view agent responses in real-time.

### Layout

```
┌────────────────────────────────────────────────────────────┐
│  SESSION CONTROLS                                           │
│  [New Game] [Current Session: abc-123] [Turn #5]           │
├────────────────────────────────────────────────────────────┤
│  INITIAL CONTEXT (New Game Only)                            │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Optional starting context...                           ││
│  └────────────────────────────────────────────────────────┘│
├────────────────────────────────────────────────────────────┤
│  PLAYER INPUT                                               │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Enter your command...                                  ││
│  └────────────────────────────────────────────────────────┘│
│  [Submit Turn] [Clear]                         ⏱ Ready     │
├────────────────────────────────────────────────────────────┤
│  TURN PROGRESS (When Processing)                            │
│  ████████░░░░░░░░░░ 40% - Executing NPCManager Agent...    │
├────────────────────────────────────────────────────────────┤
│  GAME OUTPUT (Scrollable)                                   │
│  ┌────────────────────────────────────────────────────────┐│
│  │ === Turn 5 ===                                         ││
│  │                                                         ││
│  │ Your Command: "Look around the tavern"                 ││
│  │                                                         ││
│  │ [Narrator]                                              ││
│  │ The tavern is dimly lit, filled with the smell of...   ││
│  │ [Citations: passage_42, passage_89]                    ││
│  │                                                         ││
│  │ [Rules Referee]                                         ││
│  │ ✓ Action is valid. No contradictions found.            ││
│  │                                                         ││
│  │ [NPC: Ford Prefect]                                     ││
│  │ "Don't panic," says Ford with a knowing grin...        ││
│  │ [Citations: passage_15]                                 ││
│  │                                                         ││
│  │ [⏱ Turn completed in 3.2s]                             ││
│  │                                                         ││
│  │ --- [Provide Feedback on this turn] ---                ││
│  │                                                         ││
│  │ === Turn 4 ===                                         ││
│  │ ...                                                     ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

### Features

#### Session Management
- **New Game Button**
  - Opens modal for initial context (optional)
  - Calls `POST /api/new_game`
  - Displays session ID and welcome message
  - Stores session ID in browser localStorage

- **Session Info Display**
  - Current session ID (truncated with tooltip for full ID)
  - Current turn number
  - Session duration/timestamp

- **Session Persistence**
  - Auto-save session ID to localStorage
  - Auto-load last session on page reload
  - Option to manually enter session ID

#### Input Area
- **Command Textarea**
  - Character counter (0/2000)
  - Auto-resize based on content
  - Enter to submit (Shift+Enter for newline)
  - Clear button to reset input

- **Validation**
  - Minimum 1 character
  - Maximum 2000 characters
  - Disable submit if invalid
  - Visual feedback for validation state

#### Progress Tracking
- **Progress Bar** (shown during turn processing)
  - Visual progress indicator
  - Current phase display
  - Current agent display
  - Estimated time remaining (optional)

- **Implementation**
  - Poll `GET /api/progress/{session_id}` every 500ms
  - Update progress bar and text
  - Hide when turn completes

#### Output Display
- **Turn-by-Turn Format**
  - Clear turn separators
  - Turn number header
  - Player command display
  - Agent outputs in sequence

- **Agent Output Cards**
  - Agent name as header
  - Content with proper formatting
  - Citations (expandable to show chunk content)
  - Execution time
  - Error indication if agent failed

- **Formatting**
  - Preserve line breaks
  - Markdown rendering (optional enhancement)
  - Syntax highlighting for citations
  - Auto-scroll to latest turn

- **Export Options**
  - Copy turn to clipboard
  - Export session history as JSON/text
  - Download complete game log

#### Feedback Integration
- **Per-Turn Feedback Button**
  - "Provide Feedback" link under each turn
  - Opens inline feedback form or modal
  - Pre-fills turn number and session ID
  - Quick ratings: 👍 👎 ⭐ (optional)

### API Integration

```javascript
// New Game
POST /api/new_game
{
  "initial_context": "Optional starting context"
}
→ { "session_id": "abc-123", "message": "...", "created_at": "..." }

// Submit Turn
POST /api/turn
{
  "session_id": "abc-123",
  "player_command": "Look around"
}
→ { "turn_number": 5, "narrator_output": {...}, ... }

// Get Progress (polling)
GET /api/progress/{session_id}
→ { "phase": "executing_agents", "current_agent": "NPCManager", ... }

// Get State (on page load)
GET /api/state/{session_id}
→ { "turn_count": 5, "current_scene": "...", ... }
```

### User Experience Flow

1. **User opens page**
   - Check localStorage for existing session
   - If found, load session state and display history
   - If not found, prompt to start new game

2. **User starts new game**
   - Click "New Game" button
   - Modal opens for optional initial context
   - Submit creates session via API
   - Session ID stored in localStorage
   - Welcome message displayed

3. **User submits turn**
   - Enter command in textarea
   - Click "Submit Turn"
   - Input disabled, progress bar shown
   - Poll progress endpoint every 500ms
   - Update progress bar with current phase/agent
   - When complete, display results
   - Re-enable input for next turn
   - Auto-scroll to latest turn

4. **User provides feedback**
   - Click "Provide Feedback" link
   - Feedback form appears inline
   - Submit feedback (saves to database)
   - Show confirmation message

---

## Tab 2: Status Tab

### Purpose
Display real-time system health, component status, and operational metrics.

### Layout

```
┌────────────────────────────────────────────────────────────┐
│  SYSTEM OVERVIEW                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Status: ● Ready         Uptime: 2h 34m               │  │
│  │ Active Sessions: 3      Total Turns: 127             │  │
│  │ Memory: 456 MB          CPU: 12%                     │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│  CORPUS STATUS                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Corpus: hitchhikers_guide.txt (1.2 MB)              │  │
│  │ Total Chunks: 2,450                                  │  │
│  │ BM25 Index: ✓ Loaded                                 │  │
│  │ Vector DB: ✓ Connected (ChromaDB)                    │  │
│  │ Collection: corpus_embeddings (2,450 documents)      │  │
│  │ Embedding Model: all-MiniLM-L6-v2 (384 dims)         │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│  AGENT STATUS                                               │
│  ┌────────────┬──────────┬─────────┬──────────┬─────────┐  │
│  │ Agent      │ LLM      │ Status  │ Calls    │ Avg Time│  │
│  ├────────────┼──────────┼─────────┼──────────┼─────────┤  │
│  │ Narrator   │ Ollama   │ ✓ Ready │ 127/127  │ 1.2s    │  │
│  │            │ mistral  │         │ (100%)   │         │  │
│  ├────────────┼──────────┼─────────┼──────────┼─────────┤  │
│  │ ScenePlan..│ Ollama   │ ✓ Ready │ 127/127  │ 0.8s    │  │
│  │            │ mistral  │         │ (100%)   │         │  │
│  ├────────────┼──────────┼─────────┼──────────┼─────────┤  │
│  │ NPCManager │ Ollama   │ ✓ Ready │ 98/127   │ 1.5s    │  │
│  │            │ mistral  │         │ (77%)    │         │  │
│  ├────────────┼──────────┼─────────┼──────────┼─────────┤  │
│  │ RulesRef...│ Ollama   │ ✓ Ready │ 127/127  │ 0.6s    │  │
│  │            │ mistral  │         │ (100%)   │         │  │
│  └────────────┴──────────┴─────────┴──────────┴─────────┘  │
│  [View Agent Details] [Test Connections] [Refresh]          │
├────────────────────────────────────────────────────────────┤
│  RETRIEVAL SYSTEM STATUS                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Hybrid Retrieval: ✓ Active                           │  │
│  │ BM25 Retriever: ✓ Ready (2,450 documents indexed)    │  │
│  │ Vector Retriever: ✓ Ready (ChromaDB connected)       │  │
│  │ Fusion Strategy: RRF (k=60)                          │  │
│  │ Query Rewriting: ✓ Enabled (expansion only)          │  │
│  │ Cache Hit Rate: 23.5% (48/204 queries)               │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Features

#### System Overview Card
- **System State Indicator**
  - Color-coded status: Green (Ready), Yellow (Processing), Red (Error)
  - State descriptions: "Ready", "Processing Request", "Processing Corpus", "Error"
  - Auto-refresh every 5 seconds

- **Metrics Display**
  - System uptime (HH:MM:SS format)
  - Active sessions count
  - Total turns processed (all-time)
  - Memory usage (if psutil available)
  - CPU usage (if psutil available)

- **Refresh Button**
  - Manual refresh of all status
  - Shows last updated timestamp

#### Corpus Status Card
- **Corpus Information**
  - File name and size
  - Total chunks indexed
  - Last ingestion timestamp

- **Index Status**
  - BM25 index: ✓ Loaded / ✗ Not Loaded / ⏳ Loading
  - Vector DB connection: ✓ Connected / ✗ Disconnected
  - Collection name and document count
  - Embedding model name and dimensions

- **Actions**
  - Re-index corpus button (opens confirmation modal)
  - View index statistics

#### Agent Status Table
- **Per-Agent Information**
  - Agent name
  - LLM provider and model
  - Connection status (✓ Ready, ✗ Failed, ⏳ Unknown)
  - Call statistics: successful/total (percentage)
  - Average response time
  - Last error message (if any)

- **Status Indicators**
  - Color-coded status icons
  - Tooltips with detailed information
  - Click to expand error details

- **Actions**
  - Test Connections: Ping all agent LLMs
  - View Details: Modal with full agent config and stats
  - Individual agent enable/disable toggle (future)

#### Retrieval System Card
- **Component Status**
  - BM25 retriever status and document count
  - Vector retriever status and provider
  - Fusion strategy and parameters
  - Query rewriting configuration

- **Performance Metrics**
  - Cache hit rate
  - Average retrieval time
  - Top K results setting
  - BM25/Vector weights

### API Integration

```javascript
// System Status
GET /api/status/system
→ { "status": "ready", "uptime_seconds": 9240, ... }

// Corpus Status
GET /api/status/corpus
→ { "corpus_file": "...", "total_chunks": 2450, ... }

// Agent Status
GET /api/status/agents
→ { "agents": [ { "name": "Narrator", "status": "ready", ... } ] }

// Retrieval Status
GET /api/status/retrieval
→ { "hybrid_enabled": true, "bm25_status": "ready", ... }

// Health Check (quick overview)
GET /health
→ { "status": "healthy", "components": {...} }
```

### User Experience
- **Auto-Refresh**: Poll status endpoints every 5-10 seconds
- **Real-Time Updates**: Visual indicators change color based on status
- **Expandable Details**: Click cards to see more information
- **Alerts**: Toast notifications for status changes (e.g., "Agent connection lost")

---

## Tab 3: Configuration Tab

### Purpose
Manage system configuration including agent settings, corpus management, and retrieval parameters.

### Layout

```
┌────────────────────────────────────────────────────────────┐
│  CONFIGURATION SECTIONS                                     │
│  [Agents] [Corpus & Ingestion] [Retrieval] [System]        │
├────────────────────────────────────────────────────────────┤
│  AGENTS SECTION                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Select Agent: [Narrator ▼]                             ││
│  │                                                         ││
│  │ Agent Name: [Narrator                              ]   ││
│  │                                                         ││
│  │ LLM Configuration:                                      ││
│  │   Provider:     [ollama ▼]                             ││
│  │   Model:        [mistral                           ]   ││
│  │   Temperature:  [0.7     ] (0.0 - 2.0)                 ││
│  │   Max Tokens:   [1000    ]                             ││
│  │   API Key:      [************                      ]   ││
│  │   Base URL:     [http://localhost:11434/v1         ]   ││
│  │                                                         ││
│  │ Retrieval Settings:                                     ││
│  │   Top K:        [5       ]                             ││
│  │   Query Template: [default ▼]                          ││
│  │                                                         ││
│  │ Prompt Templates:                                       ││
│  │   System Prompt:                                        ││
│  │   ┌──────────────────────────────────────────────────┐ ││
│  │   │ You are the Narrator for an interactive story...│ ││
│  │   │ [CodeMirror editor with YAML syntax highlight] │ ││
│  │   └──────────────────────────────────────────────────┘ ││
│  │                                                         ││
│  │   User Prompt Template:                                 ││
│  │   ┌──────────────────────────────────────────────────┐ ││
│  │   │ Retrieved Passages: {retrieved_chunks}...        │ ││
│  │   └──────────────────────────────────────────────────┘ ││
│  │                                                         ││
│  │ Status: ☑ Enabled                                      ││
│  │                                                         ││
│  │ [Test Agent Connection] [Save Changes] [Reset]         ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

### Sections

#### 1. Agents Configuration

**Features:**
- **Agent Selector Dropdown**
  - Select which agent to configure
  - Shows all 4 agents: Narrator, ScenePlanner, NPCManager, RulesReferee

- **Basic Settings**
  - Agent name (display name)
  - Enable/Disable toggle
  - Help text for each field

- **LLM Configuration**
  - Provider dropdown: OpenAI, Gemini, Ollama
  - Model text input (with suggestions)
  - Temperature slider (0.0 - 2.0)
  - Max tokens number input
  - API key input (masked, show/hide toggle)
  - Base URL input (for Ollama/custom endpoints)
  - Validation: required fields, format checking

- **Retrieval Settings**
  - Top K results (number input)
  - Query template selector (future: custom templates)

- **Prompt Templates**
  - CodeMirror editor for system prompt
  - CodeMirror editor for user prompt template
  - Syntax highlighting
  - Variable placeholders highlighted
  - Template validation (check for required variables)
  - Preview mode (show example with sample data)

- **Actions**
  - **Test Connection**: Ping LLM endpoint
  - **Save Changes**: Update agent config (requires restart warning)
  - **Reset**: Revert to last saved config
  - **Restore Defaults**: Reset to example config

**API Integration:**
```javascript
// Get Agent Config
GET /api/config/agents/{agent_name}
→ { "name": "Narrator", "llm": {...}, "persona_template": "...", ... }

// Update Agent Config
PUT /api/config/agents/{agent_name}
{ "name": "Narrator", "llm": {...}, ... }
→ { "success": true, "restart_required": true }

// Test Agent Connection
POST /api/config/agents/{agent_name}/test
→ { "success": true, "latency_ms": 234, "message": "..." }
```

#### 2. Corpus & Ingestion Section

```
┌────────────────────────────────────────────────────────────┐
│ CORPUS MANAGEMENT                                           │
│                                                             │
│ Current Corpus: hitchhikers_guide.txt (1.2 MB)             │
│ Total Chunks: 2,450                                         │
│ Last Indexed: 2025-11-07 10:23:45                          │
│                                                             │
│ Upload New Corpus:                                          │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ [Choose File] hitchhikers_guide.txt                  │   │
│ └─────────────────────────────────────────────────────┘   │
│ [Upload & Ingest]                                           │
│                                                             │
│ Ingestion Settings:                                         │
│   Chunk Size:        [500      ] characters                │
│   Chunk Overlap:     [50       ] characters                │
│   Embedding Model:   [all-MiniLM-L6-v2 ▼]                  │
│   ☑ Create BM25 Index                                      │
│   ☑ Create Vector Index                                    │
│                                                             │
│ [Re-index Current Corpus] [View Corpus Preview]            │
│                                                             │
│ INGESTION PROGRESS (when active)                            │
│ ████████████░░░░░░░░ 60% - Generating embeddings...        │
│ Processed 1,470 / 2,450 chunks                             │
│ Estimated time remaining: 2m 15s                            │
└────────────────────────────────────────────────────────────┘
```

**Features:**
- **Current Corpus Info**
  - File name, size, chunk count
  - Last indexed timestamp
  - View raw corpus (modal/new tab)
  - Download current corpus

- **Upload New Corpus**
  - File picker (accepts .txt files)
  - File validation (size limits, format)
  - Preview before upload
  - Upload progress bar

- **Ingestion Settings**
  - Chunk size (100-2000 characters)
  - Chunk overlap (0-500 characters)
  - Embedding model selector
  - Options: create BM25, create vector index

- **Ingestion Progress**
  - Real-time progress bar
  - Current step indicator
  - Processed/total count
  - Estimated time remaining
  - Cancel button

- **Actions**
  - Re-index existing corpus (same settings)
  - Change settings and re-index
  - View chunked output (preview modal)

**API Integration:**
```javascript
// Upload Corpus
POST /api/corpus/upload
FormData: { file: <file> }
→ { "filename": "...", "size": 1234567, "path": "..." }

// Ingest Corpus
POST /ingest
{
  "corpus_path": "data/corpus.txt",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "embedding_model": "all-MiniLM-L6-v2"
}
→ { "success": true, "task_id": "abc-123" }

// Get Ingestion Progress
GET /api/corpus/ingest/progress/{task_id}
→ { "status": "processing", "progress": 0.6, "current_step": "...", ... }

// Get Current Corpus Info
GET /api/corpus/current
→ { "filename": "...", "size": 1234567, "chunks": 2450, ... }
```

#### 3. Retrieval Configuration Section

```
┌────────────────────────────────────────────────────────────┐
│ RETRIEVAL SETTINGS                                          │
│                                                             │
│ Hybrid Retrieval:                                           │
│   ☑ Enable Hybrid Retrieval                                │
│   BM25 Weight:       [0.5      ] (0.0 - 1.0) ━━━━━━━━━●    │
│   Vector Weight:     [0.5      ] (0.0 - 1.0) ━━━━━━━━━●    │
│   Top K Results:     [10       ]                           │
│   Fusion Strategy:   [RRF ▼]   (RRF, Weighted)            │
│   RRF K Parameter:   [60       ] (only for RRF)           │
│                                                             │
│ Query Rewriting:                                            │
│   ☑ Enable Query Rewriting                                │
│   ☑ Synonym Expansion                                      │
│   ☐ Query Decomposition (future)                          │
│   ☐ LLM-Based Rewriting (future)                           │
│                                                             │
│ Cache Settings:                                             │
│   ☑ Enable Result Caching                                 │
│   Cache TTL:         [300      ] seconds                   │
│   Max Cache Size:    [100      ] entries                   │
│   [Clear Cache Now]                                         │
│                                                             │
│ [Test Retrieval] [Save Changes] [Reset]                    │
└────────────────────────────────────────────────────────────┘
```

**Features:**
- **Hybrid Retrieval Settings**
  - Enable/disable hybrid retrieval
  - Weight sliders (ensure they sum to 1.0)
  - Top K results
  - Fusion strategy selector
  - RRF K parameter (conditional display)

- **Query Rewriting**
  - Enable/disable toggle
  - Individual feature toggles
  - Future: LLM-based rewriting settings

- **Cache Settings**
  - Enable/disable caching
  - TTL in seconds
  - Max cache size
  - Clear cache action

- **Test Retrieval**
  - Input test query
  - Show retrieval results
  - Compare BM25 vs Vector vs Hybrid

**API Integration:**
```javascript
// Get Retrieval Config
GET /api/config/retrieval
→ { "bm25_weight": 0.5, "vector_weight": 0.5, ... }

// Update Retrieval Config
PUT /api/config/retrieval
{ "bm25_weight": 0.6, "vector_weight": 0.4, ... }
→ { "success": true, "restart_required": false }

// Test Retrieval
POST /api/retrieval/test
{ "query": "test query", "top_k": 10 }
→ { "results": [...], "bm25_only": [...], "vector_only": [...] }

// Clear Cache
POST /api/retrieval/cache/clear
→ { "success": true, "entries_cleared": 48 }
```

#### 4. System Configuration Section

```
┌────────────────────────────────────────────────────────────┐
│ SYSTEM SETTINGS                                             │
│                                                             │
│ Session Management:                                         │
│   Memory Window Size: [10      ] turns                     │
│   Max Tokens:         [8000    ]                           │
│   ☑ Sliding Window                                         │
│   Session TTL:        [3600    ] seconds (1 hour)          │
│                                                             │
│ API Settings:                                               │
│   Host:               [0.0.0.0                         ]   │
│   Port:               [8000    ]                           │
│   Log Level:          [INFO ▼]  (DEBUG, INFO, WARNING)    │
│                                                             │
│ Logging:                                                    │
│   Log Level:          [INFO ▼]                             │
│   Format:             [JSON ▼]  (JSON, Text)               │
│   Log File:           [logs/app.log                    ]   │
│   [View Logs]                                               │
│                                                             │
│ [Save Changes] [Restart Required] [Export Config]          │
└────────────────────────────────────────────────────────────┘
```

**Features:**
- **Session Management**
  - Memory window size
  - Max tokens
  - Sliding window toggle
  - Session TTL

- **API Settings**
  - Host and port (read-only, requires restart)
  - Log level

- **Logging**
  - Log level selector
  - Format selector (JSON/Text)
  - Log file path
  - View logs (modal or new tab)

- **Actions**
  - Save changes
  - Export full config (download YAML)
  - Import config (upload YAML)
  - Restart required indicator

**API Integration:**
```javascript
// Get System Config
GET /api/config/system
→ { "session": {...}, "api": {...}, "logging": {...} }

// Update System Config
PUT /api/config/system
{ "session": {...}, ... }
→ { "success": true, "restart_required": true }

// Export Config
GET /api/config/export
→ YAML file download

// Import Config
POST /api/config/import
FormData: { file: <config.yaml> }
→ { "success": true, "validation_errors": [] }

// View Logs
GET /api/logs
?lines=100&level=INFO&since=2025-11-08T10:00:00
→ { "logs": [...] }
```

### User Experience
- **Validation**: Real-time validation with clear error messages
- **Help Text**: Tooltips and inline help for all settings
- **Unsaved Changes**: Warn user before leaving page
- **Restart Required**: Clear indicator when restart needed
- **Test Before Save**: Test connections/settings before applying

---

## Tab 4: Feedback Tab

### Purpose
Collect user feedback on game turns and system performance, and display aggregated feedback for review.

### Layout

```
┌────────────────────────────────────────────────────────────┐
│ FEEDBACK OVERVIEW                                           │
│ Total Feedback Items: 42   |   Recent: 8 (last 24h)        │
│ [View All] [Filter] [Export]                                │
├────────────────────────────────────────────────────────────┤
│ SUBMIT NEW FEEDBACK                                         │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Feedback Type: [Bug Report ▼]                          │ │
│ │                                                         │ │
│ │ Related To:                                             │ │
│ │   Session ID:  [abc-123                            ]   │ │
│ │   Turn Number: [5       ]                              │ │
│ │   Agent:       [All ▼]                                 │ │
│ │                                                         │ │
│ │ Rating: ⭐⭐⭐⭐☆ (4/5)                                  │ │
│ │                                                         │ │
│ │ Feedback:                                               │ │
│ │ ┌────────────────────────────────────────────────────┐ │ │
│ │ │ The narrator's description was great, but the NPC │ │ │
│ │ │ response seemed out of character...                │ │ │
│ │ └────────────────────────────────────────────────────┘ │ │
│ │                                                         │ │
│ │ [Submit Feedback] [Clear]                              │ │
│ └────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────┤
│ FEEDBACK LIST                                               │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ [2025-11-08 10:23] ⭐⭐⭐⭐⭐ Feature Request           │ │
│ │ Session: abc-123 | Turn: 5 | Agent: NPCManager         │ │
│ │ "Would be great to have more NPC dialogue options..."  │ │
│ │ [View Details] [Mark Resolved] [Reply]                 │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ [2025-11-08 09:45] ⭐⭐⭐☆☆ Bug Report                │ │
│ │ Session: xyz-789 | Turn: 12 | Agent: RulesReferee      │ │
│ │ "Rules validation failed incorrectly..."               │ │
│ │ [View Details] [Mark Resolved] [Reply]                 │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ ...                                                     │ │
│ └────────────────────────────────────────────────────────┘ │
│ [Load More] Showing 10 of 42                                │
└────────────────────────────────────────────────────────────┘
```

### Features

#### Feedback Submission Form
- **Feedback Type**
  - Dropdown: Bug Report, Feature Request, General Feedback, Agent Behavior, Performance Issue

- **Context Fields**
  - Session ID (auto-filled from current session or manual input)
  - Turn number (optional)
  - Agent (dropdown: All, Narrator, ScenePlanner, NPCManager, RulesReferee)

- **Rating System**
  - 5-star rating (optional)
  - Quick sentiment: 👍 👎 😐

- **Feedback Text**
  - Textarea (max 5000 characters)
  - Character counter
  - Markdown support (optional)

- **Attachments** (future)
  - Upload screenshots
  - Attach turn output JSON

- **Actions**
  - Submit (validate required fields)
  - Clear form
  - Preview (show formatted feedback)

#### Feedback List/Display
- **List View**
  - Reverse chronological order (newest first)
  - Pagination (10 per page)
  - Search/filter by type, agent, date range, rating

- **Feedback Card**
  - Timestamp
  - Rating stars
  - Type badge
  - Session ID, turn number, agent
  - Feedback text (truncated, expand to view full)
  - Actions: View Details, Mark Resolved, Reply

- **Filters**
  - By type (multi-select)
  - By agent (multi-select)
  - By rating (slider)
  - By date range (date picker)
  - By status (Open, Resolved, All)

- **Export**
  - Export all feedback as JSON/CSV
  - Export filtered results
  - Date range export

#### Feedback Details Modal
- **Full Feedback Display**
  - All metadata (timestamp, session, turn, agent, type, rating)
  - Full feedback text
  - Attached context (turn output if available)
  - User information (if tracked)

- **Actions**
  - Mark as Resolved/Unresolve
  - Add admin reply/notes
  - View related session/turn (link to Game tab)
  - Export single feedback item

#### Feedback Storage
- **BM25 Index Integration**
  - Store feedback as documents in separate BM25 index
  - Enable full-text search
  - Metadata fields: type, agent, rating, timestamp, session_id, turn_number, status

- **Schema**
  ```json
  {
    "id": "fb-uuid-123",
    "timestamp": "2025-11-08T10:23:45Z",
    "type": "bug_report",
    "session_id": "abc-123",
    "turn_number": 5,
    "agent": "NPCManager",
    "rating": 3,
    "sentiment": "negative",
    "feedback_text": "...",
    "status": "open",
    "admin_reply": null,
    "resolved_at": null
  }
  ```

### API Integration

```javascript
// Submit Feedback
POST /api/feedback
{
  "type": "bug_report",
  "session_id": "abc-123",
  "turn_number": 5,
  "agent": "NPCManager",
  "rating": 3,
  "feedback_text": "..."
}
→ { "id": "fb-uuid-123", "created_at": "...", "success": true }

// Get Feedback List
GET /api/feedback
?type=bug_report&agent=NPCManager&rating_min=1&rating_max=5
&date_from=2025-11-01&date_to=2025-11-08&status=open
&page=1&limit=10
→ {
  "feedback_items": [...],
  "total": 42,
  "page": 1,
  "pages": 5
}

// Get Single Feedback
GET /api/feedback/{feedback_id}
→ { "id": "fb-uuid-123", "timestamp": "...", ... }

// Update Feedback Status
PATCH /api/feedback/{feedback_id}
{ "status": "resolved", "admin_reply": "Fixed in version 2.1" }
→ { "success": true }

// Search Feedback (BM25)
POST /api/feedback/search
{ "query": "NPC dialogue", "limit": 20 }
→ { "results": [...], "total": 15 }

// Export Feedback
GET /api/feedback/export
?format=json&type=bug_report&date_from=2025-11-01
→ JSON/CSV download
```

### User Experience
- **Quick Feedback**: Link from game tab pre-fills context
- **Search**: Full-text search across all feedback
- **Analytics**: Summary statistics (avg rating, common issues)
- **Notifications**: Toast when feedback submitted successfully

---

## Tab 5: Admin Tab (Optional Future Enhancement)

### Purpose
Advanced administrative functions for power users and developers.

### Features (Future)
- **Database Management**
  - View/clear sessions
  - Backup/restore databases
  - Orphan cleanup

- **Performance Profiling**
  - Agent execution timings
  - Retrieval performance
  - Memory profiling

- **User Management** (if auth added)
  - User accounts
  - Permissions
  - Usage quotas

- **Experiments/A-B Testing**
  - Test different prompts
  - Compare retrieval strategies
  - Evaluate agent performance

---

## Responsive Design

### Breakpoints
- **Desktop** (>= 992px): Full layout, side-by-side panels
- **Tablet** (768px - 991px): Stacked layout, full-width panels
- **Mobile** (< 768px): Single column, collapsible sections

### Mobile Optimizations
- **Game Tab**: Full-screen command input when focused
- **Status Tab**: Cards stack vertically
- **Config Tab**: Accordion-style sections
- **Feedback Tab**: Simplified list view

---

## File Structure

```
src/
├── api/
│   ├── app.py                          # FastAPI app (enhanced)
│   ├── endpoints/
│   │   ├── game.py                     # Existing game endpoints
│   │   ├── status.py                   # Existing status endpoints
│   │   ├── config.py                   # NEW: Configuration endpoints
│   │   ├── feedback.py                 # NEW: Feedback endpoints
│   │   └── corpus.py                   # NEW: Corpus management endpoints
│   ├── schemas/
│   │   ├── config_schemas.py           # NEW: Config API schemas
│   │   └── feedback_schemas.py         # NEW: Feedback API schemas
│   └── static/                         # NEW: Static files
│       ├── index.html                  # Main UI entry point
│       ├── css/
│       │   ├── main.css                # Custom styles
│       │   └── themes.css              # Color themes (optional)
│       └── js/
│           ├── main.js                 # Main application logic
│           ├── api-client.js           # API wrapper functions
│           ├── game-tab.js             # Game tab logic
│           ├── status-tab.js           # Status tab logic
│           ├── config-tab.js           # Config tab logic
│           ├── feedback-tab.js         # Feedback tab logic
│           └── utils.js                # Shared utilities

src/core/
├── config_manager.py                   # NEW: Dynamic config management
└── feedback_store.py                   # NEW: Feedback storage using BM25

data/
└── feedback/                           # NEW: Feedback storage
    ├── feedback_index.pkl              # BM25 index for feedback
    └── feedback_metadata.json          # Feedback metadata
```

---

## API Endpoints Summary

### New Endpoints Required

#### Configuration Endpoints (`/api/config/`)

```python
# Agent Configuration
GET    /api/config/agents                    # List all agents
GET    /api/config/agents/{agent_name}       # Get agent config
PUT    /api/config/agents/{agent_name}       # Update agent config
POST   /api/config/agents/{agent_name}/test  # Test agent connection

# Retrieval Configuration
GET    /api/config/retrieval                 # Get retrieval config
PUT    /api/config/retrieval                 # Update retrieval config
POST   /api/config/retrieval/test            # Test retrieval
POST   /api/config/retrieval/cache/clear     # Clear cache

# System Configuration
GET    /api/config/system                    # Get system config
PUT    /api/config/system                    # Update system config
GET    /api/config/export                    # Export config YAML
POST   /api/config/import                    # Import config YAML
```

#### Corpus Management Endpoints (`/api/corpus/`)

```python
POST   /api/corpus/upload                    # Upload new corpus file
GET    /api/corpus/current                   # Get current corpus info
GET    /api/corpus/preview                   # Preview corpus chunks
POST   /api/corpus/re-index                  # Re-index current corpus
GET    /api/corpus/ingest/progress/{task_id} # Get ingestion progress
```

#### Feedback Endpoints (`/api/feedback/`)

```python
POST   /api/feedback                         # Submit feedback
GET    /api/feedback                         # List feedback (with filters)
GET    /api/feedback/{feedback_id}           # Get single feedback
PATCH  /api/feedback/{feedback_id}           # Update feedback (status, reply)
DELETE /api/feedback/{feedback_id}           # Delete feedback
POST   /api/feedback/search                  # Search feedback (BM25)
GET    /api/feedback/export                  # Export feedback
GET    /api/feedback/stats                   # Feedback statistics
```

#### Logging Endpoint (`/api/logs/`)

```python
GET    /api/logs                             # Get recent logs (paginated)
```

---

## Implementation Details

### Configuration Management

#### Dynamic Config Updates
- **Runtime Updates**: Some settings (retrieval weights, cache) can update without restart
- **Restart Required**: Agent LLM changes, system settings require restart
- **Config Persistence**: Write changes to YAML files
- **Validation**: Pydantic schemas validate all config updates
- **Rollback**: Keep backup of last known good config

#### Config Manager Class

```python
class ConfigManager:
    """Manages runtime configuration updates."""

    def __init__(self, config_path: str, agents_config_path: str):
        self.config_path = config_path
        self.agents_config_path = agents_config_path
        self.config = self.load_config()
        self.agents_config = self.load_agents_config()

    def update_agent_config(self, agent_name: str, new_config: dict) -> dict:
        """Update agent configuration and save to file."""
        # Validate with Pydantic
        # Update in-memory config
        # Write to YAML file
        # Return success/failure + restart_required flag
        pass

    def update_retrieval_config(self, new_config: dict) -> dict:
        """Update retrieval configuration (runtime update)."""
        # Validate
        # Update retrieval_manager settings
        # Save to file
        # Return success
        pass

    def export_config(self) -> str:
        """Export current config as YAML."""
        pass

    def import_config(self, yaml_content: str) -> dict:
        """Import and validate config from YAML."""
        pass
```

### Feedback Storage

#### Feedback Store Class

```python
class FeedbackStore:
    """Manages feedback storage using BM25 index."""

    def __init__(self, index_path: str, metadata_path: str):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = self.load_index()
        self.metadata = self.load_metadata()

    def add_feedback(self, feedback: FeedbackItem) -> str:
        """Add new feedback item."""
        # Generate UUID
        # Add to BM25 index
        # Store metadata
        # Persist to disk
        # Return feedback ID
        pass

    def search_feedback(self, query: str, filters: dict) -> list:
        """Search feedback using BM25."""
        # BM25 search on feedback_text
        # Apply filters (type, agent, rating, date)
        # Return ranked results
        pass

    def get_feedback(self, feedback_id: str) -> dict:
        """Get single feedback item by ID."""
        pass

    def update_feedback(self, feedback_id: str, updates: dict) -> bool:
        """Update feedback (status, reply)."""
        pass

    def get_statistics(self, filters: dict) -> dict:
        """Get feedback statistics."""
        # Average rating
        # Count by type
        # Count by agent
        # Recent trends
        pass

    def export_feedback(self, filters: dict, format: str) -> str:
        """Export feedback as JSON or CSV."""
        pass
```

#### Feedback Schema

```python
class FeedbackItem(BaseModel):
    """Feedback item schema."""
    id: str = Field(default_factory=lambda: f"fb-{uuid4()}")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    type: FeedbackType  # Enum: bug_report, feature_request, general, agent_behavior, performance
    session_id: Optional[str] = None
    turn_number: Optional[int] = None
    agent: Optional[str] = None  # All, Narrator, ScenePlanner, NPCManager, RulesReferee
    rating: Optional[int] = Field(None, ge=1, le=5)
    sentiment: Optional[str] = None  # positive, negative, neutral
    feedback_text: str = Field(..., min_length=1, max_length=5000)
    status: str = Field(default="open")  # open, resolved, archived
    admin_reply: Optional[str] = None
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Corpus Upload & Ingestion

#### Background Task Processing
- Use FastAPI's `BackgroundTasks` for async ingestion
- Return task ID immediately
- Client polls progress endpoint

```python
from fastapi import BackgroundTasks

@router.post("/ingest")
async def ingest_corpus(
    request: IngestRequest,
    background_tasks: BackgroundTasks
):
    task_id = str(uuid4())
    background_tasks.add_task(
        run_ingestion,
        task_id,
        request.corpus_path,
        request.chunk_size,
        request.chunk_overlap
    )
    return {"task_id": task_id, "status": "started"}

# Progress tracking
ingestion_progress = {}  # Global dict (or Redis for production)

def run_ingestion(task_id: str, corpus_path: str, ...):
    """Background ingestion task."""
    ingestion_progress[task_id] = {
        "status": "processing",
        "progress": 0.0,
        "current_step": "Loading corpus",
        "total_chunks": 0,
        "processed_chunks": 0
    }

    # Run ingestion pipeline with progress callbacks
    # Update ingestion_progress dict

    ingestion_progress[task_id]["status"] = "completed"
```

### Static File Serving

```python
# In app.py
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="src/api/static", html=True), name="ui")

# Root redirect to UI
@app.get("/")
async def root():
    return RedirectResponse(url="/ui/index.html")
```

### Real-Time Updates

#### Polling (Initial Implementation)
- **Game Progress**: Poll `/api/progress/{session_id}` every 500ms during turn
- **Status Updates**: Poll `/api/status/*` every 5-10 seconds
- **Ingestion Progress**: Poll `/api/corpus/ingest/progress/{task_id}` every 1 second

#### WebSocket (Future Enhancement)
- **WebSocket Endpoint**: `/ws/{session_id}`
- **Events**: turn_progress, turn_complete, status_update
- **Benefits**: Lower latency, less overhead, true real-time

```python
# Future WebSocket implementation
from fastapi import WebSocket

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    # Send real-time progress updates
    # Broadcast status changes
```

---

## User Workflows

### Workflow 1: New User First-Time Setup

1. Open application at `http://localhost:8000/`
2. Redirected to UI (`/ui/index.html`)
3. Status Tab shows: "No corpus loaded"
4. Navigate to **Config Tab** → **Corpus & Ingestion**
5. Upload corpus file (e.g., `hitchhikers_guide.txt`)
6. Click "Upload & Ingest"
7. Progress bar shows ingestion progress
8. Navigate to **Config Tab** → **Agents**
9. Configure LLM settings for each agent (provider, model, API key)
10. Test connections for each agent
11. Save changes
12. Navigate to **Game Tab**
13. Click "New Game"
14. Enter initial context (optional)
15. Start playing!

### Workflow 2: Playing the Game

1. Navigate to **Game Tab**
2. If no active session, click "New Game"
3. Enter player command in textarea
4. Click "Submit Turn"
5. Progress bar appears, showing current phase/agent
6. Turn results display:
   - Narrator description
   - Scene planner output
   - NPC dialogue (if applicable)
   - Rules validation
7. Read output, enter next command
8. Repeat
9. Optionally provide feedback on any turn

### Workflow 3: Monitoring System Health

1. Navigate to **Status Tab**
2. View system overview:
   - System state (ready, processing, error)
   - Uptime, active sessions, total turns
3. Check corpus status:
   - Current corpus name
   - Index status (BM25, Vector)
4. Review agent status:
   - Connection status for each agent
   - Call statistics, avg response time
5. Check retrieval system:
   - Hybrid retrieval status
   - Cache hit rate
6. If issues detected, navigate to **Config Tab** to adjust

### Workflow 4: Adjusting Configuration

1. Navigate to **Config Tab**
2. Select section (Agents, Corpus, Retrieval, System)

**Adjusting Agent Settings:**
3. Select agent from dropdown
4. Modify LLM settings (model, temperature, etc.)
5. Edit prompt templates if needed
6. Test connection
7. Save changes
8. Restart application if required

**Adjusting Retrieval Settings:**
3. Navigate to **Retrieval** section
4. Adjust BM25/Vector weights using sliders
5. Change fusion strategy
6. Enable/disable query rewriting
7. Test retrieval with sample query
8. Save changes (no restart required)

**Re-indexing Corpus:**
3. Navigate to **Corpus & Ingestion** section
4. Adjust chunk size/overlap if desired
5. Click "Re-index Current Corpus"
6. Monitor progress bar
7. Navigate to **Status Tab** to verify new index

### Workflow 5: Providing and Reviewing Feedback

**Submitting Feedback:**
1. While playing in **Game Tab**, click "Provide Feedback" under a turn
2. Feedback form appears with pre-filled context (session, turn, agent)
3. Select feedback type (Bug Report, Feature Request, etc.)
4. Add rating (optional)
5. Write feedback text
6. Click "Submit Feedback"
7. Toast notification confirms submission
8. Continue playing

**Reviewing Feedback:**
1. Navigate to **Feedback Tab**
2. View list of all feedback items
3. Filter by type, agent, rating, date range
4. Click "View Details" on a feedback item
5. Read full feedback with all context
6. Mark as resolved or add admin reply
7. Export feedback for external analysis

---

## Security Considerations

### Authentication & Authorization
- **Phase 5**: No authentication (local deployment assumed)
- **Future**: Add API key authentication or OAuth
- **Production**: HTTPS required, CORS configured

### Input Validation
- **All User Inputs**: Validated with Pydantic schemas
- **File Uploads**: Size limits, file type checking, virus scanning (future)
- **Config Updates**: Validate before applying, rollback on failure

### Sensitive Data
- **API Keys**: Stored in environment variables, masked in UI
- **Logs**: Redact API keys and sensitive data
- **Feedback**: No PII collected without consent

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Performance Considerations

### Frontend Performance
- **Lazy Loading**: Load heavy libraries (CodeMirror, Chart.js) only when needed
- **Debouncing**: Debounce search inputs, config changes
- **Pagination**: Limit list views to 10-20 items per page
- **Caching**: Cache API responses in browser (with TTL)

### Backend Performance
- **Async Endpoints**: Use `async def` for I/O-bound operations
- **Background Tasks**: Offload heavy operations (ingestion) to background
- **Response Streaming**: Stream large responses (logs, exports)
- **Rate Limiting**: Prevent abuse (future)

### API Response Times
- **Game Endpoints**: 1-5s (LLM-dependent)
- **Status Endpoints**: <50ms (local checks)
- **Config Endpoints**: <100ms (read), <500ms (write)
- **Feedback Endpoints**: <100ms (read), <200ms (write)

---

## Error Handling

### Frontend Error Handling
- **Network Errors**: Display user-friendly toast notifications
- **Validation Errors**: Inline error messages on form fields
- **Server Errors**: Show error details with retry option
- **Loading States**: Spinners, progress bars, skeleton screens

### Backend Error Handling
- **HTTP Status Codes**:
  - 200: Success
  - 400: Bad Request (validation errors)
  - 404: Not Found (session, config)
  - 500: Internal Server Error
  - 503: Service Unavailable (LLM down)

- **Error Response Format**:
  ```json
  {
    "error": true,
    "message": "User-friendly error message",
    "detail": "Technical details for debugging",
    "code": "ERROR_CODE"
  }
  ```

### Graceful Degradation
- **LLM Unavailable**: Show error, suggest checking config
- **Index Not Loaded**: Prompt to ingest corpus
- **Agent Disabled**: Skip agent, continue with others
- **Cache Miss**: Fallback to normal retrieval

---

## Accessibility

### WCAG 2.1 AA Compliance
- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and roles
- **Color Contrast**: Minimum 4.5:1 ratio for text
- **Focus Indicators**: Clear focus states for all interactive elements
- **Alt Text**: Descriptive alt text for all images/icons

### Responsive Text
- **Font Sizes**: Minimum 14px body text
- **Scalable**: Support browser zoom up to 200%
- **Line Height**: Minimum 1.5 for body text

### Form Accessibility
- **Labels**: Every form field has a visible label
- **Error Messages**: Associated with fields via ARIA
- **Required Fields**: Clearly marked with asterisk and ARIA

---

## Testing Strategy

### Frontend Testing
- **Manual Testing**: Test all workflows on major browsers
- **Browser Compatibility**: Chrome, Firefox, Safari, Edge
- **Responsive Testing**: Desktop, tablet, mobile viewports
- **Accessibility Testing**: Lighthouse, axe DevTools

### Backend Testing
- **Unit Tests**: Test all new API endpoints
- **Integration Tests**: Test config updates, feedback storage
- **Load Testing**: Test concurrent sessions, heavy ingestion
- **Error Scenarios**: Test all error conditions

### End-to-End Testing
- **User Workflows**: Automate key user workflows (Selenium/Playwright)
- **API Testing**: Postman/Bruno collections for all endpoints
- **Performance Testing**: Monitor response times, memory usage

---

## Deployment

### Local Development
```bash
# Start backend
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# Access UI
http://localhost:8000/
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY config/ config/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Deployment
- **Reverse Proxy**: Nginx/Caddy for HTTPS, static file serving
- **Environment Variables**: Externalize all secrets
- **Logging**: Centralized logging (ELK, CloudWatch)
- **Monitoring**: Prometheus, Grafana for metrics
- **Backup**: Automated backups of config, feedback, indices

---

## Future Enhancements (Post-Phase 5)

### Phase 6 Integration: Metrics & Evaluation
- **Metrics Dashboard** in Status Tab
  - RAG evaluation metrics (Recall@K, MRR)
  - Agent performance metrics
  - Visualization with Chart.js

- **Evaluation Configuration** in Config Tab
  - Upload test datasets
  - Configure evaluation parameters
  - Run evaluations, view results

- **Feedback Analysis** in Feedback Tab
  - Sentiment analysis
  - Topic clustering
  - Trend analysis over time

### Advanced Features
- **WebSocket Support**: Real-time updates without polling
- **Multi-User Support**: User accounts, sessions per user
- **Session Persistence**: Save/load sessions to database
- **Prompt Library**: Save and reuse custom prompts
- **Agent Marketplace**: Share/import agent configurations
- **Voice Input**: Speech-to-text for player commands
- **Text-to-Speech**: Narration audio output
- **Theming**: Dark mode, custom color schemes
- **Internationalization**: Multi-language support
- **Mobile App**: Native iOS/Android app

---

## Success Criteria

Phase 5 UI will be considered successful when:

✅ **Functional Requirements**
1. Users can play the game with real-time progress feedback
2. Users can monitor all system components and their health
3. Users can update agent configurations (LLM settings, prompts)
4. Users can manage corpus (upload, ingest, re-index)
5. Users can adjust retrieval settings dynamically
6. Users can submit and review feedback
7. All existing API endpoints are accessible via UI
8. All new API endpoints are implemented and tested

✅ **Non-Functional Requirements**
9. UI is responsive on desktop and tablet
10. API response times meet targets (<5s for game, <100ms for status)
11. All user inputs are validated
12. Error messages are clear and actionable
13. UI works in all major browsers (Chrome, Firefox, Safari, Edge)
14. Zero regressions in existing functionality
15. All code follows project standards (type hints, docstrings, tests)

✅ **User Experience**
16. New users can set up and start playing within 5 minutes
17. Configuration changes are intuitive and well-documented
18. Progress indicators provide clear feedback during long operations
19. Feedback submission is quick and easy (< 30 seconds)
20. Status information is clear and actionable

---

## Open Questions for Review

1. **Technology Choice**: Agree with plain HTML/CSS/JS vs. React/Vue?
2. **WebSocket vs. Polling**: Implement WebSockets in Phase 5 or defer to future?
3. **Prompt Editing**: Use CodeMirror for rich editing or plain textarea?
4. **Feedback Storage**: BM25 index sufficient or use SQLite/PostgreSQL?
5. **Configuration Persistence**: YAML files vs. database for config storage?
6. **Admin Tab**: Include in Phase 5 or defer to Phase 6?
7. **Authentication**: Required for Phase 5 or defer to production deployment?
8. **Export Formats**: Support JSON only or also CSV, YAML for exports?
9. **Ingestion**: Background tasks with polling or synchronous with loading screen?
10. **Session Management**: Support multiple concurrent sessions per user or single session?

---

## Recommended Implementation Order

### Sprint 1: Foundation (Week 1)
1. Create basic HTML structure with Bootstrap tabs
2. Implement API client wrapper (api-client.js)
3. Create Game Tab (basic layout, no functionality)
4. Implement static file serving in FastAPI
5. Test basic navigation and API connectivity

### Sprint 2: Game Tab (Week 1-2)
6. Implement session management (new game, load session)
7. Implement turn submission with progress tracking
8. Implement output display with formatting
9. Test complete game workflow
10. Add localStorage persistence

### Sprint 3: Status Tab (Week 2)
11. Implement system status display
12. Implement corpus status display
13. Implement agent status table
14. Implement retrieval status display
15. Add auto-refresh with polling

### Sprint 4: Configuration Endpoints (Week 2-3)
16. Create ConfigManager class
17. Implement agent config endpoints
18. Implement retrieval config endpoints
19. Implement system config endpoints
20. Implement corpus management endpoints

### Sprint 5: Config Tab (Week 3)
21. Implement agent configuration UI
22. Implement corpus management UI
23. Implement retrieval settings UI
24. Implement system settings UI
25. Add validation and error handling

### Sprint 6: Feedback System (Week 4)
26. Create FeedbackStore class
27. Implement feedback endpoints
28. Implement feedback submission UI
29. Implement feedback list/display UI
30. Implement feedback search and filtering

### Sprint 7: Polish & Testing (Week 4)
31. Responsive design testing and fixes
32. Browser compatibility testing
33. Accessibility audit and fixes
34. Performance optimization
35. Comprehensive documentation
36. Demo video/walkthrough

---

## Conclusion

This UI design provides a comprehensive, user-friendly interface for the Multi-Agent RAG RPG system. It leverages existing API endpoints, introduces new endpoints for configuration and feedback management, and follows modern web development best practices.

The design is:
- **User-Friendly**: Intuitive navigation, clear feedback, helpful error messages
- **Comprehensive**: Covers all system functionality (game, status, config, feedback)
- **Extensible**: Easy to add new features (metrics, evaluation, admin tools)
- **Maintainable**: Clean code structure, well-documented, testable
- **Production-Ready**: Security considerations, error handling, performance optimization

**Next Steps:**
1. Review and approve this design document
2. Clarify any open questions
3. Proceed with implementation following the recommended sprint plan
4. Iterate based on user feedback and testing

---

**Document Version:** 1.0
**Author:** Claude Code
**Review Status:** Awaiting Approval
**Estimated Implementation Time:** 4 weeks (part-time) or 2 weeks (full-time)
