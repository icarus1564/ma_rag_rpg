# Quick Start Guide

This guide will help you get the Multi-Agent RAG RPG project up and running in minutes.

## Prerequisites

- **Python 3.11+** installed
- **Git** installed
- At least one LLM provider configured (OpenAI, Gemini, or Ollama)

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ma_rag_rpg

# Create virtual environment and install dependencies
make setup

# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# OR
.venv\Scripts\activate     # On Windows
```

## Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys (use your preferred editor)
nano .env  # or vim, code, etc.
```

### Required Configuration:

**For OpenAI:**
```bash
OPENAI_API_KEY=sk-your-key-here
```

**For Gemini:**
```bash
GEMINI_API_KEY=your-gemini-key-here
```

**For Ollama (local, no key needed):**
```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
```

**Note:** You only need to configure ONE LLM provider to get started.

## Step 3: Copy and Configure Agent Settings

```bash
# Copy agent configuration template
cp config/agents.yaml.example config/agents.yaml

# Edit to set your LLM provider (ollama, openai, or gemini)
nano config/agents.yaml
```

Update the `provider` field for each agent. Example for Ollama:

```yaml
agents:
  Narrator:
    name: Narrator
    llm:
      provider: ollama  # Change this to: ollama, openai, or gemini
      model: llama2     # Model name depends on provider
      temperature: 0.7
      max_tokens: 1000
    # ... rest of config
```

## Step 4: Copy Main Configuration

```bash
# Copy main configuration template
cp config/config.yaml.example config/config.yaml

# Edit if you need to change default settings
nano config/config.yaml
```

**Note:** The default config works fine for getting started with ChromaDB (local).

## Step 5: Prepare Sample Corpus

Create a sample corpus file for testing:

```bash
# Create data directory if it doesn't exist
mkdir -p data

# Create a simple test corpus
cat > data/corpus.txt << 'EOF'
The tavern is a dimly lit wooden building with worn tables and chairs.
Behind the bar stands Gandalf, a wise old wizard with a long grey beard.
He speaks in cryptic riddles and knows much about magic and ancient history.

The forest outside the tavern is dark and mysterious. Strange sounds echo
through the trees at night. Few dare to venture deep into the woods.

In the corner of the tavern sits Aragorn, a skilled ranger with knowledge
of the wilderness. He is brave and loyal, always ready to help those in need.
EOF
```

## Step 6: Ingest Corpus

```bash
# Run the ingestion pipeline
make ingest
# OR
python scripts/ingest.py --corpus data/corpus.txt
```

This will:
- Chunk the corpus
- Build BM25 index
- Generate embeddings
- Store in ChromaDB vector database

**Expected output:**
```
Ingestion complete!
Total chunks: ~15-20
BM25 index saved to: data/indices/bm25_index.pkl
Vector DB collection: corpus_embeddings
Duration: ~10-30 seconds
```

## Step 7: Run Tests

Verify everything is working:

```bash
# Run all tests
make test

# Or run specific test suites
make test-core       # Core framework tests
make test-agents     # Agent tests
make test-rag        # RAG integration tests

# Run with coverage report
make test-coverage
```

**Expected result:** ✅ 75 tests passing

## Step 8: Start the API Server (Optional)

```bash
# Start the FastAPI server
make run
# OR
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### Test the API:

```bash
# Health check
curl http://localhost:8000/health

# Search the corpus
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tell me about Gandalf",
    "top_k": 5
  }'
```

## Troubleshooting

### Common Issues:

**1. Import Errors After Setup**

Make sure you activated the virtual environment:
```bash
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

**2. NLTK Data Missing**

If you see NLTK download errors during query rewriting:
```python
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

**3. Ollama Connection Error**

If using Ollama locally, ensure it's running:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve
```

**4. ChromaDB Permission Errors**

Ensure the data directory is writable:
```bash
chmod -R 755 data/
```

**5. Tests Failing**

Clean and reinstall dependencies:
```bash
make clean
rm -rf .venv
make setup
```

## Next Steps

### Explore the Codebase

- **Agents:** `src/agents/` - See how agents are implemented
- **RAG Pipeline:** `src/rag/` and `src/ingestion/` - Retrieval and indexing
- **Core Framework:** `src/core/` - Session management, orchestration
- **Tests:** `tests/` - Comprehensive test suite

### Read Documentation

- [README.md](README.md) - Full project documentation
- [docs/AGENT_IMPLEMENTATION_DESIGN.md](docs/AGENT_IMPLEMENTATION_DESIGN.md) - Agent architecture
- [docs/PHASE_3_IMPLEMENTATION_SUMMARY.md](docs/PHASE_3_IMPLEMENTATION_SUMMARY.md) - Implementation details
- [.cursor/plans/multi-agent-rag-rpg-framework.plan.md](.cursor/plans/multi-agent-rag-rpg-framework.plan.md) - Complete project plan

### Try Different Configurations

**Use a different vector database (Pinecone):**
1. Uncomment `pinecone-client` in `requirements.txt`
2. Install: `pip install pinecone-client`
3. Update `config/config.yaml` to use Pinecone
4. Set `PINECONE_API_KEY` in `.env`

**Use a different LLM provider:**
1. Update `config/agents.yaml`
2. Change `provider` to `openai`, `gemini`, or `ollama`
3. Update `model` to match the provider's model name
4. Ensure API key is set in `.env`

## Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Review test files in `tests/` for usage examples
- Check [docs/](docs/) for design documents
- Run `make help` to see all available commands

## Quick Reference

```bash
# Setup
make setup              # Install dependencies
make help               # Show all commands

# Testing
make test               # Run all tests
make test-coverage      # Run with coverage

# Development
make run                # Start API server
make ingest             # Ingest corpus
make clean              # Clean build artifacts

# Docker
make docker-build       # Build image
make docker-run         # Run container
```

## Success Checklist

- ✅ Virtual environment created and activated
- ✅ Dependencies installed without errors
- ✅ `.env` file configured with at least one LLM provider
- ✅ `config/agents.yaml` and `config/config.yaml` copied and configured
- ✅ Sample corpus created in `data/corpus.txt`
- ✅ Ingestion completed successfully
- ✅ All 75 tests passing
- ✅ (Optional) API server running and responding

**You're ready to start developing!**
