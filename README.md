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
- **Pluggable Retrieval**: Abstract interface for retrieval implementations
- **Hybrid Retrieval**: BM25 + vector search with configurable fusion
- **Query Rewriting**: Custom query expansion and preprocessing
- **Retrieval Manager**: Coordinates retrieval operations for agents

### 3. Data Layer
- **Ingestion Pipeline**: Separate process for corpus processing
- **Chunking Strategies**: Sentence, paragraph, and sliding window
- **Index Building**: BM25 and vector embeddings
- **Storage**: Persistent indices for fast retrieval

### 4. API Layer
- **FastAPI**: RESTful API for game interactions
- **Session Management**: Thread-safe concurrent session handling
- **State Management**: Sliding window memory with token limits
- **Observability**: Structured JSON logging

## Key Features

- **Corpus-Grounded**: All facts must come from the corpus
- **Multi-Agent Coordination**: Agents work together in a structured flow
- **Configurable**: LLM providers, personas, and retrieval weights via YAML
- **Just-in-Time NPC Extraction**: NPC personas extracted dynamically from corpus
- **Session-Based**: Isolated game state per session
- **Concurrent**: Supports multiple simultaneous game sessions

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

- `POST /new_game` - Create a new game session
- `POST /turn` - Process a player command
- `GET /state/{session_id}` - Get current game state
- `POST /ingest` - Trigger corpus ingestion (if not done offline)

### Using Docker

```bash
# Build image
make docker-build

# Run container
make docker-run
```

## Configuration

Configuration is managed through YAML files in the `config/` directory. Example:

```yaml
agents:
  narrator:
    llm:
      provider: openai
      model: gpt-3.5-turbo
      temperature: 0.7
    persona_template: "You are a narrator describing scenes from the story."
  
  scene_planner:
    llm:
      provider: ollama
      model: llama2
      base_url: http://localhost:11434/v1

retrieval:
  bm25_weight: 0.5
  vector_weight: 0.5
  top_k: 10
  fusion_strategy: rrf

session:
  memory_window_size: 10
  max_tokens: 8000
  sliding_window: true
```

## Project Structure

```
ma_rag_rpg/
├── src/
│   ├── agents/          # Agent implementations
│   ├── rag/             # Retrieval components
│   ├── ingestion/       # Data ingestion pipeline
│   ├── api/             # FastAPI endpoints
│   ├── core/            # Core framework
│   └── utils/           # Utilities
├── tests/               # Test suite
├── config/              # Configuration files
├── data/                # Corpus and indices
├── scripts/             # Utility scripts
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
3. Add agent configuration to `config/agents.yaml`
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

**Phase 3 Planned**: Agent implementations (Narrator, ScenePlanner, NPCManager, RulesReferee).

**Phase 4 Planned**: API endpoints and game loop.

**Phase 5 Planned**: RAG metrics and evaluation framework.
