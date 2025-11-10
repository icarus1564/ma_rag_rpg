#Logic and control flow for the main game loop (aka a "turn")

1. Turn Starts
2. Verify User Prompt against Corpus
- Retrieve relevant context from Corpus
- call RulesReferee, passing in user prompt and retrieved corpus context
-- RulesReferee determines if match is good enough and returns a judgment ("approved" or "disqualified") with reasoning as a result
3. call ScenePlanner, passing in user prompt, retrieved corpus context, and RulesReferee judgment
-- Determines what to do next:
--- if judgment is approved, determine if Narrator or NPCManager is the correct next Agent. if NPCManager, determines which NPC should respond.
--- if judgment is disqualified, chooses the Narrator with the disqualification message including the reasoning passed in from the referee
---> TURN ENDS, PLAYER LOOSES
--- returns orchestrated next Agent with appropriate context (npc name if NPCManager, disqualification or narration of scene if Narrator)
4. Orchestrator constructs context and calls appropriate Agent (Narrator, NPCManager)
-- if Narrator, pass context and instructions (narrate story or disqualify user) to Narrator
-- if NPCManager
--- if npc name not in persona dictionary call NPC persona extractor and load results into persona dictionary (future: persist personas to db until corpus change)
--- load npc persona from persona dictionary and pass persona, context and instructions (respond as the npc) to NPCManager
5. Appropriate Agent (Narrator or NPCManager) processes request
6. Verify Agent response against corpus
-- call RulesReferree, passing in response from Agent and returns a judgment ("approved" or "disqualified") with reasoning as a result
-- if approved, post response to UI, identifying the responding agent ("Narrator" or npc name)
---> TURN ENDS, GAME CONTINUES to next turn
-- if disqualified, pass Agent response and disqualification message to Narrator, post response to UI
---> TURN ENDS, PLAYER WINS

#REQUIREMENTS:
- ensure proper ordering of Agents and handling of context and agent responses
- update the orchestrator to properly direct the flow of control to the appropriate Agent at stage 4: Narrator (disqualification), Narrator (narration), or NPCManager (npc name)
- phases are logged and phase of process is available through API
- process phase updates are displayed in main game page with each phase on a separate line and the status "Processing: Phase {phase_name}..." displayed in the status until processing is complete. 

