# Test Data Specification

## Overview

This document specifies the test data requirements for the RAG infrastructure, including test corpus, test queries, and ground truth data.

## Test Corpus

### Requirements

**File: `tests/data/test_corpus.txt`**

**Size**: Minimum 1000 words, recommended 2000-5000 words

**Content Requirements:**
1. **Multiple Characters/Entities**: At least 3-5 distinct characters with names
2. **Dialogue Sections**: Multiple dialogue exchanges between characters
3. **Location Descriptions**: At least 2-3 distinct locations
4. **Action Sequences**: Multiple action scenes
5. **Narrative Descriptions**: Scene-setting and narrative text

**Structure:**
- Well-formatted text with paragraphs
- Clear sentence boundaries
- Dialogue markers (quotes, speaker attribution)
- Chapter or section breaks (optional)

### Example Test Corpus Structure

```
Chapter 1: The Beginning

Arthur Dent lay in the mud in front of his house, staring up at the sky. 
The bulldozer loomed over him, its engine rumbling ominously. 

"Arthur," said Ford Prefect, "you really should move. That bulldozer 
isn't going to stop just because you're lying there."

Arthur didn't move. "I'm not moving," he said. "This is my house, 
and I'm not going to let them demolish it."

Ford sighed. "Arthur, the plans have been on display at the planning 
office for months. You had plenty of time to object."

"I didn't see them," Arthur replied stubbornly. "I was too busy 
worrying about the meaning of life."

The bulldozer's engine revved louder, and Arthur could feel the 
ground vibrating beneath him. He closed his eyes and waited.

[Continue with more chapters...]
```

### Test Corpus Generation

**Option 1: Use Real Corpus Excerpt**
- Extract first 2-3 chapters from a public domain book
- Ensure it contains the required elements (characters, dialogue, locations)

**Option 2: Synthetic Generation**
- Use `TestDataGenerator` to create synthetic corpus
- Ensure realistic structure and content

**File: `tests/fixtures/test_data_generator.py`**

```python
class TestDataGenerator:
    """Generate test data for RAG infrastructure."""
    
    def generate_test_corpus(self, num_chapters: int = 5) -> str:
        """Generate synthetic test corpus.
        
        Args:
            num_chapters: Number of chapters to generate
            
        Returns:
            Generated corpus text
        """
        # Generate chapters with:
        # - Character introductions
        # - Dialogue sections
        # - Location descriptions
        # - Action sequences
        pass
```

## Test Queries

### Requirements

**File: `tests/data/test_queries.json`**

**Format:**
```json
{
  "queries": [
    {
      "id": "q1",
      "query": "Arthur Dent lies in front of bulldozer",
      "expected_chunk_ids": ["chunk_123", "chunk_124", "chunk_125"],
      "expected_keywords": ["Arthur", "Dent", "bulldozer", "lies"],
      "min_relevant_results": 3,
      "description": "Test query for character action",
      "category": "action"
    }
  ]
}
```

### Query Categories

1. **Character Actions** (30% of queries)
   - Example: "Arthur Dent lies in front of bulldozer"
   - Focus: Character-specific actions

2. **Dialogue** (25% of queries)
   - Example: "Marvin the robot complains about his existence"
   - Focus: Character dialogue and speech patterns

3. **Locations** (20% of queries)
   - Example: "The Heart of Gold spaceship interior"
   - Focus: Location descriptions

4. **Character Descriptions** (15% of queries)
   - Example: "Ford Prefect's appearance and personality"
   - Focus: Character traits and descriptions

5. **Plot Events** (10% of queries)
   - Example: "The destruction of Earth"
   - Focus: Major plot events

### Query Requirements

**Minimum Queries**: 10 queries

**Query Characteristics:**
- **Length**: 3-10 words per query
- **Specificity**: Mix of specific and general queries
- **Keywords**: Each query should have 2-5 key terms
- **Expected Results**: Each query should have 2-5 expected chunk IDs

### Example Test Queries

```json
{
  "queries": [
    {
      "id": "q1",
      "query": "Arthur Dent lies in front of bulldozer",
      "expected_chunk_ids": ["chunk_123", "chunk_124"],
      "expected_keywords": ["Arthur", "Dent", "bulldozer", "lies"],
      "min_relevant_results": 2,
      "description": "Character action query",
      "category": "action"
    },
    {
      "id": "q2",
      "query": "Marvin the robot complains about existence",
      "expected_chunk_ids": ["chunk_456", "chunk_457", "chunk_458"],
      "expected_keywords": ["Marvin", "robot", "complains", "existence"],
      "min_relevant_results": 3,
      "description": "Character dialogue query",
      "category": "dialogue"
    },
    {
      "id": "q3",
      "query": "Heart of Gold spaceship interior description",
      "expected_chunk_ids": ["chunk_789", "chunk_790"],
      "expected_keywords": ["Heart", "Gold", "spaceship", "interior"],
      "min_relevant_results": 2,
      "description": "Location description query",
      "category": "location"
    },
    {
      "id": "q4",
      "query": "Ford Prefect appearance personality traits",
      "expected_chunk_ids": ["chunk_234", "chunk_235"],
      "expected_keywords": ["Ford", "Prefect", "appearance", "personality"],
      "min_relevant_results": 2,
      "description": "Character description query",
      "category": "character"
    },
    {
      "id": "q5",
      "query": "Earth destruction Vogons",
      "expected_chunk_ids": ["chunk_567", "chunk_568", "chunk_569"],
      "expected_keywords": ["Earth", "destruction", "Vogons"],
      "min_relevant_results": 3,
      "description": "Plot event query",
      "category": "plot"
    }
  ]
}
```

## Ground Truth Generation

### Process

1. **Ingest Test Corpus**
   - Run ingestion pipeline on test corpus
   - Generate chunk IDs and metadata

2. **Manual Annotation** (or semi-automated)
   - For each test query, identify relevant chunks
   - Mark chunk IDs as expected results
   - Verify keywords are present in chunks

3. **Validation**
   - Verify expected chunks contain query keywords
   - Verify chunks are semantically relevant
   - Check for false positives/negatives

### Ground Truth Format

**File: `tests/data/ground_truth.json`**

```json
{
  "corpus": "test_corpus.txt",
  "ingestion_date": "2024-01-01T00:00:00Z",
  "total_chunks": 1234,
  "queries": [
    {
      "query_id": "q1",
      "query": "Arthur Dent lies in front of bulldozer",
      "relevant_chunks": [
        {
          "chunk_id": "chunk_123",
          "relevance_score": 1.0,
          "contains_keywords": ["Arthur", "Dent", "bulldozer", "lies"],
          "semantic_relevance": "high"
        },
        {
          "chunk_id": "chunk_124",
          "relevance_score": 0.9,
          "contains_keywords": ["Arthur", "Dent", "bulldozer"],
          "semantic_relevance": "high"
        }
      ],
      "irrelevant_chunks": [
        {
          "chunk_id": "chunk_999",
          "reason": "Different character"
        }
      ]
    }
  ]
}
```

## Test Data Generator

### Implementation

**File: `tests/fixtures/test_data_generator.py`**

```python
from typing import List, Dict, Any
import json
from dataclasses import dataclass, asdict

@dataclass
class TestQuery:
    """Represents a test query with ground truth."""
    id: str
    query: str
    expected_chunk_ids: List[str]
    expected_keywords: List[str]
    min_relevant_results: int
    description: str
    category: str

class TestDataGenerator:
    """Generate test data for RAG infrastructure."""
    
    def __init__(self):
        """Initialize test data generator."""
        self.characters = [
            "Arthur Dent",
            "Ford Prefect",
            "Marvin",
            "Zaphod Beeblebrox",
            "Trillian"
        ]
        self.locations = [
            "Heart of Gold",
            "Earth",
            "Magrathea",
            "Restaurant at the End of the Universe"
        ]
        self.actions = [
            "lies in front of bulldozer",
            "complains about existence",
            "travels through space",
            "discusses meaning of life"
        ]
    
    def generate_test_corpus(self, num_chapters: int = 5) -> str:
        """Generate synthetic test corpus.
        
        Args:
            num_chapters: Number of chapters to generate
            
        Returns:
            Generated corpus text
        """
        corpus = []
        for i in range(num_chapters):
            chapter = self._generate_chapter(i + 1)
            corpus.append(chapter)
        return "\n\n".join(corpus)
    
    def _generate_chapter(self, chapter_num: int) -> str:
        """Generate a single chapter."""
        # Generate chapter with:
        # - Character introductions
        # - Dialogue sections
        # - Location descriptions
        # - Action sequences
        pass
    
    def generate_test_queries(
        self,
        corpus: str,
        num_queries: int = 10
    ) -> List[TestQuery]:
        """Generate test queries from corpus.
        
        Args:
            corpus: Corpus text to generate queries from
            num_queries: Number of queries to generate
            
        Returns:
            List of test queries
        """
        queries = []
        
        # Generate queries for each category
        action_queries = self._generate_action_queries(corpus, num_queries // 3)
        dialogue_queries = self._generate_dialogue_queries(corpus, num_queries // 4)
        location_queries = self._generate_location_queries(corpus, num_queries // 5)
        character_queries = self._generate_character_queries(corpus, num_queries // 6)
        plot_queries = self._generate_plot_queries(corpus, num_queries // 10)
        
        queries.extend(action_queries)
        queries.extend(dialogue_queries)
        queries.extend(location_queries)
        queries.extend(character_queries)
        queries.extend(plot_queries)
        
        return queries[:num_queries]
    
    def _generate_action_queries(
        self,
        corpus: str,
        num: int
    ) -> List[TestQuery]:
        """Generate action queries."""
        # Extract action phrases from corpus
        # Create queries with character + action
        pass
    
    def _generate_dialogue_queries(
        self,
        corpus: str,
        num: int
    ) -> List[TestQuery]:
        """Generate dialogue queries."""
        # Extract dialogue patterns
        # Create queries with character + dialogue topic
        pass
    
    def _generate_location_queries(
        self,
        corpus: str,
        num: int
    ) -> List[TestQuery]:
        """Generate location queries."""
        # Extract location mentions
        # Create queries with location + description
        pass
    
    def _generate_character_queries(
        self,
        corpus: str,
        num: int
    ) -> List[TestQuery]:
        """Generate character description queries."""
        # Extract character descriptions
        # Create queries with character + trait
        pass
    
    def _generate_plot_queries(
        self,
        corpus: str,
        num: int
    ) -> List[TestQuery]:
        """Generate plot event queries."""
        # Extract plot events
        # Create queries with event + context
        pass
    
    def save_test_queries(
        self,
        queries: List[TestQuery],
        path: str
    ) -> None:
        """Save test queries to JSON file.
        
        Args:
            queries: List of test queries
            path: File path to save to
        """
        queries_dict = {
            "queries": [asdict(q) for q in queries]
        }
        with open(path, "w") as f:
            json.dump(queries_dict, f, indent=2)
```

## Test Execution

### Setup

1. **Generate or Prepare Test Corpus**
   ```bash
   # Option 1: Use existing corpus
   cp data/corpus.txt tests/data/test_corpus.txt
   
   # Option 2: Generate synthetic corpus
   python -m tests.fixtures.test_data_generator --generate-corpus
   ```

2. **Ingest Test Corpus**
   ```bash
   python scripts/ingest.py \
     --corpus tests/data/test_corpus.txt \
     --collection test_corpus_embeddings \
     --overwrite
   ```

3. **Generate Test Queries**
   ```bash
   python -m tests.fixtures.test_data_generator \
     --corpus tests/data/test_corpus.txt \
     --output tests/data/test_queries.json \
     --num-queries 10
   ```

4. **Annotate Ground Truth** (manual or semi-automated)
   - Review test queries
   - Identify relevant chunks
   - Create ground truth file

### Test Execution

**File: `tests/test_integration/test_ingestion_to_search.py`**

```python
import pytest
from pathlib import Path
import json
from src.ingestion.pipeline import IngestionPipeline
from src.core.retrieval_manager import RetrievalManager

@pytest.fixture
def test_corpus_path():
    """Path to test corpus."""
    return Path("tests/data/test_corpus.txt")

@pytest.fixture
def test_queries():
    """Load test queries."""
    with open("tests/data/test_queries.json") as f:
        data = json.load(f)
    return data["queries"]

@pytest.fixture
def ingested_corpus(test_corpus_path, tmp_path):
    """Ingest test corpus."""
    # Initialize pipeline
    pipeline = IngestionPipeline(...)
    
    # Run ingestion
    result = pipeline.ingest(
        corpus_path=str(test_corpus_path),
        collection_name="test_corpus_embeddings",
        overwrite=True
    )
    
    return result

def test_ingestion_creates_indices(ingested_corpus):
    """Test that ingestion creates all required indices."""
    assert ingested_corpus.total_chunks > 0
    assert Path(ingested_corpus.bm25_index_path).exists()
    assert Path(ingested_corpus.metadata_path).exists()

def test_search_returns_results(ingested_corpus, test_queries):
    """Test that search returns relevant results."""
    # Initialize retrieval manager
    retrieval_manager = RetrievalManager(...)
    
    # Test each query
    for query_data in test_queries:
        query = query_data["query"]
        expected_chunk_ids = set(query_data["expected_chunk_ids"])
        min_results = query_data["min_relevant_results"]
        
        # Perform search
        results = retrieval_manager.retrieve(query, top_k=10)
        
        # Verify results
        assert len(results) >= min_results
        
        # Check for expected chunks
        result_chunk_ids = {r.chunk_id for r in results}
        found_expected = result_chunk_ids.intersection(expected_chunk_ids)
        
        assert len(found_expected) > 0, \
            f"Query '{query}' did not return expected chunks"
        
        # Verify keywords are present
        expected_keywords = query_data["expected_keywords"]
        for result in results[:min_results]:
            text_lower = result.chunk_text.lower()
            found_keywords = [
                kw for kw in expected_keywords
                if kw.lower() in text_lower
            ]
            assert len(found_keywords) > 0, \
                f"Result chunk {result.chunk_id} does not contain expected keywords"

def test_hybrid_retrieval_improves_results(ingested_corpus, test_queries):
    """Test that hybrid retrieval improves results over individual retrievers."""
    # Initialize retrievers
    bm25_retriever = BM25Retriever(...)
    vector_retriever = VectorRetriever(...)
    hybrid_retriever = HybridRetriever(...)
    
    # Test with sample query
    query = test_queries[0]["query"]
    expected_chunk_ids = set(test_queries[0]["expected_chunk_ids"])
    
    # Get results from each retriever
    bm25_results = bm25_retriever.retrieve(query, top_k=10)
    vector_results = vector_retriever.retrieve(query, top_k=10)
    hybrid_results = hybrid_retriever.retrieve(query, top_k=10)
    
    # Check recall for each
    bm25_recall = len(set(r.chunk_id for r in bm25_results).intersection(expected_chunk_ids))
    vector_recall = len(set(r.chunk_id for r in vector_results).intersection(expected_chunk_ids))
    hybrid_recall = len(set(r.chunk_id for r in hybrid_results).intersection(expected_chunk_ids))
    
    # Hybrid should have equal or better recall
    assert hybrid_recall >= bm25_recall
    assert hybrid_recall >= vector_recall
```

## Validation

### Query Validation

1. **Keyword Presence**: Verify expected keywords appear in relevant chunks
2. **Semantic Relevance**: Verify chunks are semantically relevant to query
3. **Coverage**: Verify all expected chunks are found
4. **False Positives**: Check for irrelevant chunks in results

### Result Validation

1. **Score Ordering**: Verify results are ordered by relevance score
2. **Score Range**: Verify scores are in expected range (0-1 for normalized)
3. **Metadata**: Verify chunk metadata is correct
4. **Deduplication**: Verify no duplicate chunks in results

## Maintenance

### Updating Test Data

1. **When to Update**:
   - After changing chunking strategy
   - After changing embedding model
   - After adding new test cases
   - After corpus changes

2. **Update Process**:
   - Re-run ingestion on test corpus
   - Update chunk IDs in test queries
   - Re-annotate ground truth if needed
   - Re-run tests to verify

### Version Control

- **Test Corpus**: Version controlled in `tests/data/test_corpus.txt`
- **Test Queries**: Version controlled in `tests/data/test_queries.json`
- **Ground Truth**: Version controlled in `tests/data/ground_truth.json`
- **Generator**: Version controlled in `tests/fixtures/test_data_generator.py`

---

## Summary

This specification provides:

1. **Test Corpus**: Requirements and structure for test corpus
2. **Test Queries**: Format and categories for test queries
3. **Ground Truth**: Format and generation process
4. **Test Data Generator**: Implementation for generating test data
5. **Test Execution**: How to run tests with test data
6. **Validation**: How to validate test results
7. **Maintenance**: How to update and maintain test data

All test data should be designed to:
- Test all retrieval components (BM25, vector, hybrid)
- Test query rewriting
- Test various query types (action, dialogue, location, etc.)
- Provide measurable success criteria
- Be maintainable and extensible

