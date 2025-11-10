"""Game session management with sliding window memory."""

import time
import tiktoken
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from .config import SessionConfig
from ..utils.debug_logging import debug_log_method


@dataclass
class Turn:
    """Represents a single game turn."""
    turn_number: int
    player_command: str
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: int = 0


@dataclass
class GameSession:
    """Manages state for a single game session."""
    session_id: str
    config: SessionConfig
    turns: List[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    state: Dict[str, Any] = field(default_factory=dict)

    # NEW: Persona cache for NPCs
    persona_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # NEW: Track turn outcomes
    wins: int = 0  # Player wins (agent disqualified)
    losses: int = 0  # Player losses (user disqualified)

    def __post_init__(self):
        """Initialize session state."""
        if "current_scene" not in self.state:
            self.state["current_scene"] = None
        if "active_npcs" not in self.state:
            self.state["active_npcs"] = []
        if "memory" not in self.state:
            self.state["memory"] = []
    
    @debug_log_method
    def add_turn(self, turn: Turn) -> None:
        """Add a turn to the session."""
        self.turns.append(turn)
        self.last_accessed = datetime.now()
        self._apply_sliding_window()
    
    @debug_log_method
    def _apply_sliding_window(self) -> None:
        """Apply sliding window memory based on config."""
        if not self.config.sliding_window:
            return
        
        # Count tokens in current memory
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        total_tokens = 0
        memory_turns = []
        
        # Build memory from recent turns (most recent first)
        for turn in reversed(self.turns):
            turn_text = self._turn_to_text(turn)
            turn_tokens = len(encoding.encode(turn_text))
            
            if total_tokens + turn_tokens > self.config.max_tokens:
                break
            
            memory_turns.insert(0, turn)
            total_tokens += turn_tokens
        
        # Also limit by window size
        if len(memory_turns) > self.config.memory_window_size:
            memory_turns = memory_turns[-self.config.memory_window_size:]
        
        # Update memory state
        self.state["memory"] = [
            {
                "turn_number": turn.turn_number,
                "player_command": turn.player_command,
                "outputs": turn.agent_outputs,
            }
            for turn in memory_turns
        ]
    
    def _turn_to_text(self, turn: Turn) -> str:
        """Convert turn to text representation for token counting."""
        parts = [f"Turn {turn.turn_number}: {turn.player_command}"]
        for agent_name, output in turn.agent_outputs.items():
            if isinstance(output, dict) and "content" in output:
                parts.append(f"{agent_name}: {output['content']}")
            else:
                parts.append(f"{agent_name}: {str(output)}")
        return "\n".join(parts)
    
    @debug_log_method
    def get_memory_context(self) -> str:
        """Get formatted memory context for agents."""
        if not self.state.get("memory"):
            return ""
        
        lines = ["Previous conversation:"]
        for memory_item in self.state["memory"]:
            lines.append(f"Turn {memory_item['turn_number']}: {memory_item['player_command']}")
            for agent_name, output in memory_item.get("outputs", {}).items():
                if isinstance(output, dict) and "content" in output:
                    lines.append(f"  {agent_name}: {output['content']}")
        
        return "\n".join(lines)
    
    @debug_log_method
    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary for observability."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "turn_count": len(self.turns),
            "current_scene": self.state.get("current_scene"),
            "active_npcs": self.state.get("active_npcs", []),
            "memory_size": len(self.state.get("memory", [])),
            "state": self.state,
            "persona_cache_size": len(self.persona_cache),
            "persona_cache_npcs": list(self.persona_cache.keys()),
            "wins": self.wins,
            "losses": self.losses,
        }
    
    @debug_log_method
    def is_expired(self) -> bool:
        """Check if session has expired based on TTL."""
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        return elapsed > self.config.session_ttl_seconds

