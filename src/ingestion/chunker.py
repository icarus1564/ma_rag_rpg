"""Text chunking with multiple strategies."""

from dataclasses import dataclass, field
from typing import List, Literal, Dict, Any
import re
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk."""
    id: str
    text: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class Chunker:
    """Text chunking with multiple strategies."""

    @debug_log_method
    def chunk(
        self,
        text: str,
        strategy: Literal["sentence", "paragraph", "sliding_window"] = "sliding_window",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Chunk]:
        """Split text into chunks.
        
        Args:
            text: Input text to chunk
            strategy: Chunking strategy to use
            chunk_size: Target chunk size (characters or tokens)
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of Chunk objects
        """
        if strategy == "sentence":
            return self._chunk_by_sentence(text, chunk_size, chunk_overlap)
        elif strategy == "paragraph":
            return self._chunk_by_paragraph(text, chunk_size, chunk_overlap)
        elif strategy == "sliding_window":
            return self._chunk_sliding_window(text, chunk_size, chunk_overlap)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    
    def _chunk_by_sentence(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Chunk]:
        """Split text by sentences."""
        logger.debug("Chunking by sentence", chunk_size=chunk_size, overlap=chunk_overlap)
        
        # Split by sentence boundaries (period, exclamation, question mark followed by space)
        import re
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 0
        start_pos = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed chunk_size, finalize current chunk
            if current_size + sentence_size > chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                end_pos = start_pos + len(chunk_text)
                chunks.append(Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={"strategy": "sentence", "sentence_count": len(current_chunk)}
                ))
                chunk_id += 1
                
                # Apply overlap: keep last sentences for overlap
                overlap_text = ' '.join(current_chunk[-chunk_overlap//50:]) if chunk_overlap > 0 else ""
                start_pos = end_pos - len(overlap_text) if overlap_text else end_pos
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)
            
            current_chunk.append(sentence)
            current_size += sentence_size + 1  # +1 for space
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            end_pos = start_pos + len(chunk_text)
            chunks.append(Chunk(
                id=f"chunk_{chunk_id}",
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                metadata={"strategy": "sentence", "sentence_count": len(current_chunk)}
            ))
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Chunk]:
        """Split text by paragraphs."""
        logger.debug("Chunking by paragraph", chunk_size=chunk_size, overlap=chunk_overlap)
        
        # Split by paragraph boundaries (double newlines)
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return []
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 0
        start_pos = 0
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # If adding this paragraph would exceed chunk_size, finalize current chunk
            if current_size + paragraph_size > chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                end_pos = start_pos + len(chunk_text)
                chunks.append(Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={"strategy": "paragraph", "paragraph_count": len(current_chunk)}
                ))
                chunk_id += 1
                
                # Apply overlap: keep last paragraph for overlap
                overlap_text = current_chunk[-1] if chunk_overlap > 0 and current_chunk else ""
                start_pos = end_pos - len(overlap_text) if overlap_text else end_pos
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)
            
            current_chunk.append(paragraph)
            current_size += paragraph_size + 2  # +2 for \n\n
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            end_pos = start_pos + len(chunk_text)
            chunks.append(Chunk(
                id=f"chunk_{chunk_id}",
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                metadata={"strategy": "paragraph", "paragraph_count": len(current_chunk)}
            ))
        
        return chunks
    
    def _chunk_sliding_window(self, text: str, chunk_size: int, chunk_overlap: int) -> List[Chunk]:
        """Split text using sliding window approach."""
        logger.debug("Chunking with sliding window", chunk_size=chunk_size, overlap=chunk_overlap)
        
        if not text:
            return []
        
        # Ensure overlap is less than chunk_size to prevent infinite loops
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size - 1)
        
        chunks = []
        chunk_id = 0
        start_pos = 0
        text_length = len(text)
        
        while start_pos < text_length:
            end_pos = min(start_pos + chunk_size, text_length)
            
            # Try to preserve word boundaries
            if end_pos < text_length:
                # Look for the last space before end_pos
                last_space = text.rfind(' ', start_pos, end_pos)
                if last_space > start_pos:
                    end_pos = last_space + 1
            
            chunk_text = text[start_pos:end_pos].strip()
            
            if chunk_text:
                chunks.append(Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={"strategy": "sliding_window"}
                ))
                chunk_id += 1
            
            # Move start position forward with overlap
            # Ensure we always advance by at least 1 to prevent infinite loops
            new_start_pos = end_pos - chunk_overlap if chunk_overlap > 0 else end_pos
            
            # If we didn't advance (or went backward), force advancement
            if new_start_pos <= start_pos:
                new_start_pos = start_pos + 1
            
            # If we've reached the end, break
            if new_start_pos >= text_length:
                break
            
            start_pos = new_start_pos
        
        return chunks

