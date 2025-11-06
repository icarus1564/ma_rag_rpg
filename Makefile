.PHONY: setup install test ingest eval run docker-build docker-run clean

# Activate virtual environment
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

setup: $(VENV)
	@echo "Setting up virtual environment..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Setup complete! Activate with: source $(VENV)/bin/activate"

install: setup

test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

ingest:
	@echo "Running ingestion pipeline..."
	$(PYTHON) scripts/ingest.py

eval:
	@echo "Running RAG evaluation..."
	$(PYTHON) scripts/eval.py

run:
	@echo "Starting API server..."
	$(PYTHON) -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

docker-build:
	@echo "Building Docker image..."
	docker build -t ma-rag-rpg .

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 ma-rag-rpg

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "Clean complete"

