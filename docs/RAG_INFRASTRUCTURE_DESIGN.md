# RAG Infrastructure Design Document

## Executive Summary

This document provides a comprehensive design for the RAG (Retrieval-Augmented Generation) infrastructure for the Multi-Agent RAG RPG system. The design emphasizes:

- **Componentized Architecture**: Vector database abstraction layer enabling easy swapping between providers (ChromaDB, Pinecone, etc.)
- **Hybrid Retrieval**: BM25 + vector search with configurable fusion strategies
- **Custom Query Rewriting**: Preprocessing and expansion of queries before retrieval
- **Local-First Design**: ChromaDB as default for local development and deployment
- **Docker-Ready**: All components designed for containerized deployment
- **Comprehensive Testing**: Test data and test suite demonstrating ingestion and search capabilities

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Design](#component-design)
3. [Vector Database Abstraction Layer](#vector-database-abstraction-layer)
4. [Ingestion Pipeline](#ingestion-pipeline)
5. [Retrieval System](#retrieval-system)
6. [Query Rewriting](#query-rewriting)
7. [API Design](#api-design)
8. [Test Design](#test-design)
9. [Docker Considerations](#docker-considerations)
10. [Implementation Plan](#implementation-plan)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  POST /ingest│  │  POST /search │  │  GET /health │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Manager (Orchestration)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Query        │  │ Hybrid       │  │ Result       │     │
│  │ Rewriter     │  │ Retriever    │  │ Fusion       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────────┐            ┌──────────────────────┐
│   BM25 Retriever     │            │  Vector Retriever     │
│  ┌────────────────┐  │            │  ┌────────────────┐  │
│  │ BM25 Index     │  │            │  │ Vector DB      │  │
│  │ (rank-bm25)    │  │            │  │ Abstraction    │  │
│  └────────────────┘  │            │  └────────────────┘  │
└──────────────────────┘            └──────────────────────┘
                                            │
                            ┌───────────────┼───────────────┐
                            │               │               │
                            ▼               ▼               ▼
                    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                    │  ChromaDB   │ │  Pinecone   │ │  Other      │
                    │  Provider   │ │  Provider   │ │  Providers  │
                    └─────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow

#### Ingestion Flow
```
Corpus Text → Chunking → BM25 Indexing → Embedding Generation → Vector DB Storage
                    │                              │
                    └──────────> Metadata Storage <┘
```

#### Search Flow
```
Query → Query Rewriting → BM25 Search + Vector Search → Score Fusion → Result Ranking → Return
```

---

## Component Design

### Directory Structure

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py              # Main ingestion orchestrator
│   ├── chunker.py                # Text chunking strategies
│   ├── bm25_indexer.py           # BM25 index building
│   ├── embedder.py               # Embedding generation
│   └── metadata_store.py         # Chunk metadata management
│
├── rag/
│   ├── __init__.py
│   ├── base_retriever.py         # Abstract retriever interface (existing)
│   ├── bm25_retriever.py         # BM25 retriever implementation
│   ├── vector_retriever.py       # Vector retriever implementation
│   ├── hybrid_retriever.py       # Hybrid retrieval with fusion
│   ├── query_rewriter.py         # Query preprocessing and expansion
│   │
│   └── vector_db/                # Vector DB abstraction layer
│       ├── __init__.py
│       ├── base.py                # Abstract vector DB interface
│       ├── chroma_provider.py     # ChromaDB implementation
│       ├── pinecone_provider.py   # Pinecone implementation
│       └── factory.py             # Provider factory
│
├── api/
│   ├── __init__.py
│   ├── app.py                     # FastAPI application
│   ├── endpoints/
│   │   ├── __init__.py
│   │   ├── ingestion.py           # POST /ingest endpoint
│   │   └── search.py              # POST /search endpoint
│   └── schemas/
│       ├── __init__.py
│       ├── ingestion.py           # Pydantic models for ingestion
│       └── search.py              # Pydantic models for search
│
└── core/
    ├── retrieval_manager.py       # Retrieval orchestration (existing)
    └── config.py                  # Configuration (existing, extended)
```

---

## Vector Database Abstraction Layer

### Design Principles

1. **Provider Agnostic**: All vector DB operations go through the abstraction layer
2. **Easy Swapping**: Changing providers requires only configuration changes
3. **Consistent Interface**: All providers implement the same interface
4. **Local-First**: ChromaDB as default for local development
5. **Production Ready**: Support for cloud providers (Pinecone, Weaviate, etc.)

### Abstract Interface

**File: `src/rag/vector_db/base.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VectorDocument:
    """Represents a document with vector embedding."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]

@dataclass
class VectorSearchResult:
    """Result from vector search."""
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class BaseVectorDB(ABC):
    """Abstract interface for vector database providers."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the vector database connection."""
        pass
    
    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a new collection/index."""
        pass
    
    @abstractmethod
    def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument]
    ) -> None:
        """Add documents to the collection."""
        pass
    
    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        pass
    
    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        pass
    
    @abstractmethod
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connections and cleanup."""
        pass
```

### ChromaDB Implementation

**File: `src/rag/vector_db/chroma_provider.py`**

**Key Features:**
- Local file-based storage (default: `data/vector_db/`)
- Persistent collections
- In-memory option for testing
- Metadata filtering support
- Thread-safe operations

**Configuration:**
```yaml
vector_db:
  provider: chroma
  chroma:
    persist_directory: data/vector_db
    collection_name: corpus_embeddings
    in_memory: false
```

### Pinecone Implementation

**File: `src/rag/vector_db/pinecone_provider.py`**

**Key Features:**
- Cloud-based vector database
- API key authentication
- Index management
- Metadata filtering
- Async operations support

**Configuration:**
```yaml
vector_db:
  provider: pinecone
  pinecone:
    api_key: ${PINECONE_API_KEY}
    environment: us-west1-gcp
    index_name: ma-rag-rpg-index
    dimension: 384  # Must match embedding dimension
```

### Provider Factory

**File: `src/rag/vector_db/factory.py`**

```python
from typing import Dict, Any
from .base import BaseVectorDB
from .chroma_provider import ChromaVectorDB
from .pinecone_provider import PineconeVectorDB

class VectorDBFactory:
    """Factory for creating vector DB provider instances."""
    
    @staticmethod
    def create(provider: str, config: Dict[str, Any]) -> BaseVectorDB:
        """Create a vector DB provider instance."""
        if provider == "chroma":
            return ChromaVectorDB(config)
        elif provider == "pinecone":
            return PineconeVectorDB(config)
        else:
            raise ValueError(f"Unsupported vector DB provider: {provider}")
```

---

## Ingestion Pipeline

### Pipeline Components

#### 1. Chunker (`src/ingestion/chunker.py`)

**Strategies:**
- **Sentence-based**: Split on sentence boundaries
- **Paragraph-based**: Split on paragraph boundaries
- **Sliding Window**: Fixed-size chunks with overlap
- **Semantic**: Use embeddings to find natural breakpoints (optional)

**Interface:**
```python
class Chunker:
    def chunk(
        self,
        text: str,
        strategy: str = "sliding_window",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Chunk]:
        """Split text into chunks."""
        pass
```

#### 2. BM25 Indexer (`src/ingestion/bm25_indexer.py`)

**Features:**
- Tokenization and preprocessing
- Index building using `rank-bm25`
- Persistence to disk (pickle)
- Index loading for retrieval

**Interface:**
```python
class BM25Indexer:
    def build_index(self, chunks: List[str]) -> BM25Index:
        """Build BM25 index from chunks."""
        pass
    
    def save_index(self, index: BM25Index, path: str) -> None:
        """Save index to disk."""
        pass
    
    def load_index(self, path: str) -> BM25Index:
        """Load index from disk."""
        pass
```

#### 3. Embedder (`src/ingestion/embedder.py`)

**Features:**
- Support for multiple embedding models:
  - `sentence-transformers/all-MiniLM-L6-v2` (default, 384 dim)
  - `sentence-transformers/all-mpnet-base-v2` (768 dim)
  - OpenAI `text-embedding-ada-002` (1536 dim)
- Batch processing for efficiency
- Caching of embeddings

**Interface:**
```python
class Embedder:
    def __init__(self, model_name: str):
        """Initialize embedder with model."""
        pass
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings in batches."""
        pass
```

#### 4. Metadata Store (`src/ingestion/metadata_store.py`)

**Features:**
- Store chunk metadata (ID, source, position, etc.)
- JSON-based storage
- Fast lookup by chunk ID
- Support for additional metadata fields

**Interface:**
```python
class MetadataStore:
    def save_metadata(self, chunks: List[ChunkMetadata], path: str) -> None:
        """Save chunk metadata to disk."""
        pass
    
    def load_metadata(self, path: str) -> Dict[str, ChunkMetadata]:
        """Load chunk metadata from disk."""
        pass
    
    def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk."""
        pass
```

#### 5. Ingestion Pipeline (`src/ingestion/pipeline.py`)

**Orchestrates:**
1. Load corpus text
2. Chunk text
3. Build BM25 index
4. Generate embeddings
5. Store in vector DB
6. Save metadata
7. Validate and report statistics

**Interface:**
```python
class IngestionPipeline:
    def __init__(
        self,
        chunker: Chunker,
        bm25_indexer: BM25Indexer,
        embedder: Embedder,
        vector_db: BaseVectorDB,
        metadata_store: MetadataStore
    ):
        """Initialize pipeline with components."""
        pass
    
    def ingest(
        self,
        corpus_path: str,
        collection_name: str = "corpus_embeddings",
        overwrite: bool = False
    ) -> IngestionResult:
        """Run full ingestion pipeline."""
        pass
```

### Ingestion Result

```python
@dataclass
class IngestionResult:
    """Result from ingestion pipeline."""
    total_chunks: int
    bm25_index_path: str
    vector_db_collection: str
    metadata_path: str
    embedding_model: str
    embedding_dimension: int
    duration_seconds: float
    statistics: Dict[str, Any]
```

---

## Retrieval System

### BM25 Retriever

**File: `src/rag/bm25_retriever.py`**

**Features:**
- Load BM25 index from disk
- Query preprocessing (tokenization, normalization)
- Score normalization
- Top-k retrieval

**Interface:**
```python
class BM25Retriever(BaseRetriever):
    def __init__(self, index_path: str):
        """Initialize with BM25 index."""
        pass
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using BM25."""
        pass
```

### Vector Retriever

**File: `src/rag/vector_retriever.py`**

**Features:**
- Uses vector DB abstraction layer
- Query embedding generation
- Similarity search
- Metadata filtering

**Interface:**
```python
class VectorRetriever(BaseRetriever):
    def __init__(
        self,
        vector_db: BaseVectorDB,
        collection_name: str,
        embedder: Embedder
    ):
        """Initialize with vector DB and embedder."""
        pass
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using vector search."""
        pass
```

### Hybrid Retriever

**File: `src/rag/hybrid_retriever.py`**

**Fusion Strategies:**

1. **Reciprocal Rank Fusion (RRF)** (default)
   - Combines rankings from both retrievers
   - Formula: `score = 1 / (k + rank)`
   - Default k=60

2. **Weighted Score Combination**
   - Normalizes scores from both retrievers
   - Combines: `final_score = bm25_weight * bm25_score + vector_weight * vector_score`

3. **Re-ranking** (optional, future)
   - Use cross-encoder for final ranking

**Interface:**
```python
class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        fusion_strategy: str = "rrf",
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60
    ):
        """Initialize hybrid retriever."""
        pass
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve using hybrid approach."""
        pass
```

---

## Query Rewriting

### Query Rewriter

**File: `src/rag/query_rewriter.py`**

**Techniques:**

1. **Query Expansion**
   - Synonym expansion using WordNet or custom dictionaries
   - Entity recognition and expansion
   - Related term addition

2. **Query Decomposition**
   - Split complex queries into sub-queries
   - Combine results from sub-queries

3. **Query Normalization**
   - Lowercasing
   - Stop word removal (optional)
   - Stemming/lemmatization (optional)

4. **LLM-Based Rewriting** (optional)
   - Use LLM to rewrite queries for better retrieval
   - Example: "Arthur Dent lies in front of bulldozer" → "Arthur Dent protests demolition of his house by lying in front of bulldozer"

**Interface:**
```python
class QueryRewriter:
    def __init__(
        self,
        enable_expansion: bool = True,
        enable_decomposition: bool = False,
        enable_llm_rewriting: bool = False,
        llm_client: Optional[LLMClient] = None
    ):
        """Initialize query rewriter."""
        pass
    
    def rewrite(self, query: str) -> str:
        """Rewrite query for better retrieval."""
        pass
    
    def expand(self, query: str) -> str:
        """Expand query with synonyms and related terms."""
        pass
```

**Configuration:**
```yaml
retrieval:
  query_rewriter:
    enabled: true
    expansion: true
    decomposition: false
    llm_rewriting: false
```

---

## API Design

### Ingestion API

**Endpoint: `POST /ingest`**

**Request:**
```json
{
  "corpus_path": "data/corpus.txt",
  "collection_name": "corpus_embeddings",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "overwrite": false
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "total_chunks": 1234,
    "bm25_index_path": "data/indices/bm25_index.pkl",
    "vector_db_collection": "corpus_embeddings",
    "metadata_path": "data/indices/chunks.json",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "duration_seconds": 45.2,
    "statistics": {
      "avg_chunk_size": 487,
      "total_tokens": 567890
    }
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": "Collection already exists. Use overwrite=true to replace.",
  "code": "COLLECTION_EXISTS"
}
```

### Search API

**Endpoint: `POST /search`**

**Request:**
```json
{
  "query": "Arthur Dent lies in front of bulldozer",
  "top_k": 10,
  "use_hybrid": true,
  "fusion_strategy": "rrf",
  "rewrite_query": true,
  "filters": {
    "min_score": 0.5
  }
}
```

**Response:**
```json
{
  "query": "Arthur Dent lies in front of bulldozer",
  "rewritten_query": "Arthur Dent lies in front of bulldozer protest demolition",
  "results": [
    {
      "chunk_id": "chunk_123",
      "chunk_text": "Arthur Dent lay in the mud...",
      "score": 0.87,
      "bm25_score": 0.45,
      "vector_score": 0.92,
      "metadata": {
        "source": "corpus.txt",
        "position": 1234,
        "chunk_index": 56
      }
    }
  ],
  "total_results": 10,
  "retrieval_time_ms": 45.2
}
```

### Health Check API

**Endpoint: `GET /health`**

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "bm25_index": "loaded",
    "vector_db": "connected",
    "collection": "corpus_embeddings",
    "total_documents": 1234
  }
}
```

---

## Test Design

### Test Data

**File: `tests/data/test_corpus.txt`**

Small, focused corpus for testing (e.g., first chapter of a book or synthetic test data).

**File: `tests/data/test_queries.json`**

```json
{
  "queries": [
    {
      "id": "q1",
      "query": "Arthur Dent lies in front of bulldozer",
      "expected_chunk_ids": ["chunk_123", "chunk_124", "chunk_125"],
      "expected_keywords": ["Arthur", "Dent", "bulldozer", "lies"],
      "min_relevant_results": 3
    },
    {
      "id": "q2",
      "query": "Marvin the robot complains",
      "expected_chunk_ids": ["chunk_456", "chunk_457"],
      "expected_keywords": ["Marvin", "robot", "complains"],
      "min_relevant_results": 2
    }
  ]
}
```

### Test Suite Structure

```
tests/
├── test_ingestion/
│   ├── test_chunker.py
│   ├── test_bm25_indexer.py
│   ├── test_embedder.py
│   ├── test_metadata_store.py
│   └── test_pipeline.py
│
├── test_rag/
│   ├── test_bm25_retriever.py
│   ├── test_vector_retriever.py
│   ├── test_hybrid_retriever.py
│   ├── test_query_rewriter.py
│   └── test_vector_db/
│       ├── test_chroma_provider.py
│       ├── test_pinecone_provider.py
│       └── test_factory.py
│
├── test_api/
│   ├── test_ingestion_endpoint.py
│   └── test_search_endpoint.py
│
└── test_integration/
    ├── test_ingestion_to_search.py
    └── test_hybrid_retrieval.py
```

### Key Test Cases

#### Ingestion Tests

1. **Chunker Tests**
   - Test all chunking strategies
   - Verify chunk sizes and overlaps
   - Test edge cases (empty text, very short text)

2. **BM25 Indexer Tests**
   - Build index from test corpus
   - Verify index persistence and loading
   - Test retrieval from index

3. **Embedder Tests**
   - Test embedding generation
   - Verify embedding dimensions
   - Test batch processing

4. **Pipeline Tests**
   - End-to-end ingestion
   - Verify all outputs (BM25 index, vector DB, metadata)
   - Test overwrite behavior

#### Retrieval Tests

1. **BM25 Retriever Tests**
   - Test retrieval with various queries
   - Verify score ordering
   - Test filtering

2. **Vector Retriever Tests**
   - Test vector search
   - Verify similarity scores
   - Test metadata filtering

3. **Hybrid Retriever Tests**
   - Test RRF fusion
   - Test weighted fusion
   - Verify result diversity
   - Compare with individual retrievers

4. **Query Rewriter Tests**
   - Test query expansion
   - Test query normalization
   - Test LLM rewriting (if enabled)

#### Integration Tests

1. **Ingestion to Search Flow**
   - Ingest test corpus
   - Search with test queries
   - Verify results match expectations

2. **Hybrid Retrieval Integration**
   - Compare BM25-only, vector-only, and hybrid results
   - Verify hybrid improves recall

### Test Data Generation

**File: `tests/fixtures/test_data_generator.py`**

```python
class TestDataGenerator:
    """Generate test data for RAG infrastructure."""
    
    def generate_test_corpus(self, num_chapters: int = 5) -> str:
        """Generate synthetic test corpus."""
        pass
    
    def generate_test_queries(
        self,
        corpus: str,
        num_queries: int = 10
    ) -> List[TestQuery]:
        """Generate test queries from corpus."""
        pass
```

---

## Docker Considerations

### Volume Mounts

**Required Volumes:**
- `data/` - Corpus and indices (persistent)
- `data/vector_db/` - ChromaDB data (persistent)
- `data/indices/` - BM25 index and metadata (persistent)

### Environment Variables

```bash
# Vector DB Configuration
VECTOR_DB_PROVIDER=chroma  # or pinecone
CHROMA_PERSIST_DIRECTORY=/app/data/vector_db
CHROMA_COLLECTION_NAME=corpus_embeddings

# Pinecone (if using)
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=ma-rag-rpg-index

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Ingestion Paths
CORPUS_PATH=/app/data/corpus.txt
BM25_INDEX_PATH=/app/data/indices/bm25_index.pkl
METADATA_PATH=/app/data/indices/chunks.json
```

### Dockerfile Updates

**Key Considerations:**
1. Install sentence-transformers models at build time (optional, for faster startup)
2. Create data directories with proper permissions
3. Expose vector DB port if using ChromaDB server mode
4. Health check endpoint for container orchestration

**Updated Dockerfile Structure:**
```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p /app/data/indices /app/data/vector_db && \
    chmod -R 755 /app/data

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (Optional)

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - VECTOR_DB_PROVIDER=chroma
      - CHROMA_PERSIST_DIRECTORY=/app/data/vector_db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Implementation Plan

### Phase 1: Vector DB Abstraction Layer

**Tasks:**
1. Create `BaseVectorDB` abstract interface
2. Implement `ChromaVectorDB` provider
3. Implement `PineconeVectorDB` provider (stub for future)
4. Create `VectorDBFactory`
5. Add configuration support for vector DB selection
6. Write unit tests for abstraction layer

**Deliverables:**
- `src/rag/vector_db/base.py`
- `src/rag/vector_db/chroma_provider.py`
- `src/rag/vector_db/pinecone_provider.py`
- `src/rag/vector_db/factory.py`
- `tests/test_rag/test_vector_db/`

### Phase 2: Ingestion Pipeline

**Tasks:**
1. Implement `Chunker` with multiple strategies
2. Implement `BM25Indexer`
3. Implement `Embedder` with model support
4. Implement `MetadataStore`
5. Implement `IngestionPipeline` orchestrator
6. Create CLI script `scripts/ingest.py`
7. Write comprehensive tests

**Deliverables:**
- `src/ingestion/chunker.py`
- `src/ingestion/bm25_indexer.py`
- `src/ingestion/embedder.py`
- `src/ingestion/metadata_store.py`
- `src/ingestion/pipeline.py`
- `scripts/ingest.py`
- `tests/test_ingestion/`

### Phase 3: Retrieval System

**Tasks:**
1. Implement `BM25Retriever`
2. Implement `VectorRetriever` using abstraction layer
3. Implement `HybridRetriever` with fusion strategies
4. Implement `QueryRewriter`
5. Update `RetrievalManager` to use hybrid retriever
6. Write comprehensive tests

**Deliverables:**
- `src/rag/bm25_retriever.py`
- `src/rag/vector_retriever.py`
- `src/rag/hybrid_retriever.py`
- `src/rag/query_rewriter.py`
- Updated `src/core/retrieval_manager.py`
- `tests/test_rag/`

### Phase 4: API Endpoints

**Tasks:**
1. Create FastAPI application structure
2. Implement `POST /ingest` endpoint
3. Implement `POST /search` endpoint
4. Implement `GET /health` endpoint
5. Add request/response schemas
6. Add error handling and validation
7. Write API tests

**Deliverables:**
- `src/api/app.py`
- `src/api/endpoints/ingestion.py`
- `src/api/endpoints/search.py`
- `src/api/schemas/ingestion.py`
- `src/api/schemas/search.py`
- `tests/test_api/`

### Phase 5: Test Data and Integration Tests

**Tasks:**
1. Create test corpus
2. Create test queries with ground truth
3. Implement test data generator
4. Write integration tests (ingestion → search)
5. Write end-to-end API tests
6. Document test execution

**Deliverables:**
- `tests/data/test_corpus.txt`
- `tests/data/test_queries.json`
- `tests/fixtures/test_data_generator.py`
- `tests/test_integration/`

### Phase 6: Docker and Documentation

**Tasks:**
1. Update Dockerfile with data directory setup
2. Create docker-compose.yml (optional)
3. Update Makefile with new targets
4. Update README with setup instructions
5. Create ingestion and search API documentation
6. Document configuration options

**Deliverables:**
- Updated `Dockerfile`
- `docker-compose.yml` (optional)
- Updated `Makefile`
- Updated `README.md`
- `docs/API.md`
- `docs/CONFIGURATION.md`

---

## Configuration Schema

### Extended Configuration

**File: `config/config.yaml`**

```yaml
# Vector Database Configuration
vector_db:
  provider: chroma  # chroma, pinecone, etc.
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

# ... existing agent and session config ...
```

---

## Dependencies

### New Dependencies

**Add to `requirements.txt`:**

```txt
# Vector Database
chromadb>=0.4.0
pinecone-client>=2.2.0  # Optional, for Pinecone support

# BM25
rank-bm25>=0.2.2

# Embeddings
sentence-transformers>=2.2.0

# Text Processing
nltk>=3.8.0
spacy>=3.7.0  # Optional, for advanced NLP

# Query Expansion (optional)
wordnet>=0.0.1  # Via nltk
```

---

## Success Criteria

### Functional Requirements

1. ✅ **Ingestion API**: Successfully ingest corpus and create indices
2. ✅ **Search API**: Return relevant results using hybrid retrieval
3. ✅ **Query Rewriting**: Improve retrieval quality with query expansion
4. ✅ **Provider Swapping**: Change vector DB provider via configuration only
5. ✅ **Docker Support**: Full functionality in containerized environment

### Performance Requirements

1. **Ingestion**: Process 10,000 chunks in < 5 minutes (local)
2. **Search**: Return results in < 200ms (p95)
3. **Memory**: < 2GB RAM for local ChromaDB with 10K chunks

### Test Coverage

1. **Unit Tests**: > 80% coverage for all components
2. **Integration Tests**: Full ingestion → search flow tested
3. **API Tests**: All endpoints tested with various inputs

---

## Future Enhancements

1. **Additional Vector DB Providers**: Weaviate, Qdrant, Milvus
2. **Advanced Query Rewriting**: LLM-based query rewriting
3. **Re-ranking**: Cross-encoder for final result ranking
4. **Caching**: Redis-based caching for frequent queries
5. **Monitoring**: Metrics and observability for production
6. **Batch Ingestion**: Support for large-scale corpus updates

---

## Conclusion

This design provides a comprehensive, componentized RAG infrastructure that:

- **Separates concerns** through clear abstraction layers
- **Enables easy provider swapping** via the vector DB abstraction
- **Supports local development** with ChromaDB as default
- **Scales to production** with cloud provider support
- **Is fully testable** with comprehensive test suite
- **Is Docker-ready** for easy deployment

The implementation follows Python best practices, uses type hints throughout, and maintains clear separation between components for maintainability and extensibility.

