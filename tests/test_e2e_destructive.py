"""Destructive end-to-end tests for full ingestion and retrieval pipeline.

These tests do NOT use mocks and verify actual ChromaDB and BM25 operations.
They clear test indices before and after testing to ensure clean state.
"""

import pytest
import shutil
from pathlib import Path

from src.ingestion.chunker import Chunker
from src.ingestion.bm25_indexer import BM25Indexer
from src.ingestion.metadata_store import MetadataStore
from src.ingestion.embedder import Embedder
from src.ingestion.pipeline import IngestionPipeline
from src.rag.bm25_retriever import BM25Retriever
from src.rag.vector_retriever import VectorRetriever
from src.rag.vector_db.chroma_provider import ChromaVectorDB
from src.core.base_agent import RetrievalResult


@pytest.fixture
def test_indices_dir():
    """Use the fixed test indices directory."""
    test_dir = Path(__file__).parent.parent / "data" / "test_data" / "indices"
    test_dir.mkdir(parents=True, exist_ok=True)
    return str(test_dir)


@pytest.fixture
def test_corpus_file():
    """Use the existing test corpus file."""
    corpus_path = Path(__file__).parent.parent / "data" / "test_data" / "test_corpus.txt"
    # Use existing test corpus file
    assert corpus_path.exists(), f"Test corpus file not found at {corpus_path}"
    return str(corpus_path)


class TestEndToEndDestructive:
    """Destructive end-to-end tests for full ingestion and retrieval pipeline."""

    def test_full_pipeline_end_to_end(self, test_indices_dir, test_corpus_file):
        """Complete end-to-end test: clear, ingest, search, retrieve, clear again."""
        test_collection = "test_e2e_collection"
        test_dir = Path(test_indices_dir)

        # PHASE 1: Clear existing test indices
        print("\n=== PHASE 1: Clearing existing test indices ===")
        vector_db_dir = test_dir / "vector_db"
        bm25_index_path = test_dir / "bm25_index.pkl"
        metadata_path = test_dir / "metadata.json"

        # Clear vector DB
        if vector_db_dir.exists():
            print(f"Removing existing vector DB at {vector_db_dir}")
            shutil.rmtree(vector_db_dir)

        # Clear BM25 index
        if bm25_index_path.exists():
            print(f"Removing existing BM25 index at {bm25_index_path}")
            bm25_index_path.unlink()

        # Clear metadata
        if metadata_path.exists():
            print(f"Removing existing metadata at {metadata_path}")
            metadata_path.unlink()

        print("Test indices cleared successfully")

        # PHASE 2: Ingest test corpus
        print("\n=== PHASE 2: Ingesting test corpus ===")

        # Create components (no mocks!)
        chunker = Chunker()
        bm25_indexer = BM25Indexer()
        metadata_store = MetadataStore()
        embedder = Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Create vector DB
        vector_db_config = {
            "persist_directory": str(vector_db_dir),
            "in_memory": False
        }
        vector_db = ChromaVectorDB(vector_db_config)

        # Create and run ingestion pipeline
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )

        result = pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name=test_collection,
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50
        )

        print(f"Ingestion complete: {result.total_chunks} chunks processed")
        print(f"BM25 index: {result.bm25_index_path}")
        print(f"Metadata: {result.metadata_path}")
        print(f"Vector DB collection: {result.vector_db_collection}")

        # Verify ingestion results
        assert result.total_chunks > 0, "No chunks were created during ingestion"
        assert Path(result.bm25_index_path).exists(), "BM25 index file not created"
        assert Path(result.metadata_path).exists(), "Metadata file not created"
        assert vector_db.collection_exists(test_collection), "Vector DB collection not created"

        collection_stats = vector_db.get_collection_stats(test_collection)
        assert collection_stats["count"] == result.total_chunks, \
            f"Vector DB count mismatch: {collection_stats['count']} != {result.total_chunks}"

        # PHASE 3: Test BM25 search
        print("\n=== PHASE 3: Testing BM25 search ===")

        bm25_retriever = BM25Retriever(
            index_path=result.bm25_index_path,
            metadata_path=result.metadata_path
        )

        # Verify BM25 retriever is loaded
        assert bm25_retriever.is_loaded(), "BM25 retriever failed to load"
        assert len(bm25_retriever.chunks) > 0, "BM25 retriever has no chunks"
        print(f"BM25 retriever loaded with {len(bm25_retriever.chunks)} chunks")

        # Perform BM25 search with query that matches corpus content
        bm25_query = "Gandalf wizard magic"

        # DEBUG: Get raw BM25 scores first
        import numpy as np
        tokenized_query = bm25_query.lower().split()
        raw_scores = bm25_retriever.index.get_scores(tokenized_query)
        print(f"\nDEBUG - Raw BM25 scores for '{bm25_query}':")
        print(f"  Max raw score: {np.max(raw_scores):.6f}")
        print(f"  Min raw score: {np.min(raw_scores):.6f}")
        print(f"  Mean raw score: {np.mean(raw_scores):.6f}")
        print(f"  Top 5 raw scores: {sorted(raw_scores, reverse=True)[:5]}")

        bm25_results = bm25_retriever.retrieve(bm25_query, top_k=5)

        print(f"\nBM25 search for '{bm25_query}' returned {len(bm25_results)} results")
        assert len(bm25_results) > 0, "BM25 search returned no results"
        assert all(isinstance(r, RetrievalResult) for r in bm25_results), \
            "BM25 results are not RetrievalResult objects"
        assert all(r.score >= 0 for r in bm25_results), "BM25 scores are invalid"
        assert all(r.chunk_text for r in bm25_results), "BM25 results have empty chunk text"

        # Verify results are sorted by score
        bm25_scores = [r.score for r in bm25_results]
        assert bm25_scores == sorted(bm25_scores, reverse=True), \
            "BM25 results are not sorted by score"

        print(f"Top BM25 result score: {bm25_results[0].score:.4f}")
        print(f"Top BM25 result preview: {bm25_results[0].chunk_text[:100]}...")

        # PHASE 4: Test ChromaDB vector retrieval
        print("\n=== PHASE 4: Testing ChromaDB vector retrieval ===")

        vector_retriever = VectorRetriever(
            vector_db=vector_db,
            collection_name=test_collection,
            embedder=embedder
        )

        # Perform vector search with query that matches corpus content
        vector_query = "Gandalf wizard magic"
        vector_results = vector_retriever.retrieve(vector_query, top_k=5)

        print(f"Vector search for '{vector_query}' returned {len(vector_results)} results")
        assert len(vector_results) > 0, "Vector search returned no results"
        assert all(isinstance(r, RetrievalResult) for r in vector_results), \
            "Vector results are not RetrievalResult objects"
        assert all(r.score > 0 for r in vector_results), "Vector scores are invalid"
        assert all(r.chunk_text for r in vector_results), "Vector results have empty chunk text"

        # Verify results are sorted by score
        vector_scores = [r.score for r in vector_results]
        assert vector_scores == sorted(vector_scores, reverse=True), \
            "Vector results are not sorted by score"

        print(f"Top vector result score: {vector_results[0].score:.4f}")
        print(f"Top vector result preview: {vector_results[0].chunk_text[:100]}...")

        # PHASE 5: Clear test indices again (cleanup)
        print("\n=== PHASE 5: Cleaning up test indices ===")

        # Clear vector DB
        if vector_db_dir.exists():
            print(f"Removing vector DB at {vector_db_dir}")
            shutil.rmtree(vector_db_dir)

        # Clear BM25 index
        if bm25_index_path.exists():
            print(f"Removing BM25 index at {bm25_index_path}")
            bm25_index_path.unlink()

        # Clear metadata
        if metadata_path.exists():
            print(f"Removing metadata at {metadata_path}")
            metadata_path.unlink()

        # Verify cleanup
        assert not vector_db_dir.exists(), "Vector DB directory still exists after cleanup"
        assert not bm25_index_path.exists(), "BM25 index file still exists after cleanup"
        assert not metadata_path.exists(), "Metadata file still exists after cleanup"

        print("Test indices cleaned up successfully")
        print("\n=== END-TO-END TEST COMPLETE ===")
