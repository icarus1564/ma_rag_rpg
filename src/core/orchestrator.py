"""Game orchestrator coordinates agent execution."""

from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent, AgentContext, AgentOutput, RetrievalResult
from .session import GameSession
from ..utils.logging import get_logger
from ..utils.debug_logging import debug_log_method

logger = get_logger(__name__)


class GameOrchestrator:
    """Orchestrates agent execution in the game loop."""
    
    def __init__(self, agents: Dict[str, BaseAgent]):
        """
        Initialize orchestrator with agents.
        
        Args:
            agents: Dictionary mapping agent names to agent instances
        """
        self.agents = agents
        self.logger = get_logger(__name__)
    
    @debug_log_method
    def execute_turn(
        self,
        session: GameSession,
        player_command: str,
        retrieval_results: List[RetrievalResult],
        initial_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single game turn with all agents.

        Args:
            session: Current game session
            player_command: Player's command/action
            retrieval_results: Retrieved chunks from RAG system
            initial_context: Optional initial context for first turn

        Returns:
            Dictionary with outputs from all agents
        """
        turn_number = len(session.turns) + 1
        self.logger.info("Executing turn", session_id=session.session_id, turn_number=turn_number)
        
        # Build agent context
        context = AgentContext(
            player_command=player_command,
            session_state=session.state,
            retrieval_results=retrieval_results,
            previous_turns=session.state.get("memory", []),
        )
        
        # If initial context provided (first turn), set it
        if initial_context and turn_number == 1:
            context.session_state["initial_context"] = initial_context
        
        outputs = {}
        
        # Execute agents in sequence
        # Prefer standard order, but execute all provided agents
        agent_order = ["narrator", "scene_planner", "npc_manager", "rules_referee"]
        # Add any other agents not in standard order
        all_agents = set(agent_order) | set(self.agents.keys())
        # Execute in order: standard order first, then others
        agents_to_execute = [a for a in agent_order if a in self.agents]
        agents_to_execute.extend([a for a in sorted(all_agents - set(agent_order)) if a in self.agents])
        
        for agent_name in agents_to_execute:
            if agent_name not in self.agents:
                continue
            
            agent = self.agents[agent_name]
            
            if not agent.config.enabled:
                self.logger.debug(f"Agent {agent_name} is disabled, skipping")
                continue
            
            try:
                self.logger.debug(f"Executing agent: {agent_name}")
                agent_output = agent.process(context)
                
                # Update context with this agent's output for next agents
                context.session_state[f"{agent_name}_output"] = agent_output.content
                
                outputs[agent_name] = {
                    "content": agent_output.content,
                    "citations": agent_output.citations,
                    "reasoning": agent_output.reasoning,
                    "metadata": agent_output.metadata,
                }
                
                self.logger.debug(f"Agent {agent_name} completed successfully")
                
            except Exception as e:
                self.logger.error(
                    f"Agent {agent_name} failed",
                    error=str(e),
                    exc_info=True,
                )
                outputs[agent_name] = {
                    "content": f"Error: {str(e)}",
                    "citations": [],
                    "error": True,
                }
        
        # Update session state based on agent outputs
        self._update_session_state(session, outputs, context)
        
        return {
            "turn_number": turn_number,
            "outputs": outputs,
        }
    
    @debug_log_method
    def _update_session_state(
        self,
        session: GameSession,
        outputs: Dict[str, Any],
        context: AgentContext,
    ) -> None:
        """Update session state based on agent outputs."""
        # Update current scene from narrator or scene_planner
        if "scene_planner" in outputs:
            scene_plan = outputs["scene_planner"].get("metadata", {}).get("scene_plan")
            if scene_plan:
                session.state["current_scene"] = scene_plan.get("next_scene")
                if "responding_npc" in scene_plan:
                    npc = scene_plan["responding_npc"]
                    if npc and npc not in session.state["active_npcs"]:
                        session.state["active_npcs"].append(npc)
        
        elif "narrator" in outputs:
            # Narrator might set scene directly
            narrator_metadata = outputs["narrator"].get("metadata", {})
            if "scene" in narrator_metadata:
                session.state["current_scene"] = narrator_metadata["scene"]
        
        # Store rules validation result
        if "rules_referee" in outputs:
            session.state["last_validation"] = outputs["rules_referee"].get("metadata", {}).get("validation_result")

