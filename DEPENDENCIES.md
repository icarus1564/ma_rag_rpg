# Project Dependencies

This document lists all dependencies and their purposes for the Multi-Agent RAG RPG project.

## Core Dependencies

### Web Framework
- **fastapi** (>=0.104.0) - Modern web framework for building APIs
- **uvicorn[standard]** (>=0.24.0) - ASGI server for running FastAPI apps
- **pydantic** (>=2.5.0) - Data validation using Python type annotations
- **pydantic-settings** (>=2.1.0) - Settings management with environment variables

### LLM Client Libraries
- **openai** (>=1.3.0) - OpenAI API client for GPT models
- **google-generativeai** (>=0.3.0) - Google Gemini API client

### RAG and Retrieval
- **rank-bm25** (>=0.2.2) - BM25 ranking algorithm for keyword search
- **sentence-transformers** (>=2.2.0) - Sentence embeddings for semantic search
- **chromadb** (>=0.4.0) - Vector database (default provider)
- **numpy** (>=1.24.0) - Numerical computing (required by sentence-transformers)

### Data Processing
- **nltk** (>=3.8.0) - Natural Language Toolkit for query rewriting
- **tiktoken** (>=0.5.0) - Token counting for OpenAI models

### Configuration and Utilities
- **pyyaml** (>=6.0) - YAML parser for configuration files
- **python-dotenv** (>=1.0.0) - Environment variable management from .env files

### Testing
- **pytest** (>=7.4.0) - Testing framework
- **pytest-asyncio** (>=0.21.0) - Async support for pytest
- **pytest-mock** (>=3.12.0) - Mocking support for pytest
- **pytest-cov** (>=4.1.0) - Coverage reporting for pytest

### Logging
- **structlog** (>=23.2.0) - Structured logging for better observability

## Optional Dependencies

### Vector Databases (Alternative Providers)
- **pinecone-client** (>=2.2.0) - Pinecone vector database client (commented out in requirements.txt)
  - To use: Uncomment in requirements.txt and run `pip install pinecone-client`
  - Configuration: Set `PINECONE_API_KEY` and update `config/config.yaml`

### Development Tools (Not in requirements.txt)
These are optional tools for code quality:

- **pylint** - Python linter
- **black** - Code formatter
- **ruff** - Fast Python linter (replaces flake8, isort)
- **mypy** - Static type checker

Install separately if needed:
```bash
pip install pylint black ruff mypy
```

## Python Version Requirement

- **Minimum:** Python 3.11
- **Recommended:** Python 3.11 or 3.12
- **Tested on:** Python 3.12

## System Dependencies

### NLTK Data
NLTK requires additional data downloads for query rewriting:

```bash
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

### Ollama (Optional)
For local LLM inference:
- Install Ollama from https://ollama.ai
- Pull a model: `ollama pull llama2`
- Ensure service is running: `ollama serve`

## Installation

### Standard Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install all dependencies
pip install -r requirements.txt
```

### Using Make (Recommended)

```bash
make setup
source .venv/bin/activate  # Linux/Mac
```

### Verification

Verify installation:

```bash
# Test Python imports
python -c "import fastapi, chromadb, sentence_transformers; print('✅ Dependencies OK')"

# Run tests
make test
```

## Dependency Updates

### Checking for Updates

```bash
pip list --outdated
```

### Updating Dependencies

```bash
# Update specific package
pip install --upgrade <package-name>

# Update requirements.txt
pip freeze | grep <package-name> > temp.txt
# Manually update requirements.txt with new version
```

### Security Updates

Regularly check for security vulnerabilities:

```bash
pip install safety
safety check
```

## Docker Dependencies

The Dockerfile handles all dependencies automatically:

```bash
make docker-build  # Installs everything in container
make docker-run    # Runs with dependencies
```

## Troubleshooting

### Common Issues

**1. ChromaDB Installation Fails**
- Ensure you have build tools installed:
  - Linux: `sudo apt-get install build-essential`
  - Mac: `xcode-select --install`

**2. Sentence Transformers Download Issues**
- First run downloads models (~100MB)
- Ensure internet connection
- Models cached in `~/.cache/huggingface/`

**3. NLTK Data Missing**
```bash
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

**4. Import Errors**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

**5. Pytest-cov Not Found**
- Already in requirements.txt (>=4.1.0)
- If missing: `pip install pytest-cov`

## Dependency Graph

```
fastapi (Web Framework)
├── uvicorn (Server)
└── pydantic (Validation)

RAG Pipeline
├── sentence-transformers (Embeddings)
│   └── numpy (Math)
├── chromadb (Vector DB)
└── rank-bm25 (Keyword Search)

LLM Clients
├── openai (GPT models)
└── google-generativeai (Gemini models)

Data Processing
├── nltk (NLP)
└── tiktoken (Tokenization)

Development
├── pytest (Testing)
│   ├── pytest-asyncio
│   ├── pytest-mock
│   └── pytest-cov
└── structlog (Logging)
```

## License Compatibility

All dependencies are compatible with common open-source licenses:
- Apache 2.0
- MIT
- BSD

Check individual package licenses:
```bash
pip-licenses
```

## Platform Support

### Tested Platforms
- ✅ Linux (Ubuntu 20.04+, Debian 11+)
- ✅ macOS (11+)
- ✅ Windows 10/11 (with WSL recommended)

### Architecture
- ✅ x86_64 (Intel/AMD)
- ✅ ARM64 (Apple Silicon, ARM servers)

### Docker
- ✅ All platforms via Docker

## Version Pinning Strategy

Dependencies use **minimum version specifiers** (`>=`):
- Allows bug fixes and minor updates
- Prevents breaking changes (semantic versioning)
- Pin specific versions in production if needed

For production, consider creating `requirements-lock.txt`:
```bash
pip freeze > requirements-lock.txt
```

## Contact

For dependency issues:
1. Check this document
2. Review [QUICKSTART.md](QUICKSTART.md)
3. Check package documentation
4. Submit an issue with error details
