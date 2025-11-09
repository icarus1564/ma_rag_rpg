"""Thread-safe session manager for concurrent sessions."""

import threading
import uuid
from typing import Dict, Optional
from datetime import datetime
from .session import GameSession
from .config import SessionConfig
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)


class SessionManager:
    """Manages game sessions with thread-safe operations."""
    
    def __init__(self, session_config: SessionConfig):
        """
        Initialize session manager.
        
        Args:
            session_config: Configuration for session management
        """
        self.config = session_config
        self._sessions: Dict[str, GameSession] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    @debug_log_method
    def create_session(self, initial_context: Optional[str] = None) -> GameSession:
        """
        Create a new game session.

        Args:
            initial_context: Optional initial context for the game

        Returns:
            New GameSession instance
        """
        session_id = str(uuid.uuid4())
        session = GameSession(
            session_id=session_id,
            config=self.config,
        )
        
        if initial_context:
            session.state["initial_context"] = initial_context
        
        with self._lock:
            self._sessions[session_id] = session
        
        self.logger.info("Session created", session_id=session_id)
        return session
    
    @debug_log_method
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            GameSession if found, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_expired():
                del self._sessions[session_id]
                self.logger.info("Session expired and removed", session_id=session_id)
                return None
            return session
    
    @debug_log_method
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self.logger.info("Session deleted", session_id=session_id)
                return True
            return False
    
    @debug_log_method
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            Number of sessions removed
        """
        with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired_ids:
                del self._sessions[sid]
        
        if expired_ids:
            self.logger.info("Cleaned up expired sessions", count=len(expired_ids))
        
        return len(expired_ids)
    
    def list_sessions(self) -> list:
        """
        List all active session IDs.
        
        Returns:
            List of session IDs
        """
        with self._lock:
            return list(self._sessions.keys())
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        with self._lock:
            return len(self._sessions)

