#Logic and control flow for the main game loop (aka a "turn")

1. Turn Starts
2. Verify User Prompt against Corpus
- Retrieve relevant context from Corpus
- call RulesReferee, passing in user prompt and retrieved corpus context
-- RulesReferee determines if match is good enough and returns a judgment ("approved" or "disqualified") with reasoning as a result
3. call ScenePlanner, passing in user prompt, retrieved corpus context, and RulesReferee judgment
-- Determines what to do next:
--- if judgment is approved, determine if Narrator or NPCManager is the correct next Agent. if NPCManager, determines which NPC should respond.
---> GAME LOOP CONTINUES: returns orchestrated next Agent with appropriate context / metadata (npc name if NPCManager, narration of scene if Narrator)
--- if judgment is disqualified, sets next_action to "disqualify" with alternative_suggestions
---> returns player_disqualified with reason message from RulesReferee

4. Handle disqualification or continue to appropriate Agent
-- if Player disqualified (ScenePlanner returned "disqualify")
---> GAME LOOP ENDS, PLAYER LOSES. Use RulesReferee's rejection message directly as disqualification message
---> Update metadata with disqualification_reason and alternative_suggestions from RulesReferee/ScenePlanner
---> Return TurnResult with player_loses=True, displaying RulesReferee's message to UI
-- else if Narrator, GAME LOOP CONTINUES: pass context and instructions (narrate story) to Narrator
-- else if NPCManager
--- if npc name not in persona dictionary call NPC persona extractor and load results into persona dictionary (future: persist personas to db until corpus change)
--- load npc persona from persona dictionary and pass persona, context and instructions (respond as the npc) to NPCManager
5. Appropriate Agent (Narrator or NPCManager) processes request
6. Verify Agent response against corpus
-- call RulesReferee, passing in response from Agent and returns a judgment ("approved" or "disqualified") with reasoning as a result
-- if approved, post Agent response to UI, identifying the responding agent ("Narrator" or npc name)
---> TURN ENDS, GAME CONTINUES to next turn
-- if disqualified
---> GAME ENDS, PLAYER WINS. Update metadata to indicate agent_disqualified, player wins, with reason message from RulesReferee to display in UI

#REQUIREMENTS:
- ensure proper ordering of Agents and handling of context and agent responses
- update the orchestrator to properly direct the flow of control to the appropriate Agent at stage 4: Narrator (narration), or NPCManager (npc name). Note: Narrator is NOT called for disqualification messages.
- phases are logged and phase of process is available through API
- process phase updates are displayed in main game page with each phase on a separate line and the status "Processing: Phase {phase_name}..." displayed in the status until processing is complete.

#IMPLEMENTATION NOTES:
- User prompt disqualification uses RulesReferee message directly, no Narrator call needed
- Agent response disqualification also uses RulesReferee message directly, no Narrator call needed
- This simplifies the flow and ensures the disqualification reason is consistent with the validation result
- The metadata includes disqualification_reason and original_agent_response (for agent disqualification) or alternative_suggestions (for user disqualification) for the UI to display
- Both disqualification types now have metadata indicating source="rules_referee" and disqualification_type="user_prompt" or "agent_response" 

