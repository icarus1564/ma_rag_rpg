# RAG Infrastructure Design Documentation

## Overview

This directory contains comprehensive design documentation for the RAG (Retrieval-Augmented Generation) infrastructure of the Multi-Agent RAG RPG system.

## Documentation Structure

### 1. [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md)

**Complete design document** covering:
- Architecture overview
- Component design
- Vector database abstraction layer
- Ingestion pipeline
- Retrieval system
- Query rewriting
- API design
- Test design
- Docker considerations
- Implementation plan

**Use this document for:**
- Understanding the complete system architecture
- Detailed component specifications
- Design decisions and rationale
- Configuration schemas

### 2. [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md)

**Detailed implementation plan** with:
- Phase-by-phase breakdown
- Specific tasks for each component
- Code interfaces and specifications
- Test requirements
- Deliverables for each phase

**Use this document for:**
- Planning implementation work
- Understanding task dependencies
- Code structure and interfaces
- Testing requirements

### 3. [TEST_DATA_SPECIFICATION.md](./TEST_DATA_SPECIFICATION.md)

**Test data requirements** including:
- Test corpus structure and requirements
- Test query format and categories
- Ground truth generation process
- Test data generator implementation
- Test execution procedures

**Use this document for:**
- Creating test data
- Understanding test requirements
- Generating test queries
- Validating test results

### 4. [RAG_DESIGN_SUMMARY.md](./RAG_DESIGN_SUMMARY.md)

**Quick reference summary** with:
- High-level architecture overview
- Key components summary
- Configuration examples
- API endpoint specifications
- File structure
- Success criteria

**Use this document for:**
- Quick reference during implementation
- Understanding system overview
- Configuration examples
- API usage

## Quick Start Guide

### For Design Review

1. **Start with**: [RAG_DESIGN_SUMMARY.md](./RAG_DESIGN_SUMMARY.md)
   - Get high-level overview
   - Understand key components
   - Review configuration examples

2. **Deep dive**: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md)
   - Understand complete architecture
   - Review component designs
   - Check design decisions

3. **Implementation details**: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md)
   - Review implementation phases
   - Understand task breakdown
   - Check code interfaces

4. **Testing**: [TEST_DATA_SPECIFICATION.md](./TEST_DATA_SPECIFICATION.md)
   - Understand test requirements
   - Review test data format
   - Check validation procedures

### For Implementation

1. **Phase 1**: Vector DB Abstraction Layer
   - Review: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Section "Vector Database Abstraction Layer"
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 1

2. **Phase 2**: Ingestion Pipeline
   - Review: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Section "Ingestion Pipeline"
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 2

3. **Phase 3**: Retrieval System
   - Review: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Section "Retrieval System"
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 3

4. **Phase 4**: API Endpoints
   - Review: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Section "API Design"
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 4

5. **Phase 5**: Test Data and Integration Tests
   - Review: [TEST_DATA_SPECIFICATION.md](./TEST_DATA_SPECIFICATION.md)
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 5

6. **Phase 6**: Docker and Documentation
   - Review: [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Section "Docker Considerations"
   - Tasks: [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Phase 6

## Key Design Principles

1. **Componentized Architecture**: All components are independent and testable
2. **Provider Abstraction**: Vector DB providers can be swapped via configuration
3. **Hybrid Retrieval**: Combines BM25 (keyword) and vector (semantic) search
4. **Query Rewriting**: Improves retrieval quality through expansion and normalization
5. **Local-First**: ChromaDB as default for local development
6. **Docker-Ready**: All components designed for containerized deployment

## Configuration

### Example Configuration

See [config/config.yaml.example](../config/config.yaml.example) for a complete configuration example.

### Key Configuration Sections

1. **Vector DB**: Provider selection and settings
2. **Ingestion**: Corpus path, chunking, embedding model
3. **Retrieval**: Hybrid weights, fusion strategy, query rewriting
4. **Session**: Memory window, token limits
5. **API**: Host, port, logging

## API Endpoints

### POST /ingest

Ingest corpus and create indices (BM25 and vector).

**Request**: See [RAG_DESIGN_SUMMARY.md](./RAG_DESIGN_SUMMARY.md) - API Endpoints

**Response**: Ingestion result with statistics

### POST /search

Search corpus using hybrid retrieval.

**Request**: Query, top_k, fusion strategy, etc.

**Response**: Search results with scores and metadata

### GET /health

Health check endpoint.

**Response**: System status and component health

## Testing

### Test Data

- **Test Corpus**: `tests/data/test_corpus.txt` (1000+ words)
- **Test Queries**: `tests/data/test_queries.json` (10+ queries)
- **Ground Truth**: `tests/data/ground_truth.json` (annotations)

### Test Execution

```bash
# Run all tests
make test

# Run specific test suite
pytest tests/test_ingestion/ -v
pytest tests/test_rag/ -v
pytest tests/test_api/ -v
pytest tests/test_integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Implementation Timeline

- **Phase 1**: Vector DB Abstraction Layer - 2-3 days
- **Phase 2**: Ingestion Pipeline - 3-4 days
- **Phase 3**: Retrieval System - 2-3 days
- **Phase 4**: API Endpoints - 2 days
- **Phase 5**: Test Data and Integration Tests - 2 days
- **Phase 6**: Docker and Documentation - 1-2 days

**Total**: 12-16 days

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

## Questions or Issues?

If you have questions or need clarification:

1. **Design Questions**: Review [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md)
2. **Implementation Questions**: Review [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md)
3. **Testing Questions**: Review [TEST_DATA_SPECIFICATION.md](./TEST_DATA_SPECIFICATION.md)
4. **Quick Reference**: See [RAG_DESIGN_SUMMARY.md](./RAG_DESIGN_SUMMARY.md)

## Status

**Design Status**: ✅ Complete - Awaiting Approval

**Implementation Status**: ⏸️ Not Started - Awaiting Design Approval

**Last Updated**: 2024-01-01

---

## Document Index

- [RAG_INFRASTRUCTURE_DESIGN.md](./RAG_INFRASTRUCTURE_DESIGN.md) - Complete design document
- [RAG_IMPLEMENTATION_PLAN.md](./RAG_IMPLEMENTATION_PLAN.md) - Detailed implementation plan
- [TEST_DATA_SPECIFICATION.md](./TEST_DATA_SPECIFICATION.md) - Test data requirements
- [RAG_DESIGN_SUMMARY.md](./RAG_DESIGN_SUMMARY.md) - Quick reference summary

