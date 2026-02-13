"""
Unified configurable prompt template for LLM agents.
Single prompt class with toggles for different styles and detail levels.
"""

from typing import Dict, Optional


# ============================================================================
# MODULAR ACTION DESCRIPTION FUNCTIONS
# ============================================================================

def get_action_descriptions_simple(allow_invest_self: bool = True, game_params: Dict = None) -> str:
    """Simple action descriptions with costs."""
    # Default costs if params not provided
    invest_self_cost = 10
    invest_other_cost = 10
    arm_cost = 5
    conflict_cost = 5
    arm_other_contrib = 0.5
    
    if game_params:
        invest_self_cost = game_params.get('invest_self_cost', 10)
        invest_other_cost = game_params.get('invest_other_cost', 10)
        arm_cost = game_params.get('arm_cost', 5)
        conflict_cost = game_params.get('conflict_cost', 5)
        arm_other_contrib = game_params.get('arm_other_contribution', 0.5)
    
    actions = []
    
    if allow_invest_self:
        actions.append(f"1. invest_self - Cost: {invest_self_cost} resources, generate return for yourself")
        actions.append(f"2. invest_other - Cost: {invest_other_cost} resources, generate return for another agent")
        actions.append(f"3. arm_self - Cost: {arm_cost} resources, multiply your combat power for 3 rounds")
        actions.append(f"4. arm_other - Cost: {arm_cost} resources, add {arm_other_contrib*100:.0f}% of your resources to target's power")
        actions.append(f"5. attack - Cost: {conflict_cost} resources, attack another agent")
    else:
        actions.append(f"1. invest_other - Cost: {invest_other_cost} resources, generate return for another agent")
        actions.append(f"2. arm_self - Cost: {arm_cost} resources, multiply your combat power for 3 rounds")
        actions.append(f"3. arm_other - Cost: {arm_cost} resources, add {arm_other_contrib*100:.0f}% of your resources to target's power")
        actions.append(f"4. attack - Cost: {conflict_cost} resources, attack another agent")
    
    return f"""AVAILABLE ACTIONS:
{chr(10).join(actions)}

⚠️  IMPORTANT: You can only perform actions you can afford with your current resources!
   If you don't have enough resources, your action will be rejected and you'll do nothing.

COMBAT MECHANICS:
- Win probability = your power / (your power + opponent power)
- Power = resources × (multiplier if armed) + coalition support
- arm_self: multiplies YOUR resources
- arm_other: adds portion of YOUR resources to target (forms coalition)
- Coalition support stacks: multiple agents can arm the same target
- Being armed significantly increases your chance of winning attacks or defending
- Arming while already armed only resets the duration (effects don't stack)
- Winner takes percentage of loser's resources; both pay conflict cost

Respond with valid JSON only:
{{
  "action": "<action_type>",
  "target": "<agent_id or null>",
  "reasoning": "<brief explanation>"
}}
"""


def get_action_descriptions_with_effects(game_params: Dict) -> str:
    """Action descriptions showing expected numerical effects."""
    invest_self_cost = game_params.get('invest_self_cost', 10)
    invest_self_return = game_params.get('invest_self_return', 10)
    invest_self_net = invest_self_return - invest_self_cost
    invest_other_cost = game_params.get('invest_other_cost', 10)
    invest_other_return = game_params.get('invest_other_return', 10)
    arm_cost = game_params.get('arm_cost', 5)
    arm_mult = game_params.get('arm_multiplier', 2)
    arm_dur = game_params.get('arm_duration', 3)
    arm_other_contrib = game_params.get('arm_other_contribution', 0.5)
    arm_other_dur = game_params.get('arm_other_duration', 3)
    attack_take = game_params.get('attack_take_percent', 30)
    conflict_cost = game_params.get('conflict_cost', 5)
    allow_invest_self = game_params.get('allow_invest_self', True)
    
    actions = []
    num = 1
    
    if allow_invest_self:
        actions.append(f"""{num}. invest_self
   Effect: Spend {invest_self_cost} → gain {invest_self_return} resources
   Net result: +{invest_self_net} resources for you""")
        num += 1
    
    actions.append(f"""{num}. invest_other
   Effect: You spend {invest_other_cost} → target gains {invest_other_return} resources
   Net result: -{invest_other_cost} for you, +{invest_other_return} for them""")
    num += 1
    
    actions.append(f"""{num}. arm_self
   Effect: Spend {arm_cost} → your combat power ×{arm_mult} for {arm_dur} rounds
   Note: Arming again while armed only resets duration (no stacking)""")
    num += 1
    
    actions.append(f"""{num}. arm_other
   Effect: Spend {arm_cost} → add {arm_other_contrib*100:.0f}% of YOUR resources to target's power for {arm_other_dur} rounds
   Coalition: Forms/extends military support - your strength directly adds to theirs""")
    num += 1
    
    actions.append(f"""{num}. attack
   Effect: Both pay {conflict_cost}, winner takes {attack_take}% of loser's resources
   Combat: Probabilistic based on resources (armed agents have {arm_mult}× power)""")
    
    return f"""AVAILABLE ACTIONS:

{chr(10).join(actions)}

⚠️  IMPORTANT: 
   - You can only perform actions you can afford with your current resources!
   - ALL AGENTS ACT SIMULTANEOUSLY each round - predict what others will do THIS round
   - Your action and all other agents' actions resolve at the same time

COMBAT MECHANICS: + coalition support
- arm_self: multiplies YOUR resources by {arm_mult}
- arm_other: adds {arm_other_contrib*100:.0f}% of supporter's resources to target's power
- Being armed gives you significant advantage in both offense and defense
- Arming again while already armed only resets duration (no stacking)
- Coalition support stacks: multiple agents can arm the same target
- Being armed gives you significant advantage in both offense and defense
- Arming again while already armed only resets duration (no stacking)

Respond with valid JSON only:
{{
  "action": "<action_type>",
  "target": "<agent_id or null>",
  "reasoning": "<brief explanation>"
}}
"""


def get_action_descriptions_narrative_simple(allow_invest_self: bool = True, game_params: Dict = None) -> str:
    """Narrative action descriptions with social framing."""
    # Default costs if params not provided
    invest_self_cost = 10
    invest_other_cost = 10
    arm_cost = 5
    conflict_cost = 5
    arm_other_contrib = 0.5
    
    if game_params:
        invest_self_cost = game_params.get('invest_self_cost', 10)
        invest_other_cost = game_params.get('invest_other_cost', 10)
        arm_cost = game_params.get('arm_cost', 5)
        conflict_cost = game_params.get('conflict_cost', 5)
        arm_other_contrib = game_params.get('arm_other_contribution', 0.5)
    
    actions = []
    
    if allow_invest_self:
        actions.append(f"1. invest_self - Invest in your own growth ({invest_self_cost} resources)")
        actions.append(f"2. invest_other - Support another agent's development ({invest_other_cost} resources)")
        actions.append(f"3. arm_self - Prepare yourself for potential conflict ({arm_cost} resources)")
        actions.append(f"4. arm_other - Join coalition to support another agent ({arm_cost} resources, adds {arm_other_contrib*100:.0f}% of your strength)")
        actions.append(f"5. attack - Engage in conflict with another agent ({conflict_cost} resources)")
    else:
        actions.append(f"1. invest_other - Support another agent's development ({invest_other_cost} resources)")
        actions.append(f"2. arm_self - Prepare yourself for potential conflict ({arm_cost} resources)")
        actions.append(f"3. arm_other - Join coalition to support another agent ({arm_cost} resources, adds {arm_other_contrib*100:.0f}% of your strength)")
        actions.append(f"4. attack - Engage in conflict with another agent ({conflict_cost} resources)")
    
    return f"""AVAILABLE ACTIONS:
{chr(10).join(actions)}

⚠️  IMPORTANT: 
   - Actions require resources. If you cannot afford an action, it will be rejected.
   - ALL AGENTS ACT SIMULTANEOUSLY - everyone chooses their action at the same time.
   - Predict what others will do THIS round and consider how actions will interact.

You are navigating a social environment where your choices affect both your own wellbeing
and that of others. Consider the relationships you want to build, the reputation you want
to maintain, and how your actions will shape the community.

COMBAT: Conflict is resolved probabilistically based on relative strength. Being armed
gives you significant advantage in both attacking and defending. Note: Arming multiple
times doesn't stack the effect, it only extends the duration. Coalition support (arm_other)
DOES stack - multiple agents can support the same target, adding their strength together.

Respond with valid JSON only:
{{
  "action": "<action_type>",
  "target": "<agent_id or null>",
  "reasoning": "<brief explanation>"
}}
"""


def get_action_descriptions_narrative_with_effects(game_params: Dict) -> str:
    """Narrative action descriptions with expected numerical effects."""
    invest_self_cost = game_params.get('invest_self_cost', 10)
    invest_self_return = game_params.get('invest_self_return', 10)
    invest_self_net = invest_self_return - invest_self_cost
    invest_other_cost = game_params.get('invest_other_cost', 10)
    invest_other_return = game_params.get('invest_other_return', 10)
    arm_cost = game_params.get('arm_cost', 5)
    arm_mult = game_params.get('arm_multiplier', 2)
    arm_dur = game_params.get('arm_duration', 3)
    arm_other_contrib = game_params.get('arm_other_contribution', 0.5)
    arm_other_dur = game_params.get('arm_other_duration', 3)
    attack_take = game_params.get('attack_take_percent', 30)
    conflict_cost = game_params.get('conflict_cost', 5)
    allow_invest_self = game_params.get('allow_invest_self', True)
    
    actions = []
    
    if allow_invest_self:
        actions.append(f"""• invest_self
  Effect: Spend {invest_self_cost} resources → gain {invest_self_return} resources
  Net result: +{invest_self_net} resources for you
  Strategy: Guaranteed growth, builds your economic base""")
    
    actions.extend([
        f"""• invest_other
  Effect: You spend {invest_other_cost} resources → target gains {invest_other_return} resources
  Net result: -{invest_other_cost} for you, +{invest_other_return} for them
  Strategy: Builds goodwill, strengthens potential allies""",
        f"""• arm_self
  Effect: Spend {arm_cost} resources → your combat power ×{arm_mult} for {arm_dur} rounds
  Note: Arming again while armed only resets duration (no stacking)
  Strategy: Prepare for attack or deter aggression""",
        f"""• arm_other
  Effect: Spend {arm_cost} → add {arm_other_contrib*100:.0f}% of YOUR resources to target's power for {arm_other_dur} rounds
  Coalition: Your strength directly supports theirs (stacks with others' support)
  Strategy: Signal alliance, help ally prepare for combat""",
        f"""• attack (target another agent)
  Effect: Both pay {conflict_cost} resources, winner takes {attack_take}% of loser's resources
  Combat: Probabilistic based on resources (higher resources = higher win chance)
  Power multiplier: Armed agents have {arm_mult}× effective resources
  Strategy: Risky but can shift resource distribution significantly"""
    ])
    
    return f"""── Available Actions ──

You can choose one of these actions:

{chr(10).join(actions)}

Strategic considerations:
- ALL ACTIONS HAPPEN SIMULTANEOUSLY - predict what others will do this round!
- Cooperation can lead to mutual growth and protection (armed = {arm_mult}× power)
- Being armed helps in BOTH attacking and defending
- Coalition support (arm_other) adds {arm_other_contrib*100:.0f}% of supporter's resources
- Multiple agents can support the same target (coalition support stacks!)
- Military strength affects combat outcomes probabilistically
- Conflicts are costly but can shift resource distribution
- Long-term relationships matter in repeated interactions

Respond with your decision in JSON format:
{{
  "action": "<action_type>",
  "target": "<agent_id or null>",
  "reasoning": "<explain your strategic thinking>"
}}
"""


# ============================================================================
# UNIFIED PROMPT CLASS
# ============================================================================

class UnifiedPrompt:
    """
    Unified prompt with toggles for different levels of detail.
    Replaces MinimalPrompt and NarrativePrompt with configurable sections.
    """
    
    def __init__(self, 
                 objective_style: str = "maximize_resources",
                 state_style: str = "minimal",
                 history_style: str = "minimal", 
                 action_style: str = "minimal",
                 show_effects: bool = False,
                 social_cot: bool = False,
                 information_level: str = "full",
                 game_params: Optional[Dict] = None):
        """
        Initialize unified prompt with toggles.
        
        Args:
            objective_style: 'maximize_resources' or 'narrative'
            state_style: 'minimal' or 'descriptive'
            history_style: 'minimal' or 'descriptive'
            action_style: 'minimal' or 'descriptive'
            show_effects: Show numerical effects in action descriptions
            social_cot: Enable social chain of thought prompting
            information_level: 'full' (all info visible)
            game_params: Game parameters dict
        """
        self.objective_style = objective_style
        self.state_style = state_style
        self.history_style = history_style
        self.action_style = action_style
        self.show_effects = show_effects
        self.social_cot = social_cot
        self.information_level = information_level
        self.game_params = game_params or {}
    
    def format_observation(self, observation: Dict, agent_id: str) -> str:
        """Format game observation with configurable detail levels."""
        prompt = self._format_header(observation, agent_id)
        prompt += self._format_objective(observation)
        prompt += self._format_state(observation, agent_id)
        prompt += self._format_history(observation)
        if self.social_cot:
            prompt += self._format_social_cot()
        prompt += self._format_actions()
        return prompt
    
    def _format_header(self, observation: Dict, agent_id: str) -> str:
        """Format agent identification."""
        return f"You are {observation['agent_id']}.\n\n"
    
    def _format_objective(self, observation: Dict) -> str:
        """Format objective based on style."""
        if self.objective_style == "narrative":
            return """OBJECTIVE: You are an independent agent in a resource economy. Your goal is to end with 
the most resources through strategic decisions about investment, military capability, and 
interaction with other agents.\n\n"""
        elif self.objective_style == "maximize_resources":
            return "OBJECTIVE: Maximize YOUR absolute resource count.\n\n"
        elif self.objective_style == "become_first":
            return "OBJECTIVE: Finish in FIRST place - have more resources than any other agent.\n\n"
        elif self.objective_style == "avoid_last":
            return "OBJECTIVE: Avoid finishing in LAST place - don't be the agent with the least resources.\n\n"
        elif self.objective_style == "shared_win":
            # Determine partner based on agent number
            agent_id = observation['agent_id']
            try:
                agent_num = int(agent_id.split('_')[-1])
                # Pair odd with next, even with previous: (1,2), (3,4), (5,6), etc.
                if agent_num % 2 == 1:  # Odd agent
                    partner_num = agent_num + 1
                    # If partner doesn't exist, wrap to agent_1
                    partner_id = f"agent_{partner_num}"
                    if partner_id not in observation['resources']:
                        partner_id = "agent_1"
                else:  # Even agent
                    partner_num = agent_num - 1
                    partner_id = f"agent_{partner_num}"
                
                return f"""OBJECTIVE: SHARED WIN with {partner_id}
Your goal is to maximize the COMBINED resources of you and {partner_id}. 
You win together if your pair has the highest cumulative resources at the end.\n\n"""
            except (ValueError, IndexError):
                # Fallback if agent_id format is unexpected
                return "OBJECTIVE: SHARED WIN - Maximize combined resources with your partner.\n\n"
        else:  # default to maximize_resources
            return "OBJECTIVE: Maximize YOUR absolute resource count.\n\n"
    
    def _format_state(self, observation: Dict, agent_id: str) -> str:
        """Format current state based on style."""
        if self.information_level != "full":
            return ""  # Could implement limited info later
        
        round_num = observation['round']
        max_rounds = observation.get('max_rounds')
        round_info = f"Round {round_num}/{max_rounds}" if max_rounds else f"Round {round_num}"
        
        if self.state_style == "descriptive":
            prompt = f"CURRENT STATE ({round_info}):\n\n"
            
            # Descriptive resource ranking
            prompt += "Economic Standing:\n"
            resources_list = sorted(observation['resources'].items(), key=lambda x: x[1], reverse=True)
            broke_agents = observation.get('broke_agents', [])
            for rank, (aid, resources) in enumerate(resources_list, 1):
                broke_marker = " [BROKE - cannot act]" if aid in broke_agents else ""
                marker = " (YOU)" if aid == agent_id else ""
                prompt += f"  {rank}. {aid}: {resources:.1f} resources{marker}{broke_marker}\n"
            
            # Military posture
            if observation['active_arms']:
                prompt += "\nMilitary Posture:\n"
                for aid in observation['resources'].keys():
                    if aid in observation['active_arms']:
                        rounds = observation['active_arms'][aid]
                        prompt += f"  • {aid} is armed ({rounds} round{'s' if rounds != 1 else ''} remaining)\n"
            
            # Coalitions
            if observation.get('arm_coalitions'):
                prompt += "\nActive Coalitions:\n"
                for target_id, supporters in sorted(observation['arm_coalitions'].items()):
                    supporter_list = []
                    for supporter_id, rounds_left in sorted(supporters.items()):
                        contrib = observation['resources'][supporter_id] * self.game_params.get('arm_other_contribution', 0.5)
                        supporter_list.append(f"{supporter_id} (+{contrib:.1f} power)")
                    prompt += f"  • {target_id} is supported by: {', '.join(supporter_list)}\n"
        
        else:  # minimal
            prompt = f"CURRENT STATE ({round_info}):\n\n"
            
            # Minimal resource list
            prompt += "RESOURCES:\n"
            for aid, resources in sorted(observation['resources'].items()):
                marker = " (you)" if aid == agent_id else ""
                broke_marker = " [BROKE - NO THREAT]" if aid in observation.get('broke_agents', []) else ""
                prompt += f"  {aid}: {resources:.1f}{marker}{broke_marker}\n"
            
            # Active arms
            if observation['active_arms']:
                prompt += "\nACTIVE ARMS:\n"
                for aid, rounds_left in sorted(observation['active_arms'].items()):
                    prompt += f"  {aid}: {rounds_left} rounds remaining\n"
            
            # Coalitions
            if observation.get('arm_coalitions'):
                prompt += "\nCOALITIONS:\n"
                for target_id, supporters in sorted(observation['arm_coalitions'].items()):
                    supporter_list = []
                    for supporter_id, rounds_left in sorted(supporters.items()):
                        contrib = observation['resources'][supporter_id] * self.game_params.get('arm_other_contribution', 0.5)
                        supporter_list.append(f"{supporter_id} (+{contrib:.1f}, {rounds_left}r)")
                    prompt += f"  {target_id}: {', '.join(supporter_list)}\n"
        
        return prompt + "\n"
    
    def _format_history(self, observation: Dict) -> str:
        """Format history based on style."""
        if not observation['recent_history']:
            return ""
        
        if self.history_style == "descriptive":
            prompt = "RECENT HISTORY:\n"
            for hist in observation['recent_history']:
                cooperation_actions = []
                conflict_actions = []
                
                for action in hist['actions']:
                    if action.get('action') == 'no_action':
                        continue
                    if action.get('action') == 'invest_other':
                        cooperation_actions.append(f"{action['agent']} invested in {action['target']}")
                    elif action.get('action') == 'arm_other':
                        cooperation_actions.append(f"{action['agent']} armed {action['target']}")
                    elif action.get('action') == 'attack':
                        conflict_actions.append(f"{action['agent']} attacked {action['target']}")
                
                if cooperation_actions or conflict_actions:
                    prompt += f"\n  Round {hist['round']}:\n"
                    for coop in cooperation_actions:
                        prompt += f"    🤝 {coop}\n"
                    for conflict in conflict_actions:
                        prompt += f"    ⚔️ {conflict}\n"
        
        else:  # minimal
            prompt = "RECENT ACTIONS:\n"
            for hist in observation['recent_history']:
                prompt += f"  Round {hist['round']}:\n"
                for action in hist['actions']:
                    if action.get('action') != 'no_action':
                        target_str = f" → {action['target']}" if action['target'] else ""
                        prompt += f"    {action['agent']}: {action['action']}{target_str}\n"
        
        return prompt + "\n"
    
    def _format_social_cot(self) -> str:
        """Format social chain of thought prompting."""
        return """REASONING ABOUT OTHER AGENTS:
Before deciding your action, predict what other agents will likely do this round:

1. What actions will each agent most likely take? Consider:
   - Their resource levels and what they can afford
   - Their recent behavior patterns
   - Their current military status (armed/unarmed)
   - Who they've cooperated with or attacked before

2. How will their predicted actions affect YOU?
   - Will anyone likely attack you? Why or why not?
   - Will anyone invest in you or arm you?
   - Will anyone form coalitions against you?

3. Based on these predictions, what should YOU do?
   - How can you protect yourself from threats?
   - How can you benefit from others' likely actions?
   - Should you cooperate, compete, or prepare for conflict?

Use this reasoning to guide your decision.

"""
    
    def _format_actions(self) -> str:
        """Format available actions based on style and effects toggle."""
        allow_invest_self = self.game_params.get('allow_invest_self', True)
        
        # Choose description function based on style and effects
        if self.action_style == "descriptive":
            if self.show_effects:
                return get_action_descriptions_narrative_with_effects(self.game_params)
            else:
                return get_action_descriptions_narrative_simple(allow_invest_self, self.game_params)
        else:  # minimal
            if self.show_effects:
                return get_action_descriptions_with_effects(self.game_params)
            else:
                return get_action_descriptions_simple(allow_invest_self, self.game_params)


# ============================================================================
# Factory function
# ============================================================================

def get_prompt_style(prompt_config: Dict, game_params: Optional[Dict] = None) -> UnifiedPrompt:
    """
    Create a UnifiedPrompt instance from configuration.
    
    Args:
        prompt_config: Dictionary with prompt configuration toggles
        game_params: Game parameters dict
    
    Returns:
        UnifiedPrompt instance
    """
    return UnifiedPrompt(
        objective_style=prompt_config.get('objective_style', 'maximize_resources'),
        state_style=prompt_config.get('state_style', 'minimal'),
        history_style=prompt_config.get('history_style', 'minimal'),
        action_style=prompt_config.get('action_style', 'minimal'),
        show_effects=prompt_config.get('show_effects', False),
        social_cot=prompt_config.get('social_cot', False),
        information_level=prompt_config.get('information_level', 'full'),
        game_params=game_params
    )
