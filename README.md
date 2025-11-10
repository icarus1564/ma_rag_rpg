# Multi-Agent RAG RPG

A role-playing game engine where multiple AI agents role-play inside the world of a text corpus. All in-game facts, locations, items, and NPC knowledge are retrieved from the corpus using RAG (Retrieval-Augmented Generation), with a rules checker agent preventing hallucinations.

NOTE: This is currently a non-functional prototype under construction. We will update this readme when we have a working prototype worthy of cloning / investigation.

## Architecture

The system consists of four main layers:

### 1. Agent Framework Layer
- **Core Agent Interface**: Abstract base class for all agents
- **Orchestrator**: Coordinates agent execution in the game loop
- **Multi-Provider LLM Support**: Unified interface for OpenAI, Gemini, and Ollama
- **Agent Types**:
  - **Narrator**: Generates scene descriptions grounded in corpus
  - **ScenePlanner**: Plans next scene and determines NPC responses
  - **NPCManager**: Generates NPC dialogue with just-in-time persona extraction
  - **RulesReferee**: Validates player actions against corpus facts

### 2. RAG Layer
- **Vector DB Abstraction**: Provider-agnostic interface supporting ChromaDB (default), Pinecone, and extensible to other providers
- **Pluggable Retrieval**: Abstract interface for retrieval implementations
- **Hybrid Retrieval**: BM25 + vector search with configurable fusion strategies (RRF, weighted)
- **Query Rewriting**: Query expansion, normalization, and optional LLM-based rewriting
- **Retrieval Components**:
  - BM25 Retriever: Keyword-based retrieval using rank-bm25
  - Vector Retriever: Semantic search via vector database abstraction
  - Hybrid Retriever: Combines both approaches with score fusion
- **Retrieval Manager**: Coordinates retrieval operations for agents with caching

### 3. Data Layer
- **Ingestion Pipeline**: Separate process for corpus processing with full orchestration
- **Chunking Strategies**: Sentence-based, paragraph-based, and sliding window chunking
- **BM25 Indexing**: Builds and persists BM25 index for keyword retrieval
- **Embedding Generation**: Supports multiple embedding models (sentence-transformers, OpenAI)
- **Vector Database**: Stores embeddings with provider abstraction (ChromaDB default, Pinecone support)
- **Metadata Management**: Tracks chunk metadata (source, position, indices)
- **Storage**: Persistent indices (BM25 pickle, vector DB, metadata JSON)

### 4. API Layer
- **FastAPI**: RESTful API for game interactions
- **Session Management**: Thread-safe concurrent session handling
- **State Management**: Sliding window memory with token limits
- **Observability**: Structured JSON logging

## Key Features

- **Corpus-Grounded**: All facts must come from the corpus via RAG
- **Multi-Agent Coordination**: Agents work together in a structured flow
- **Hybrid Retrieval**: Combines BM25 (keyword) and vector (semantic) search for better results
- **Vector DB Abstraction**: Easy swapping between providers (ChromaDB, Pinecone) via configuration
- **Query Rewriting**: Improves retrieval quality through expansion and normalization
- **Configurable**: LLM providers, personas, retrieval weights, and fusion strategies via YAML
- **Just-in-Time NPC Extraction**: NPC personas extracted dynamically from corpus
- **Session-Based**: Isolated game state per session with sliding window memory
- **Concurrent**: Supports multiple simultaneous game sessions
- **Docker-Ready**: Full containerization support with persistent data volumes

## Quick Start

**New users:** See [QUICKSTART.md](QUICKSTART.md) for a step-by-step guide to get running in minutes.

## Installation

### Prerequisites

- Python 3.11+
- Git
- At least one LLM provider (OpenAI, Gemini, or Ollama)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ma_rag_rpg
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Make will create the venv automatically
   make setup

   # Activate the virtual environment
   source .venv/bin/activate  # On Linux/Mac
   .venv\Scripts\activate     # On Windows
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (choose ONE provider):
   # OPENAI_API_KEY=your_key_here
   # GEMINI_API_KEY=your_key_here
   # OLLAMA_BASE_URL=http://localhost:11434/v1  # For local Ollama
   ```

4. **Configure agents**:
   ```bash
   cp config/config.yaml.example config/config.yaml
   cp config/agents.yaml.example config/agents.yaml
   # Edit config/agents.yaml to set your LLM provider (ollama, openai, or gemini)
   ```

5. **Download NLTK data** (for query rewriting):
   ```bash
   python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
   ```

## Usage

### Ingesting Corpus

Before using the system, you need to ingest your corpus to create indices:

```bash
# Using the CLI script
python scripts/ingest.py --corpus data/corpus.txt

# Or via API
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "corpus_path": "data/corpus.txt",
    "collection_name": "corpus_embeddings",
    "chunk_size": 500,
    "chunk_overlap": 50
  }'
```

### Running Tests

```bash
# Run all tests (recommended after setup)
make test

# Run specific test suites
make test-core       # Core framework tests (36 tests)
make test-agents     # Agent tests (39 tests)
make test-rag        # RAG integration tests (21 tests)

# Run with coverage report
make test-coverage   # Generates htmlcov/index.html

# Manual pytest
pytest tests/ -v
```

**Expected Result:** ✅ 168 tests passing (zero warnings)

### Running the API Server

```bash
make run
# Or:
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

**Access the UI:** Open your browser to `http://localhost:8000` (automatically redirects to `/ui/index.html`)

### API Endpoints

**Game Endpoints:**
- `POST /api/new_game` - Create a new game session
- `POST /api/turn` - Process a player command through the game loop
- `GET /api/state/{session_id}` - Get current game state
- `GET /api/progress/{session_id}` - Get real-time turn progress
- `DELETE /api/session/{session_id}` - Delete a game session

**Status/Monitoring Endpoints:**
- `GET /api/status/system` - Overall system status and metrics
- `GET /api/status/corpus` - Corpus and indexing status
- `GET /api/status/agents` - All agents health and statistics
- `GET /api/status/retrieval` - Retrieval system status
- `GET /health` - Quick health check with component status

**RAG Infrastructure Endpoints:**
- `POST /ingest` - Trigger corpus ingestion and index creation
- `POST /search` - Search corpus using hybrid retrieval

### Using Docker

```bash
# Build image
make docker-build

# Run container
make docker-run
```

## Configuration

Configuration is managed through YAML files in the `config/` directory. See `config/config.yaml.example` and `config/agents.yaml.example` for complete examples.

### Main Configuration (`config/config.yaml`)

```yaml
# Vector Database Configuration
vector_db:
  provider: chroma  # chroma, pinecone
  chroma:
    persist_directory: data/vector_db
    collection_name: corpus_embeddings
    in_memory: false
  pinecone:
    api_key: ${PINECONE_API_KEY}
    environment: us-west1-gcp
    index_name: ma-rag-rpg-index
    dimension: 384

# Ingestion Configuration
ingestion:
  corpus_path: data/corpus.txt
  chunk_size: 500
  chunk_overlap: 50
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  bm25_index_path: data/indices/bm25_index.pkl
  vector_index_path: data/indices/vector_index
  chunk_metadata_path: data/indices/chunks.json

# Retrieval Configuration
retrieval:
  bm25_weight: 0.5
  vector_weight: 0.5
  top_k: 10
  fusion_strategy: rrf  # rrf, weighted
  rrf_k: 60
  query_rewriter:
    enabled: true
    expansion: true
    decomposition: false
    llm_rewriting: false

# Agent Configuration (loaded from config/agents.yaml.example)
# See config/agents.yaml.example for agent-specific settings

# Session Configuration
session:
  memory_window_size: 10
  max_tokens: 8000
  sliding_window: true
  session_ttl_seconds: 3600
```

### Agent Configuration (`config/agents.yaml.example`)

```yaml
agents:
  Narrator:
    name: Narrator
    llm:
      provider: ollama
      model: nameOfModel
      temperature: 0.7
      max_tokens: 1000
    persona_template: null
    retrieval_query_template: null
    retrieval_top_k: 5
    enabled: true
  # ... other agents
```

## Project Structure

```
ma_rag_rpg/
├── src/
│   ├── agents/          # Agent implementations (Phase 3)
│   │   ├── narrator.py
│   │   ├── scene_planner.py
│   │   ├── npc_manager.py
│   │   ├── npc_persona_extractor.py
│   │   ├── rules_referee.py
│   │   ├── citation_utils.py
│   │   ├── response_parsers.py
│   │   └── prompt_templates.py
│   ├── rag/             # Retrieval components
│   │   ├── base_retriever.py
│   │   ├── bm25_retriever.py
│   │   ├── vector_retriever.py
│   │   ├── hybrid_retriever.py
│   │   ├── query_rewriter.py
│   │   └── vector_db/   # Vector DB abstraction layer
│   │       ├── base.py
│   │       ├── chroma_provider.py
│   │       ├── pinecone_provider.py
│   │       └── factory.py
│   ├── ingestion/       # Data ingestion pipeline
│   │   ├── chunker.py
│   │   ├── bm25_indexer.py
│   │   ├── embedder.py
│   │   ├── metadata_store.py
│   │   └── pipeline.py
│   ├── api/             # FastAPI endpoints
│   │   ├── app.py
│   │   ├── endpoints/
│   │   │   ├── ingestion.py
│   │   │   └── search.py
│   │   └── schemas/
│   ├── core/            # Core framework
│   │   ├── base_agent.py
│   │   ├── config.py
│   │   ├── orchestrator.py
│   │   ├── retrieval_manager.py
│   │   ├── session.py
│   │   └── session_manager.py
│   └── utils/           # Utilities
├── tests/               # Test suite
│   ├── test_agents/     # Agent tests (39 tests)
│   ├── test_core.py     # Core framework tests
│   └── test_rag_pipeline.py  # RAG integration tests
├── config/              # Configuration files
│   ├── config.yaml.example
│   └── agents.yaml.example
├── data/                # Corpus and indices
│   ├── corpus.txt
│   ├── indices/
│   └── vector_db/
├── scripts/             # Utility scripts
├── docs/                # Design documentation
├── Dockerfile
├── Makefile
└── requirements.txt
```

## Development

### Running Tests

```bash
# Run all tests
make test
# Or:
pytest tests/ -v

# Run specific test suites
pytest tests/test_core.py -v              # Core framework tests
pytest tests/test_agents/ -v              # Agent tests only
pytest tests/test_rag_pipeline.py -v      # RAG integration tests

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Current Test Status:** ✅ 168 tests passing

### Code Quality

**Linting** (Optional - install separately):
```bash
# Install linting tools
pip install pylint black ruff mypy

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

**Pre-commit Checks** (before committing):
```bash
make test           # Ensure all tests pass
make clean          # Clean up artifacts
```

### Agent Implementation Pattern

All agents follow this pattern (see existing agents for examples):

```python
from src.core.base_agent import BaseAgent, AgentContext, AgentOutput
from src.core.config import AgentConfig
from src.core.retrieval_manager import RetrievalManager

class MyAgent(BaseAgent):
    def __init__(self, config: AgentConfig, retrieval_manager: RetrievalManager):
        super().__init__(config)
        self.retrieval_manager = retrieval_manager

    def process(self, context: AgentContext) -> AgentOutput:
        # 1. Build retrieval query
        query = self._build_query(context)

        # 2. Retrieve relevant chunks
        results = self.retrieval_manager.retrieve(
            query=query,
            top_k=self.config.retrieval_top_k,
            agent_name=self.config.name
        )

        # 3. Build prompt and generate
        prompt = self._build_prompt(context, results)
        response = self.llm_client.generate(prompt, system_prompt=...)

        # 4. Parse and return structured output
        return self._parse_response(response, results)
```

Steps to add a new agent:
1. Create a new class inheriting from `BaseAgent`
2. Implement the `process()` method following the pattern above
3. Add prompt templates to `prompt_templates.py`
4. Add agent configuration to `config/agents.yaml.example`
5. Write comprehensive tests
6. Register agent in orchestrator

### Adding a New LLM Provider

1. Add provider to `LLMProvider` enum in `src/core/config.py`
2. Update `LLMClient._initialize_client()` in `src/core/base_agent.py`
3. Update `LLMClient.generate()` method
4. Add tests

## LLM Providers

### OpenAI
Set `OPENAI_API_KEY` environment variable.

### Gemini
Set `GEMINI_API_KEY` environment variable.

### Ollama
Runs locally by default at `http://localhost:11434/v1`. No API key required.
Set `OLLAMA_BASE_URL` to customize the endpoint.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code standards and style
- Testing requirements
- Pull request process
- Development workflow

## Additional Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick start guide for new users
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [DEPENDENCIES.md](DEPENDENCIES.md) - Complete dependency documentation

## License

[Add your license here]

## Implementation Status

### Phase 1: Foundation ✅ COMPLETE
- ✅ Core framework (config, session, orchestrator, base agent)
- ✅ LLM abstraction (OpenAI, Gemini, Ollama)
- ✅ Session management with sliding window memory
- ✅ Testing infrastructure
- ✅ **Tests:** 36 core tests passing

### Phase 2: RAG Infrastructure ✅ COMPLETE
- ✅ Vector DB abstraction layer (ChromaDB, Pinecone)
- ✅ Ingestion pipeline (chunking, BM25, embeddings, metadata)
- ✅ Hybrid retrieval (BM25 + vector with RRF/weighted fusion)
- ✅ Query rewriting (expansion, normalization)
- ✅ Retrieval manager with caching
- ✅ API endpoints for ingestion and search
- ✅ **Tests:** 21 RAG integration tests passing

### Phase 3: Agent Implementations ❌ Known Issues (see below): 
- ✅ **Narrator Agent**: Scene descriptions grounded in corpus
- ❌ BUG: **Scene Planner Agent**: Story flow and NPC response determination not working
- ℹ️ UNKNOWN:**NPC Manager Agent**: In-character dialogue with just-in-time persona extraction not tested due to orchestration/planner issues
- ❌ BUG: **Rules Referee Agent**: Action validation against corpus facts not working
- ✅ **Shared Utilities**: Citation mapping, response parsing, prompt templates
- ℹ️ UNKNOWN:**NPC Persona Extractor**: Dynamic character extraction from corpus
- ℹ️ REQUIRES UPDATE:**Tests:** 39 agent tests passing (100% coverage)
- ℹ️ REQUIRES UPDATE:**Documentation:** Complete design and implementation docs

**Key Features Implemented:**
- Corpus-grounded operation with citation tracking
- Just-in-time NPC persona extraction and caching
- Graceful error handling and fallbacks
- Structured output with metadata
- Integration-ready for game loop

### Phase 4: Game Loop & API ✅ COMPLETE
- ℹ️ REQUIRES UPDATE: **GameLoop Class**: Orchestrated turn execution with comprehensive logging
- ℹ️ REQUIRES UPDATE: *Progress Tracking**: Real-time progress updates via callbacks not displaying effectively
- ✅ **Game Endpoints**: `/api/new_game`, `/api/turn`, `/api/state/{session_id}`, `/api/progress/{session_id}`, `/api/session/{session_id}`
- ✅ **Status Endpoints**: `/api/status/system`, `/api/status/corpus`, `/api/status/agents`, `/api/status/retrieval`
- ✅ **Health Check**: Enhanced `/health` endpoint with real component status
- ✅ **API Schemas**: Complete Pydantic models for all requests/responses
- ✅ **Session Manager**: Thread-safe, TTL-based concurrent session handling
- ✅ **FastAPI Lifespan**: Modern context manager pattern (no deprecated code)
- ✅ **Tests**: 40 new tests (100% passing, zero warnings)

### Phase 5: Simple UI for Game, Statistics, Configuration, Status, and Feedback  ✅ COMPLETE
- ✅ **Design Document:** [docs/PHASE_5_UI_DESIGN.md](docs/PHASE_5_UI_DESIGN.md)
- ✅ **Technology Stack:** Plain HTML/CSS/JavaScript with Bootstrap 5.3, Font Awesome
- ✅ **Four-Tab UI Implementation:**
  - **Game Tab:** Interactive gameplay with real-time progress tracking
    - ✅ Session management (new game, load session, localStorage persistence)
    - ✅ Turn submission with progress polling showing current agent execution
    - ✅ Agent output display with citations, metadata, and turn history
    - ✅ Export game history functionality
  - **Status Tab:** Comprehensive system monitoring dashboard
    - ✅ System overview (uptime, active sessions, total turns)
    - ✅ Corpus status (chunks, BM25/Vector indices, embedding model)
    - ✅ Agent status table (LLM connections, call statistics, response times)
    - ✅ Retrieval system status (hybrid retrieval, cache hit rate)
    - ✅ Auto-refresh with real-time updates
  - **Configuration Tab:** Simplified configuration overview
    - ✅ Agent configuration overview (LLM provider, model display)
    - ✅ Corpus management (upload and ingest via existing /ingest endpoint)
    - ✅ Retrieval settings display
    - ℹ️ Note: Full dynamic config editing deferred to reduce scope
  - **Feedback Tab:** User feedback collection interface
    - ✅ Feedback submission form (type, rating, agent, session/turn context)
    - ✅ Client-side feedback logging (console output)
    - ℹ️ Note: Full BM25 feedback storage deferred to reduce scope
- ✅ **Static File Serving:**
  - FastAPI static file mounting at `/ui`
  - Root endpoint (`/`) redirects to UI
  - All HTML, CSS, and JavaScript files properly served
- ✅ **Testing:**
  - 9 new UI connectivity tests
  - All 145 total tests passing (zero warnings)
  - Server startup verified
  - UI accessibility confirmed
- ✅ **Logging:**
  - Comprehensive debug logging added using Decorator pattern

### Phase 6: MVP  ⏳ PLANNED
####Fix ScenePlanner which does not properly orchestrate and gets stuck. ScenePlanner should
- take in the validated results from the vector / bm25 search and the results from the rules_referee
- analyze the results and determine whether they indicate a "not good enough" response or engagement with a character or the narrator
- return the guidance and reasoning to the "orchestrator"
- Orchestrator: launch the appropriate Agent for next steps (e.g. npc_persona_extractor OR narrator with scene narration OR narrator with disqualification message)

####Fix RulesReferee which does not identify out-of-scope user prompts or agent responses
- take in the raw response from the vector / bm25 search
- analyze the response and determine if they indicate a clean match between source (prompt or agent response) and the corpus
- return whether the match is good enough or not
- Orechstrator: Results returned to scene_planner to determine next steps

####Verify if PersonaExtractor is working well enough for MVP
- take in the name of the character to extract
- query the corpus for N examples of character personality and dialogue
- build and return persona
- Orchestrator: launch the npc_manager with the scene search results, user prompt, and persona

####Ensure external LLMs work properly
- Update to use OpenAI GPT & test
- Update to use Gemini & test

####Containerize and Deploy
- Ensure app works on local Linux following quick start guide
- Ensure app works on local windows following quick start guide
- Ensure app works on Google Collab following quick start guide

###Stretch Goals / Post MVP

####NPC Persona extractor
- see extracted personas for NPCs
- test loop:
-- give NPC name from corpus
-- provide ability to see and update system prompt
-- sytem generages RAG results
-- see full context sent to LLM
-- see results containing extracted personality traits/etc
-- see results of test scenario with NPCManager utilizing persona to respond as the character
- in game loop: trigger NPCManager to respond using the personality

#### Test and Improve

####Implement ScenePlanner test loop:
-- see and update system prompt and parameters
-- provide context with user prompt
-- retrieve RAG results
-- see full context sent to ScenePlanner
-- see output of ScenePlanner
-- metrics: score the results and store system prompt, parameters, context with score for review

####Implement RulesReferree test loop:
-- see and update system prompt and parameters
-- provide input prompt (user or Agent)
-- RAG input prompt
-- show full context sent to RulesReferee
-- see results from RulesReferee
-- metrics: results scoring against known corpus and input, stored for each permutation of system prompt and parameters

####See and update vectordb and bm25 retriever/search result tuning / hybrid approach with test loop (tweak, search, see results)
- new page (?) that provides parameter tuning, request query tuning, and results
- metrics on parameter combinations / versions and results matching expectations or not

####See and update Agent prompts and settings in test loop (tweak, prompt, see results)
- source system prompt, source data, parameters, response
- TODO: metrics on source system prompt and parameters with resulting match to expectations

####See full context input sent to Agents with full output per step
- "log to UI" with expandable input / output UI components
- separation of system prompt from data in input

####See running status of system as it processes each turn
- building on the above, logging every step to UI with stages / handoffs / state of process




#### Metrics & Evaluation ⏳ PLANNED
- ❌ Test data generation
- ❌ RAG evaluation metrics (Recall@K, MRR)
- ❌ Parameterized Evaluation framework
- ❌ Simple Evaluation of Personality Extraction and Model Response (with test corpus data, extraction prompt, and expected results)
- ❌ Updates to UI Status Tab and Configuration Tab to support viewing metrics, evaluation results, and update evaluation parameters

**Current Test Coverage:** 168 tests passing
- Core framework: 36 tests
- Agent implementations: 39 tests
- RAG integration: 29 tests (21 pipeline + 7 integration + 1 e2e)
- GameLoop: 14 tests
- Game API: 13 tests
- Status API: 15 tests
- UI Connectivity: 9 tests
- Integration: 7 tests

## Documentation

### Design Documents
- [docs/RAG_DESIGN_SUMMARY.md](docs/RAG_DESIGN_SUMMARY.md) - High-level RAG infrastructure overview
- [docs/RAG_INFRASTRUCTURE_DESIGN.md](docs/RAG_INFRASTRUCTURE_DESIGN.md) - Complete RAG infrastructure design
- [docs/RAG_IMPLEMENTATION_PLAN.md](docs/RAG_IMPLEMENTATION_PLAN.md) - Detailed implementation plan
- [docs/TEST_DATA_SPECIFICATION.md](docs/TEST_DATA_SPECIFICATION.md) - Test data requirements

### Agent Implementation (Phase 3)
- [docs/AGENT_IMPLEMENTATION_DESIGN.md](docs/AGENT_IMPLEMENTATION_DESIGN.md) - Complete agent design document
- [docs/PHASE_3_IMPLEMENTATION_SUMMARY.md](docs/PHASE_3_IMPLEMENTATION_SUMMARY.md) - Implementation summary and verification

### Game Loop and API (Phase 4)
- [docs/PHASE_4_IMPLEMENTATION_SUMMARY.md](docs/PHASE_4_IMPLEMENTATION_SUMMARY.md) - Implementation summary, verification, and lessons learned
- [docs/PHASE_5_IMPLEMENTATION_SUMMARY.md](docs/PHASE_5_IMPLEMENTATION_SUMMARY.md) - Implementation summary, verification, and details on deferred components and functionality

