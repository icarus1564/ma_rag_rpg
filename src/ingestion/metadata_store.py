"""Store and retrieve chunk metadata."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    chunk_id: str
    text: str
    start_pos: int
    end_pos: int
    chunk_index: int
    source: str
    additional_metadata: Dict[str, Any] = field(default_factory=dict)


class MetadataStore:
    """Store and retrieve chunk metadata."""
    
    @debug_log_method
    def save_metadata(
        self,
        chunks: List[ChunkMetadata],
        path: str
    ) -> None:
        """Save chunk metadata to disk.

        Args:
            chunks: List of chunk metadata
            path: File path to save to
        """
        logger.info("Saving chunk metadata", path=path, chunk_count=len(chunks))
        
        # Create directory if needed
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert chunks to dict format
        metadata_dict = {chunk.chunk_id: asdict(chunk) for chunk in chunks}
        
        # Save as JSON
        with open(path, "w") as f:
            json.dump(metadata_dict, f, indent=2)
        
        logger.info("Chunk metadata saved successfully", path=path, chunk_count=len(chunks))
    
    @debug_log_method
    def load_metadata(self, path: str) -> Dict[str, ChunkMetadata]:
        """Load chunk metadata from disk.

        Args:
            path: File path to load from

        Returns:
            Dictionary mapping chunk_id to metadata
        """
        logger.info("Loading chunk metadata", path=path)
        
        if not Path(path).exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")
        
        # Load JSON file
        with open(path, "r") as f:
            metadata_dict = json.load(f)
        
        # Convert dict to ChunkMetadata objects
        result = {
            chunk_id: ChunkMetadata(**data)
            for chunk_id, data in metadata_dict.items()
        }
        
        logger.info("Chunk metadata loaded successfully", path=path, chunk_count=len(result))
        return result
    
    def get_chunk_metadata(
        self,
        chunk_id: str,
        metadata_path: str
    ) -> Optional[ChunkMetadata]:
        """Get metadata for a specific chunk.
        
        Args:
            chunk_id: ID of the chunk
            metadata_path: Path to metadata file
            
        Returns:
            ChunkMetadata if found, None otherwise
        """
        logger.debug("Getting chunk metadata", chunk_id=chunk_id)
        
        # Load metadata if not already loaded
        metadata = self.load_metadata(metadata_path)
        return metadata.get(chunk_id)

