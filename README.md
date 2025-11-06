# Multi-Agent RAG RPG

A role-playing game engine where multiple AI agents role-play inside the world of a text corpus. All in-game facts, locations, items, and NPC knowledge are retrieved from the corpus using RAG (Retrieval-Augmented Generation), with a rules checker agent preventing hallucinations.

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

## Installation

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ma_rag_rpg
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   make setup
   # Or manually:
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys:
   # OPENAI_API_KEY=your_key_here
   # GEMINI_API_KEY=your_key_here
   # OLLAMA_BASE_URL=http://localhost:11434/v1  # Optional, defaults to this
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
make test
# Or:
pytest tests/ -v
```

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
│   ├── agents/          # Agent implementations
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
make test
```

### Running Linting

```bash
# Check for linting errors
pylint src/ tests/
```

### Adding a New Agent

1. Create a new class inheriting from `BaseAgent`
2. Implement the `process()` method
3. Add agent configuration to `config/agents.yaml.example`
4. Register agent in orchestrator

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

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Status

**Phase 1 Complete**: Core framework, session management, and agent infrastructure implemented and tested.

**Phase 2 In Progress**: RAG infrastructure, ingestion pipeline, and retrieval components.
- Vector DB abstraction layer (ChromaDB, Pinecone support)
- Ingestion pipeline (chunking, BM25 indexing, embedding generation)
- Hybrid retrieval system (BM25 + vector with fusion strategies)
- Query rewriting (expansion, normalization)

**Phase 3 Planned**: Agent implementations (Narrator, ScenePlanner, NPCManager, RulesReferee).

**Phase 4 Planned**: API endpoints and game loop integration.

**Phase 5 Planned**: RAG metrics and evaluation framework.

## Documentation

For detailed design documentation, see:
- `docs/RAG_DESIGN_SUMMARY.md` - High-level RAG infrastructure overview
- `docs/RAG_INFRASTRUCTURE_DESIGN.md` - Complete RAG infrastructure design
- `docs/RAG_IMPLEMENTATION_PLAN.md` - Detailed implementation plan
- `docs/TEST_DATA_SPECIFICATION.md` - Test data requirements
