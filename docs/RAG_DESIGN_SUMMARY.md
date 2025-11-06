# RAG Infrastructure Design Summary

## Quick Reference

This document provides a high-level summary of the RAG infrastructure design. For detailed information, refer to:

- **RAG_INFRASTRUCTURE_DESIGN.md**: Complete design document
- **RAG_IMPLEMENTATION_PLAN.md**: Detailed implementation plan
- **TEST_DATA_SPECIFICATION.md**: Test data requirements
- **.cursor/DevNotes_Phase2.md**: Implementation notes and lessons learned

## Implementation Status

**Phase 2 Complete**: Ingestion pipeline and retrieval system are fully implemented and tested.

- ✅ Ingestion Pipeline: Complete with 3 chunking strategies, BM25 indexing, embedding generation, and metadata storage
- ✅ Retrieval System: Complete with BM25, vector, and hybrid retrieval (RRF and weighted fusion)
- ✅ Test Coverage: 21 comprehensive tests, 100% pass rate
- ⏸️ Query Rewriter: Deferred to future phase
- ⏸️ API Endpoints: Next phase

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  POST /ingest  │  POST /search  │  GET /health               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Manager (Orchestration)               │
│  Query Rewriter  │  Hybrid Retriever  │  Result Fusion       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────────┐            ┌──────────────────────┐
│   BM25 Retriever     │            │  Vector Retriever     │
│  (rank-bm25)         │            │  (Vector DB Abstraction)│
└──────────────────────┘            └──────────────────────┘
                                            │
                            ┌───────────────┼───────────────┐
                            │               │               │
                            ▼               ▼               ▼
                    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                    │  ChromaDB    │ │  Pinecone   │ │  Other      │
                    │  Provider    │ │  Provider   │ │  Providers  │
                    └─────────────┘ └─────────────┘ └─────────────┘
```

## Key Components

### 1. Vector Database Abstraction Layer

**Purpose**: Enable easy swapping between vector DB providers

**Location**: `src/rag/vector_db/`

**Components**:
- `base.py`: Abstract interface (`BaseVectorDB`)
- `chroma_provider.py`: ChromaDB implementation
- `pinecone_provider.py`: Pinecone implementation (stub)
- `factory.py`: Provider factory

**Key Features**:
- Provider-agnostic interface
- Easy configuration-based swapping
- Local-first (ChromaDB default)
- Production-ready (Pinecone support)

### 2. Ingestion Pipeline

**Purpose**: Process corpus text and create indices

**Location**: `src/ingestion/`

**Components**:
- `chunker.py`: Text chunking strategies
- `bm25_indexer.py`: BM25 index building
- `embedder.py`: Embedding generation
- `metadata_store.py`: Chunk metadata management
- `pipeline.py`: Pipeline orchestrator

**Key Features**:
- Multiple chunking strategies (sentence, paragraph, sliding window)
- BM25 index persistence
- Multiple embedding models support
- Metadata tracking

### 3. Retrieval System

**Purpose**: Retrieve relevant chunks using hybrid approach

**Location**: `src/rag/`

**Components**:
- `bm25_retriever.py`: BM25 retrieval
- `vector_retriever.py`: Vector retrieval
- `hybrid_retriever.py`: Hybrid retrieval with fusion
- `query_rewriter.py`: Query preprocessing and expansion

**Key Features**:
- Hybrid retrieval (BM25 + vector)
- Multiple fusion strategies (RRF, weighted)
- Query rewriting (expansion, normalization)
- Configurable weights and strategies

### 4. API Endpoints

**Purpose**: HTTP API for ingestion and search

**Location**: `src/api/`

**Components**:
- `app.py`: FastAPI application
- `endpoints/ingestion.py`: POST /ingest
- `endpoints/search.py`: POST /search
- `schemas/`: Request/response models

**Key Features**:
- RESTful API design
- Request validation
- Error handling
- Health check endpoint

## Data Flow

### Ingestion Flow

```
Corpus Text
    │
    ▼
Chunking (sentence/paragraph/sliding window)
    │
    ├──► BM25 Indexing ──► BM25 Index (pickle)
    │
    └──► Embedding Generation ──► Vector DB Storage
    │
    └──► Metadata Storage ──► Metadata (JSON)
```

### Search Flow

```
Query
    │
    ▼
Query Rewriting (expansion, normalization)
    │
    ├──► BM25 Search ──► BM25 Results
    │
    └──► Vector Search ──► Vector Results
    │
    ▼
Score Fusion (RRF or weighted)
    │
    ▼
Result Ranking & Deduplication
    │
    ▼
Return Top-K Results
```

## Configuration

### Vector DB Configuration

```yaml
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
```

### Ingestion Configuration

```yaml
ingestion:
  corpus_path: data/corpus.txt
  chunk_size: 500
  chunk_overlap: 50
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  bm25_index_path: data/indices/bm25_index.pkl
  vector_index_path: data/indices/vector_index
  chunk_metadata_path: data/indices/chunks.json
```

### Retrieval Configuration

```yaml
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
```

## API Endpoints

### POST /ingest

**Request**:
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

**Response**:
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

### POST /search

**Request**:
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

**Response**:
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

### GET /health

**Response**:
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

## File Structure

```
src/
├── ingestion/
│   ├── chunker.py              # Text chunking
│   ├── bm25_indexer.py          # BM25 index building
│   ├── embedder.py              # Embedding generation
│   ├── metadata_store.py        # Metadata management
│   └── pipeline.py              # Pipeline orchestrator
│
├── rag/
│   ├── base_retriever.py        # Abstract retriever (existing)
│   ├── bm25_retriever.py        # BM25 retriever
│   ├── vector_retriever.py      # Vector retriever
│   ├── hybrid_retriever.py      # Hybrid retriever
│   ├── query_rewriter.py        # Query rewriting
│   │
│   └── vector_db/               # Vector DB abstraction
│       ├── base.py               # Abstract interface
│       ├── chroma_provider.py    # ChromaDB implementation
│       ├── pinecone_provider.py  # Pinecone implementation
│       └── factory.py            # Provider factory
│
├── api/
│   ├── app.py                    # FastAPI application
│   ├── endpoints/
│   │   ├── ingestion.py          # POST /ingest
│   │   └── search.py             # POST /search
│   └── schemas/
│       ├── ingestion.py          # Ingestion schemas
│       └── search.py            # Search schemas
│
└── core/
    ├── retrieval_manager.py      # Retrieval orchestration (updated)
    └── config.py                # Configuration (extended)
```

## Implementation Phases

### Phase 1: Vector DB Abstraction Layer (2-3 days)
- Create abstract interface
- Implement ChromaDB provider
- Implement Pinecone provider (stub)
- Create provider factory
- Update configuration

### Phase 2: Ingestion Pipeline (3-4 days)
- Implement chunker
- Implement BM25 indexer
- Implement embedder
- Implement metadata store
- Implement pipeline orchestrator
- Create CLI script

### Phase 3: Retrieval System (2-3 days)
- Implement BM25 retriever
- Implement vector retriever
- Implement hybrid retriever
- Implement query rewriter
- Update retrieval manager

### Phase 4: API Endpoints (2 days)
- Create API schemas
- Implement ingestion endpoint
- Implement search endpoint
- Create FastAPI application
- Add health check

### Phase 5: Test Data and Integration Tests (2 days)
- Create test corpus
- Create test queries
- Implement test data generator
- Write integration tests
- Write end-to-end tests

### Phase 6: Docker and Documentation (1-2 days)
- Update Dockerfile
- Create docker-compose.yml (optional)
- Update Makefile
- Update README
- Create API documentation
- Create configuration documentation

**Total**: 12-16 days

## Key Design Decisions

1. **Vector DB Abstraction**: Enables easy provider swapping via configuration
2. **Hybrid Retrieval**: Combines BM25 (keyword) and vector (semantic) search
3. **Query Rewriting**: Improves retrieval quality through expansion and normalization
4. **Componentized Design**: Each component is independent and testable
5. **Local-First**: ChromaDB as default for local development
6. **Docker-Ready**: All components designed for containerized deployment

## Success Criteria

### Functional Requirements
- ✅ Ingestion API successfully creates indices
- ✅ Search API returns relevant results using hybrid retrieval
- ✅ Query rewriting improves retrieval quality
- ✅ Vector DB provider can be swapped via configuration
- ✅ Full functionality in Docker container

### Performance Requirements
- Ingestion: Process 10,000 chunks in < 5 minutes (local)
- Search: Return results in < 200ms (p95)
- Memory: < 2GB RAM for local ChromaDB with 10K chunks

### Test Coverage
- Unit Tests: > 80% coverage for all components
- Integration Tests: Full ingestion → search flow tested
- API Tests: All endpoints tested with various inputs

## Dependencies

### New Dependencies

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
```

## Testing Strategy

### Unit Tests
- Vector DB abstraction layer
- Ingestion components
- Retrieval components
- Query rewriting
- API endpoints

### Integration Tests
- Ingestion → Search flow
- Hybrid retrieval comparison
- End-to-end API tests

### Test Data
- Test corpus (1000+ words)
- Test queries (10+ queries)
- Ground truth annotations

## Docker Considerations

### Volume Mounts
- `data/`: Corpus and indices (persistent)
- `data/vector_db/`: ChromaDB data (persistent)
- `data/indices/`: BM25 index and metadata (persistent)

### Environment Variables
```bash
VECTOR_DB_PROVIDER=chroma
CHROMA_PERSIST_DIRECTORY=/app/data/vector_db
CHROMA_COLLECTION_NAME=corpus_embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CORPUS_PATH=/app/data/corpus.txt
```

### Health Check
- Endpoint: `GET /health`
- Checks: BM25 index loaded, vector DB connected, collection exists

## Next Steps

1. **Review Design**: Review all design documents
2. **Approve Design**: Get approval before implementation
3. **Set Up Environment**: Ensure virtual environment and dependencies
4. **Start Implementation**: Begin with Phase 1 (Vector DB Abstraction)
5. **Iterate**: Test each phase before moving to next
6. **Document**: Update documentation as you implement

## Questions or Issues?

If you have questions or need clarification on any aspect of the design:

1. Review the detailed design documents
2. Check the implementation plan for specific tasks
3. Refer to test data specification for testing requirements
4. Consult configuration examples for setup

---

**Status**: Design Complete - Awaiting Approval

**Last Updated**: 2024-01-01

