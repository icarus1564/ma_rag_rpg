.PHONY: setup install test test-agents test-core test-rag test-coverage ingest eval run docker-build docker-run clean help

# Activate virtual environment
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

# Create virtual environment if it doesn't exist
$(VENV):
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)

setup: $(VENV)
	@echo "Setting up virtual environment..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Setup complete! Activate with: source $(VENV)/bin/activate"

install: setup

test:
	@echo "Running all tests..."
	$(PYTEST) tests/ -v

test-agents:
	@echo "Running agent tests..."
	$(PYTEST) tests/test_agents/ -v

test-core:
	@echo "Running core framework tests..."
	$(PYTEST) tests/test_core.py -v

test-rag:
	@echo "Running RAG integration tests..."
	$(PYTEST) tests/test_rag_pipeline.py -v

test-coverage:
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

ingest:
	@echo "Running ingestion pipeline..."
	$(PYTHON) scripts/ingest.py

eval:
	@echo "Running RAG evaluation..."
	@if [ -f scripts/eval.py ]; then \
		$(PYTHON) scripts/eval.py; \
	else \
		echo "Error: scripts/eval.py not found (Metrics not implemented yet)"; \
		exit 1; \
	fi

run:
	@echo "Starting API server..."
	$(PYTHON) -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

docker-build:
	@echo "Building Docker image..."
	docker build -t ma-rag-rpg .

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/config:/app/config \
		--env-file .env \
		ma-rag-rpg

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "Clean complete"

help:
	@echo "Multi-Agent RAG RPG - Available Make Targets"
	@echo ""
	@echo "Setup:"
	@echo "  make setup           - Create venv and install dependencies"
	@echo "  make install         - Alias for setup"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make test-agents     - Run agent tests only"
	@echo "  make test-core       - Run core framework tests only"
	@echo "  make test-rag        - Run RAG integration tests only"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make run             - Start API server (with auto-reload)"
	@echo "  make ingest          - Run corpus ingestion pipeline"
	@echo "  make eval            - Run RAG evaluation (Phase 6)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run Docker container"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           - Remove build artifacts and cache files"
	@echo "  make help            - Show this help message"

