"""Tests for RAG ingestion and retrieval pipeline."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.ingestion.chunker import Chunker, Chunk
from src.ingestion.embedder import Embedder
from src.ingestion.bm25_indexer import BM25Indexer
from src.ingestion.metadata_store import MetadataStore, ChunkMetadata
from src.ingestion.pipeline import IngestionPipeline, IngestionResult
from src.rag.vector_retriever import VectorRetriever
from src.rag.bm25_retriever import BM25Retriever
from src.rag.hybrid_retriever import HybridRetriever
from src.rag.vector_db.chroma_provider import ChromaVectorDB
from src.rag.vector_db.factory import VectorDBFactory
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


@pytest.fixture
def chunker():
    """Create a Chunker instance."""
    return Chunker()


@pytest.fixture
def embedder():
    """Create an Embedder instance."""
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


@pytest.fixture
def bm25_indexer():
    """Create a BM25Indexer instance."""
    return BM25Indexer()


@pytest.fixture
def metadata_store():
    """Create a MetadataStore instance."""
    return MetadataStore()


@pytest.fixture
def vector_db(test_indices_dir, request):
    """Create a ChromaVectorDB instance with unique database path per test."""
    # Use test name to create unique database path for each test
    test_name = request.node.name.replace("[", "_").replace("]", "_")
    vector_db_dir = Path(test_indices_dir) / "vector_db" / test_name
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "persist_directory": str(vector_db_dir),
        "in_memory": False
    }
    db = ChromaVectorDB(config)
    yield db
    # Cleanup: close database connection after test
    db.close()


class TestChunker:
    """Test Chunker functionality."""
    
    def test_chunk_sliding_window(self, chunker):
        """Test sliding window chunking."""
        text = "This is a test sentence. This is another test sentence. This is a third test sentence."
        chunks = chunker.chunk(text, strategy="sliding_window", chunk_size=30, chunk_overlap=10)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all(chunk.text for chunk in chunks)
        assert all(chunk.id.startswith("chunk_") for chunk in chunks)
    
    def test_chunk_by_sentence(self, chunker):
        """Test sentence-based chunking."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunker.chunk(text, strategy="sentence", chunk_size=50, chunk_overlap=10)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all("sentence" in chunk.metadata.get("strategy", "") for chunk in chunks)
    
    def test_chunk_by_paragraph(self, chunker):
        """Test paragraph-based chunking."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunker.chunk(text, strategy="paragraph", chunk_size=50, chunk_overlap=10)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all("paragraph" in chunk.metadata.get("strategy", "") for chunk in chunks)
    
    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk("", strategy="sliding_window")
        assert len(chunks) == 0
    
    def test_chunk_invalid_strategy(self, chunker):
        """Test chunking with invalid strategy."""
        with pytest.raises(ValueError):
            chunker.chunk("test", strategy="invalid")


class TestEmbedder:
    """Test Embedder functionality."""
    
    def test_embedder_initialization(self, embedder):
        """Test embedder initialization."""
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.model is not None
        assert embedder.dimension > 0
    
    def test_embed_single_text(self, embedder):
        """Test embedding a single text."""
        texts = ["This is a test sentence."]
        embeddings = embedder.embed(texts)
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == embedder.dimension
        assert all(isinstance(x, (int, float)) for x in embeddings[0])
    
    def test_embed_multiple_texts(self, embedder):
        """Test embedding multiple texts."""
        texts = [
            "This is the first sentence.",
            "This is the second sentence.",
            "This is the third sentence."
        ]
        embeddings = embedder.embed(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == embedder.dimension for emb in embeddings)
    
    def test_embed_batch(self, embedder):
        """Test batch embedding."""
        texts = [f"This is sentence {i}." for i in range(10)]
        embeddings = embedder.embed_batch(texts, batch_size=3)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == embedder.dimension for emb in embeddings)
    
    def test_embed_empty_list(self, embedder):
        """Test embedding empty list."""
        embeddings = embedder.embed([])
        assert len(embeddings) == 0


class TestBM25Indexer:
    """Test BM25Indexer functionality."""
    
    def test_build_index(self, bm25_indexer, test_indices_dir):
        """Test building BM25 index."""
        chunks = [
            "This is the first chunk about machine learning.",
            "This is the second chunk about artificial intelligence.",
            "This is the third chunk about deep learning."
        ]
        
        index = bm25_indexer.build_index(chunks)
        assert index is not None
    
    def test_save_and_load_index(self, bm25_indexer, test_indices_dir):
        """Test saving and loading BM25 index."""
        chunks = [
            "This is the first chunk.",
            "This is the second chunk.",
            "This is the third chunk."
        ]

        index = bm25_indexer.build_index(chunks)
        index_path = str(Path(test_indices_dir) / "test_index.pkl")
        
        bm25_indexer.save_index(index, index_path)
        assert Path(index_path).exists()
        
        loaded_index = bm25_indexer.load_index(index_path)
        assert loaded_index is not None
    
    def test_build_index_empty_chunks(self, bm25_indexer):
        """Test building index with empty chunks."""
        with pytest.raises(ValueError):
            bm25_indexer.build_index([])


class TestMetadataStore:
    """Test MetadataStore functionality."""
    
    def test_save_and_load_metadata(self, metadata_store, test_indices_dir):
        """Test saving and loading metadata."""
        chunks = [
            ChunkMetadata(
                chunk_id="chunk_0",
                text="First chunk",
                start_pos=0,
                end_pos=11,
                chunk_index=0,
                source="test.txt"
            ),
            ChunkMetadata(
                chunk_id="chunk_1",
                text="Second chunk",
                start_pos=12,
                end_pos=24,
                chunk_index=1,
                source="test.txt"
            )
        ]

        metadata_path = str(Path(test_indices_dir) / "metadata.json")
        metadata_store.save_metadata(chunks, metadata_path)
        assert Path(metadata_path).exists()
        
        loaded_metadata = metadata_store.load_metadata(metadata_path)
        assert len(loaded_metadata) == 2
        assert "chunk_0" in loaded_metadata
        assert "chunk_1" in loaded_metadata
    
    def test_get_chunk_metadata(self, metadata_store, test_indices_dir):
        """Test getting specific chunk metadata."""
        chunks = [
            ChunkMetadata(
                chunk_id="chunk_0",
                text="First chunk",
                start_pos=0,
                end_pos=11,
                chunk_index=0,
                source="test.txt"
            )
        ]

        metadata_path = str(Path(test_indices_dir) / "metadata.json")
        metadata_store.save_metadata(chunks, metadata_path)
        
        metadata = metadata_store.get_chunk_metadata("chunk_0", metadata_path)
        assert metadata is not None
        assert metadata.chunk_id == "chunk_0"
        assert metadata.text == "First chunk"


class TestIngestionPipeline:
    """Test IngestionPipeline functionality."""
    
    def test_ingest_pipeline(self, chunker, embedder, bm25_indexer, metadata_store, vector_db, test_corpus_file, test_indices_dir):
        """Test full ingestion pipeline."""
        # Use test indices directory
        indices_dir = Path(test_indices_dir)
        
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        result = pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name="test_collection",
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50,
            indices_dir=test_indices_dir
        )
        
        assert isinstance(result, IngestionResult)
        assert result.total_chunks > 0
        assert result.vector_db_collection == "test_collection"
        assert result.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert result.embedding_dimension > 0
        assert result.duration_seconds > 0
        assert "avg_chunk_size" in result.statistics
        
        # Verify files were created
        assert Path(result.bm25_index_path).exists()
        assert Path(result.metadata_path).exists()
        
        # Verify vector DB collection exists
        assert vector_db.collection_exists("test_collection")
        stats = vector_db.get_collection_stats("test_collection")
        assert stats["count"] == result.total_chunks
    
    def test_ingest_pipeline_nonexistent_file(self, chunker, embedder, bm25_indexer, metadata_store, vector_db):
        """Test ingestion with nonexistent file."""
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        with pytest.raises(FileNotFoundError):
            pipeline.ingest("nonexistent.txt", collection_name="test")


class TestVectorRetriever:
    """Test VectorRetriever functionality."""
    
    def test_vector_retrieval(self, embedder, vector_db, test_corpus_file, test_indices_dir):
        """Test vector retrieval."""
        # First, ingest data
        from src.ingestion.chunker import Chunker
        from src.ingestion.bm25_indexer import BM25Indexer
        from src.ingestion.metadata_store import MetadataStore
        from src.ingestion.pipeline import IngestionPipeline

        chunker = Chunker()
        bm25_indexer = BM25Indexer()
        metadata_store = MetadataStore()

        indices_dir = Path(test_indices_dir)
        
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name="test_collection",
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50,
            indices_dir=test_indices_dir
        )
        
        # Now test retrieval
        retriever = VectorRetriever(
            vector_db=vector_db,
            collection_name="test_collection",
            embedder=embedder
        )
        
        results = retriever.retrieve("library of Alexandria", top_k=3)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.score > 0 for r in results)
        assert all(r.chunk_text for r in results)
        assert all(r.chunk_id for r in results)
        
        # Verify results are sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestBM25Retriever:
    """Test BM25Retriever functionality."""
    
    def test_bm25_retrieval(self, embedder, vector_db, test_corpus_file, test_indices_dir):
        """Test BM25 retrieval."""
        # First, ingest data
        from src.ingestion.chunker import Chunker
        from src.ingestion.bm25_indexer import BM25Indexer
        from src.ingestion.metadata_store import MetadataStore
        from src.ingestion.pipeline import IngestionPipeline

        chunker = Chunker()
        bm25_indexer = BM25Indexer()
        metadata_store = MetadataStore()

        indices_dir = Path(test_indices_dir)
        
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        result = pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name="test_collection",
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50,
            indices_dir=test_indices_dir
        )
        
        # Now test BM25 retrieval
        retriever = BM25Retriever(
            index_path=result.bm25_index_path,
            metadata_path=result.metadata_path
        )
        
        results = retriever.retrieve("library of Alexandria", top_k=3)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.score >= 0 for r in results)
        assert all(r.chunk_text for r in results)
        assert all(r.chunk_id for r in results)
        
        # Verify results are sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestHybridRetriever:
    """Test HybridRetriever functionality."""
    
    def test_hybrid_retrieval_rrf(self, embedder, vector_db, test_corpus_file, test_indices_dir):
        """Test hybrid retrieval with RRF fusion."""
        # First, ingest data
        from src.ingestion.chunker import Chunker
        from src.ingestion.bm25_indexer import BM25Indexer
        from src.ingestion.metadata_store import MetadataStore
        from src.ingestion.pipeline import IngestionPipeline

        chunker = Chunker()
        bm25_indexer = BM25Indexer()
        metadata_store = MetadataStore()

        indices_dir = Path(test_indices_dir)
        
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        result = pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name="test_collection",
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50,
            indices_dir=test_indices_dir
        )
        
        # Create retrievers
        bm25_retriever = BM25Retriever(
            index_path=result.bm25_index_path,
            metadata_path=result.metadata_path
        )
        
        vector_retriever = VectorRetriever(
            vector_db=vector_db,
            collection_name="test_collection",
            embedder=embedder
        )
        
        # Create hybrid retriever with RRF
        hybrid_retriever = HybridRetriever(
            bm25_retriever=bm25_retriever,
            vector_retriever=vector_retriever,
            fusion_strategy="rrf",
            rrf_k=60
        )
        
        results = hybrid_retriever.retrieve("library of Alexandria", top_k=5)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.score > 0 for r in results)
        assert all(r.chunk_text for r in results)
        assert all(r.chunk_id for r in results)
        
        # Verify results are sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_hybrid_retrieval_weighted(self, embedder, vector_db, test_corpus_file, test_indices_dir):
        """Test hybrid retrieval with weighted fusion."""
        # First, ingest data
        from src.ingestion.chunker import Chunker
        from src.ingestion.bm25_indexer import BM25Indexer
        from src.ingestion.metadata_store import MetadataStore
        from src.ingestion.pipeline import IngestionPipeline

        chunker = Chunker()
        bm25_indexer = BM25Indexer()
        metadata_store = MetadataStore()

        indices_dir = Path(test_indices_dir)
        
        pipeline = IngestionPipeline(
            chunker=chunker,
            bm25_indexer=bm25_indexer,
            embedder=embedder,
            vector_db=vector_db,
            metadata_store=metadata_store
        )
        
        result = pipeline.ingest(
            corpus_path=test_corpus_file,
            collection_name="test_collection",
            overwrite=True,
            chunk_size=200,
            chunk_overlap=50,
            indices_dir=test_indices_dir
        )
        
        # Create retrievers
        bm25_retriever = BM25Retriever(
            index_path=result.bm25_index_path,
            metadata_path=result.metadata_path
        )
        
        vector_retriever = VectorRetriever(
            vector_db=vector_db,
            collection_name="test_collection",
            embedder=embedder
        )
        
        # Create hybrid retriever with weighted fusion
        hybrid_retriever = HybridRetriever(
            bm25_retriever=bm25_retriever,
            vector_retriever=vector_retriever,
            fusion_strategy="weighted",
            bm25_weight=0.6,
            vector_weight=0.4
        )
        
        results = hybrid_retriever.retrieve("machine learning", top_k=5)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.score >= 0 for r in results)
        assert all(r.chunk_text for r in results)
        assert all(r.chunk_id for r in results)
        
        # Verify results are sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

