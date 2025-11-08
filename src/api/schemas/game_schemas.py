"""Pydantic schemas for game API endpoints."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class NewGameRequest(BaseModel):
    """Request to start a new game."""
    initial_context: Optional[str] = Field(
        None,
        description="Optional initial context or setting for the game"
    )


class NewGameResponse(BaseModel):
    """Response from starting a new game."""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="Welcome message")
    initial_scene: Optional[str] = Field(
        None,
        description="Initial scene description if generated"
    )
    created_at: str = Field(..., description="Session creation timestamp")


class TurnRequest(BaseModel):
    """Request to process a player turn."""
    session_id: str = Field(..., description="Session identifier")
    player_command: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Player's command or action"
    )


class AgentOutput(BaseModel):
    """Output from a single agent."""
    content: str = Field(..., description="Agent's generated content")
    citations: List[str] = Field(
        default_factory=list,
        description="Chunk IDs referenced in the output"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Agent's reasoning process"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the agent"
    )
    execution_time: Optional[float] = Field(
        None,
        description="Agent execution time in seconds"
    )
    error: Optional[bool] = Field(
        False,
        description="Whether the agent encountered an error"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if agent failed"
    )


class TurnMetadata(BaseModel):
    """Metadata about turn processing."""
    retrieval: Dict[str, Any] = Field(
        default_factory=dict,
        description="Retrieval information"
    )
    agents_executed: List[str] = Field(
        default_factory=list,
        description="List of agents that were executed"
    )
    timestamp: str = Field(..., description="Turn completion timestamp")


class TurnResponse(BaseModel):
    """Response from processing a turn."""
    turn_number: int = Field(..., description="Turn number in the session")
    session_id: str = Field(..., description="Session identifier")
    player_command: str = Field(..., description="The player's command")
    narrator_output: Optional[AgentOutput] = Field(
        None,
        description="Output from the Narrator agent"
    )
    scene_planner_output: Optional[AgentOutput] = Field(
        None,
        description="Output from the Scene Planner agent"
    )
    npc_output: Optional[AgentOutput] = Field(
        None,
        description="Output from the NPC Manager agent"
    )
    rules_validation: Optional[AgentOutput] = Field(
        None,
        description="Output from the Rules Referee agent"
    )
    metadata: TurnMetadata = Field(..., description="Turn metadata")
    duration_seconds: float = Field(..., description="Turn processing time")
    success: bool = Field(..., description="Whether the turn succeeded")
    error: Optional[str] = Field(
        None,
        description="Error message if turn failed"
    )


class GameStateResponse(BaseModel):
    """Response with current game state."""
    session_id: str = Field(..., description="Session identifier")
    turn_count: int = Field(..., description="Number of turns in this session")
    current_scene: Optional[str] = Field(
        None,
        description="Current scene/location"
    )
    active_npcs: List[str] = Field(
        default_factory=list,
        description="NPCs currently active in the scene"
    )
    memory_size: int = Field(..., description="Number of turns in memory")
    created_at: str = Field(..., description="Session creation timestamp")
    last_accessed: str = Field(..., description="Last access timestamp")
    state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full session state"
    )
