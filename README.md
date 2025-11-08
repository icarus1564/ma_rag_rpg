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

**Expected Result:** ✅ 75 tests passing

### Running the API Server

```bash
make run
# Or:
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Endpoints

**Game Endpoints:**
- `POST /new_game` - Create a new game session
- `POST /turn` - Process a player command
- `GET /state/{session_id}` - Get current game state

**RAG Infrastructure Endpoints:**
- `POST /ingest` - Trigger corpus ingestion and index creation
- `POST /search` - Search corpus using hybrid retrieval
- `GET /health` - Health check for indices and vector DB

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

**Current Test Status:** ✅ 75 tests passing

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

### Phase 3: Agent Implementations ✅ COMPLETE
- ✅ **Narrator Agent**: Scene descriptions grounded in corpus
- ✅ **Scene Planner Agent**: Story flow and NPC response determination
- ✅ **NPC Manager Agent**: In-character dialogue with just-in-time persona extraction
- ✅ **Rules Referee Agent**: Action validation against corpus facts
- ✅ **Shared Utilities**: Citation mapping, response parsing, prompt templates
- ✅ **NPC Persona Extractor**: Dynamic character extraction from corpus
- ✅ **Tests:** 39 agent tests passing (100% coverage)
- ✅ **Documentation:** Complete design and implementation docs

**Key Features Implemented:**
- Corpus-grounded operation with citation tracking
- Just-in-time NPC persona extraction and caching
- Graceful error handling and fallbacks
- Structured output with metadata
- Integration-ready for game loop

### Phase 4: Game Loop & API ⚠️ IN PROGRESS
- ✅ Session manager (thread-safe, TTL-based)
- ✅ RAG infrastructure endpoints
- ⚠️ Health check endpoint (stubbed)
- ❌ Game loop orchestration
- ❌ Game endpoints (`/new_game`, `/turn`, `/state`)

### Phase 5: Simple UI for Game, Statistics, Configuration and Status  ⏳ PLANNED
- ❌ Three-Tab UI - Game, Status, Configuration
- ❌ Game Tab - simple form to allow end-user to submit their prompt, see what turn they are on, view progress information for in-progress requests, and Agent responses
- ❌ Status Tab - provides status of underlying components, including Agent connections to their LLMs, title of current corpus, and current state of the system (Processing Corpus, Processing Request, Waiting for User)
- ❌ Configuration Tab - allows updating of corpus and changes to prompts and LLM configurations for Agents

### Phase 6: Metrics & Evaluation ⏳ PLANNED
- ❌ Test data generation
- ❌ RAG evaluation metrics (Recall@K, MRR)
- ❌ Parameterized Evaluation framework
- ❌ Simple Evaluation of Personality Extraction and Model Response (with test corpus data, extraction prompt, and expected results)
- ❌ Updates to UI Status Tab and Configuration Tab to support viewing metrics, evaluation results, and update evaluation parameters

**Current Test Coverage:** 75 tests passing
- Core framework: 36 tests
- Agent implementations: 39 tests
- RAG integration: 21 tests

## Documentation

### Design Documents
- [docs/RAG_DESIGN_SUMMARY.md](docs/RAG_DESIGN_SUMMARY.md) - High-level RAG infrastructure overview
- [docs/RAG_INFRASTRUCTURE_DESIGN.md](docs/RAG_INFRASTRUCTURE_DESIGN.md) - Complete RAG infrastructure design
- [docs/RAG_IMPLEMENTATION_PLAN.md](docs/RAG_IMPLEMENTATION_PLAN.md) - Detailed implementation plan
- [docs/TEST_DATA_SPECIFICATION.md](docs/TEST_DATA_SPECIFICATION.md) - Test data requirements

### Agent Implementation (Phase 3)
- [docs/AGENT_IMPLEMENTATION_DESIGN.md](docs/AGENT_IMPLEMENTATION_DESIGN.md) - Complete agent design document
- [docs/PHASE_3_IMPLEMENTATION_SUMMARY.md](docs/PHASE_3_IMPLEMENTATION_SUMMARY.md) - Implementation summary and verification

### Implementation Plan
- [.cursor/plans/multi-agent-rag-rpg-framework.plan.md](.cursor/plans/multi-agent-rag-rpg-framework.plan.md) - Complete project plan with status updates
