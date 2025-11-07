"""Citation utilities for mapping and formatting citations."""

from typing import List, Dict, Any
from ..core.base_agent import RetrievalResult


class CitationMapper:
    """Map citation markers to chunk IDs."""

    @staticmethod
    def map_citations(
        citation_markers: List[str],
        retrieval_results: List[RetrievalResult]
    ) -> List[str]:
        """Map citation numbers to chunk IDs.

        Args:
            citation_markers: List of citation numbers ["1", "2", "5"]
            retrieval_results: Retrieved chunks in order

        Returns:
            List of chunk IDs
        """
        chunk_ids = []
        for marker in citation_markers:
            try:
                idx = int(marker) - 1  # Citations are 1-indexed
                if 0 <= idx < len(retrieval_results):
                    chunk_ids.append(retrieval_results[idx].chunk_id)
            except (ValueError, IndexError):
                pass
        return chunk_ids

    @staticmethod
    def format_chunks_for_prompt(
        results: List[RetrievalResult],
        include_scores: bool = False
    ) -> str:
        """Format retrieval results for prompt.

        Returns formatted string like:
        [1] (Score: 0.85) Text of chunk 1...
        [2] (Score: 0.72) Text of chunk 2...

        Args:
            results: List of retrieval results
            include_scores: Whether to include scores in output

        Returns:
            Formatted string for prompt
        """
        if not results:
            return "[No relevant passages found]"

        formatted = []
        for i, result in enumerate(results, 1):
            if include_scores:
                formatted.append(f"[{i}] (Score: {result.score:.2f}) {result.chunk_text}")
            else:
                formatted.append(f"[{i}] {result.chunk_text}")

        return "\n\n".join(formatted)

    @staticmethod
    def extract_chunk_ids(retrieval_results: List[RetrievalResult]) -> List[str]:
        """Extract chunk IDs from retrieval results.

        Args:
            retrieval_results: List of retrieval results

        Returns:
            List of chunk IDs
        """
        return [result.chunk_id for result in retrieval_results]
