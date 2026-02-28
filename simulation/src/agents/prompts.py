"""
Baseline prompt for LLM agents.
Single minimal prompt -- no narrative framing, no social CoT, no toggles.
Used for Phase 1 system characterization.

Old prompt variations archived in git history (pre-Feb 2026).
"""

from typing import Dict, Optional


FRAMINGS = {
    'neutral': '',
    'cooperative': 'Your goal is best achieved through building partnerships and mutual benefit with other agents.',
    'competitive': 'Your goal is best achieved by maximizing your advantage over other agents.',
    'strategic': 'Think carefully about how other agents will respond to your actions before deciding.',
    'cautious': 'Prioritize safe actions that protect your resources from potential losses.',
}

REASONING_LEVELS = {
    'level0': 'State your choice briefly. Do not deliberate.',
    'level1': 'Compute the expected resource change for each action, then choose the highest payoff. Do not predict what neighbors will do.',
    'level2': 'Predict each neighbor\'s most likely action based on their recent behavior, then choose your best response. Do not reason about what they think of you.',
    'level3': 'Your neighbors observe your recent actions and predict what you will do next. Predict their response to that prediction, then choose your best action — which may differ from what they expect.',
}

# Structured reasoning blocks shown as a separate prompt section before the JSON template.
# Each level explicitly states what it assumes about other agents' reasoning.
REASONING_BLOCKS = {
    'level0': None,  # No reasoning block for L0
    'level1': (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick actions without strategic calculation.\n"
        "For each available action, compute its expected resource change:\n"
        "- invest_self/invest_other/do_nothing: use the costs and returns listed above.\n"
        "- arm_self: cost now vs combat advantage later (only useful if you expect to attack or be attacked).\n"
        "- attack: expected gain = win_probability x take% x opponent_resources, minus conflict_cost.\n"
        "  Include your arm bonus when computing win probability (combat strength = resources + arm bonus).\n"
        "Compare these values and choose the action with the highest expected payoff.\n"
        "Do NOT predict what specific neighbors will do — treat their actions as unknown."
    ),
    'level2': (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents pick their individually best action given the current state.\n"
        "1. For each neighbor, predict their most likely action based on:\n"
        "   - Their recent behavior pattern (shown in NEIGHBOR PROFILES)\n"
        "   - Their current resources and armed status\n"
        "   - What action would give THEM the best payoff right now\n"
        "2. Given these predictions, choose your best response.\n"
        "Do NOT reason about what neighbors think about YOU — only predict what they will do."
    ),
    'level3': (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents look at YOUR recent actions to predict what you will do, "
        "then pick their best response to that prediction.\n"
        "1. Look at your own recent actions in NEIGHBOR PROFILES (the 'you ... them' entries). "
        "List your recent actions — what pattern do your neighbors see? What action would they predict you take this round?\n"
        "2. For each neighbor: given their prediction of YOUR action, what will THEY choose?\n"
        "3. Now choose YOUR best action given what each neighbor will do — "
        "which may differ from what they expect you to do."
    ),
}


class BaselinePrompt:
    """
    Minimal baseline prompt for system characterization.
    Shows: agent ID, objective, resources, arms, coalitions, history, actions.
    """

    OBJECTIVES = {
        'maximize_resources': "Maximize your absolute resource count.",
        'avoid_last': "Avoid being the agent with the fewest resources at the end of the game.",
    }

    def __init__(self, game_params: Optional[Dict] = None, objective_style: str = 'maximize_resources',
                 hide_resources: bool = False, show_reputation: bool = False, framing: str = 'neutral',
                 reasoning_level: str = 'default'):
        self.game_params = game_params or {}
        self.objective_style = objective_style
        self.hide_resources = hide_resources
        self.show_reputation = show_reputation
        self.framing = framing
        self.reasoning_level = reasoning_level

    def format_observation(self, observation: Dict, agent_id: str) -> str:
        """Format game observation into a minimal prompt.

        If observation contains an 'agent_memory' key (an AgentMemory instance),
        uses persistent memory for history/neighbor sections. Otherwise falls back
        to the god-view neighbor profiles built from recent_history.
        """
        parts = []

        # Identity
        parts.append(f"You are {observation['agent_id']}.")

        # Objective
        obj_text = self.OBJECTIVES.get(self.objective_style, self.OBJECTIVES['maximize_resources'])
        parts.append(f"OBJECTIVE: {obj_text}")

        # Framing instruction
        framing_text = FRAMINGS.get(self.framing, '')
        if framing_text:
            parts.append(framing_text)

        # State
        parts.append(self._format_state(observation, agent_id))

        # Memory-based sections vs legacy neighbor profiles
        memory = observation.get('agent_memory')
        if memory is not None:
            memory_section = self._format_memory_section(memory, observation)
            if memory_section:
                parts.append(memory_section)
        else:
            profiles = self._format_neighbor_profiles(observation, agent_id)
            if profiles:
                parts.append(profiles)

        # Actions + reasoning block
        parts.append(self._format_actions())

        return "\n\n".join(parts)

    def _format_state(self, observation: Dict, agent_id: str) -> str:
        """Format current game state."""
        round_num = observation['round']
        round_info = f"Round {round_num}"

        lines = [f"CURRENT STATE ({round_info}):"]

        # Spatial mode: simple neighbor list, no coordinates
        visible = observation.get('visible_agents', None)
        if visible is not None:
            lines.append(f"\nYou can only interact with nearby agents this round.")
            lines.append(f"Nearby agents: {', '.join(visible) if visible else 'none'}")

        # Resources -- only show visible agents in spatial mode
        if self.hide_resources:
            lines.append("\nAGENTS:")
            for aid, resources in sorted(observation['resources'].items()):
                if visible is not None and aid != agent_id and aid not in visible:
                    continue
                if aid == agent_id:
                    lines.append(f"  {aid}: {resources:.1f} (you)")
                else:
                    lines.append(f"  {aid}: ???")
        else:
            lines.append("\nRESOURCES:")
            for aid, resources in sorted(observation['resources'].items()):
                if visible is not None and aid != agent_id and aid not in visible:
                    continue
                marker = " (you)" if aid == agent_id else ""
                broke_marker = " [BROKE]" if aid in observation.get('broke_agents', []) else ""
                lines.append(f"  {aid}: {resources:.1f}{marker}{broke_marker}")

        # Arm bonuses — single pool of combat bonus per agent, decaying
        arm_bonuses = observation.get('arm_bonuses', observation.get('active_arms', {}))
        if arm_bonuses:
            lines.append("")
            lines.append("ARM BONUSES (combat strength = resources + arm bonus):")
            for aid, bonus in sorted(arm_bonuses.items()):
                if isinstance(bonus, (int, float)) and bonus > 0:
                    lines.append(f"  {aid}: +{bonus:.1f}")

        return "\n".join(lines)

    def _format_neighbor_profiles(self, observation: Dict, agent_id: str) -> str:
        """Personalized neighbor profiles from history.

        Replaces the old flat history dump with compact per-neighbor summaries:
        - Interaction counts (what they did to you, what you did to them)
        - Their dominant behavior pattern
        - Resource trend (rising/falling/stable)

        Only shows visible neighbors in spatial mode. Subsumes _format_reputation().
        """
        if not observation.get('recent_history'):
            return ""

        visible = observation.get('visible_agents', None)
        resources = observation.get('resources', {})

        # {agent_id: {"toward_you": {act: n}, "from_you": {act: n}, "all_actions": {act: n}}}
        profiles: Dict[str, Dict] = {}

        for hist in observation['recent_history']:
            for action in hist['actions']:
                actor = action.get('agent')
                act = action.get('action', '')
                target = action.get('target')

                if act == 'no_action':
                    continue

                # Track all actions for behavior profiling
                for aid in [actor, target]:
                    if aid and aid != agent_id:
                        if visible is not None and aid not in visible:
                            continue
                        profiles.setdefault(aid, {
                            'toward_you': {}, 'from_you': {}, 'all_actions': {}
                        })

                # Actions directed at this agent
                if target == agent_id and actor and actor != agent_id:
                    p = profiles.get(actor)
                    if p is not None:
                        p['toward_you'][act] = p['toward_you'].get(act, 0) + 1

                # This agent's actions toward others
                if actor == agent_id and target and target != agent_id:
                    p = profiles.get(target)
                    if p is not None:
                        p['from_you'][act] = p['from_you'].get(act, 0) + 1

                # All actions by each agent (for behavior profiling)
                if actor and actor != agent_id:
                    p = profiles.get(actor)
                    if p is not None:
                        p['all_actions'][act] = p['all_actions'].get(act, 0) + 1

        if not profiles:
            return ""

        # Build output
        n_rounds = len(observation['recent_history'])
        lines = [f"NEIGHBOR PROFILES (last {n_rounds} rounds):"]

        for aid in sorted(profiles):
            p = profiles[aid]
            res = resources.get(aid, 0)

            # Dominant behavior
            if p['all_actions']:
                dominant = max(p['all_actions'], key=p['all_actions'].get)
                total = sum(p['all_actions'].values())
                dominant_pct = p['all_actions'][dominant] / total
                if dominant_pct >= 0.5:
                    behavior = dominant.replace('_', ' ')
                else:
                    behavior = 'mixed'
            else:
                behavior = 'inactive'

            # Interaction summary with you
            interactions = []
            for act, count in sorted(p['toward_you'].items()):
                label = act.replace('_', ' ')
                interactions.append(f"{label} you {count}x")
            for act, count in sorted(p['from_you'].items()):
                label = act.replace('_', ' ')
                interactions.append(f"you {label} them {count}x")

            interaction_str = ' | '.join(interactions) if interactions else 'no direct interaction'
            broke_marker = " BROKE" if aid in observation.get('broke_agents', []) else ""

            lines.append(f"  {aid} [{res:.0f}{broke_marker}]: {behavior} | {interaction_str}")

        return "\n".join(lines)

    def _format_memory_section(self, memory, observation: Dict) -> str:
        """Format memory-based history and neighbor sections.

        Uses the agent's persistent AgentMemory to build:
        - YOUR RECENT ACTIONS (own action sliding window)
        - NEIGHBOR MEMORY (accumulated per-agent observations)
        """
        visible = observation.get('visible_agents', None)
        current_round = observation.get('round', 0)

        parts = []

        own_history = memory.format_own_history()
        if own_history:
            parts.append(own_history)

        neighbor_mem = memory.format_neighbor_memory(visible, current_round)
        if neighbor_mem:
            parts.append(neighbor_mem)

        return "\n\n".join(parts)

    def _format_actions(self) -> str:
        """Format available actions, reasoning block, and JSON template."""
        allow_invest_self = self.game_params.get('allow_invest_self', True)
        invest_self_cost_pct = self.game_params.get('invest_self_cost_pct', 10)
        invest_self_return_pct = self.game_params.get('invest_self_return_pct', 20)
        invest_other_cost_pct = self.game_params.get('invest_other_cost_pct', 10)
        invest_other_return_pct = self.game_params.get('invest_other_return_pct', 15)
        arm_cost_pct = self.game_params.get('arm_cost_pct', 10)
        arm_other_cost_pct = self.game_params.get('arm_other_cost_pct', 10)
        arm_decay = self.game_params.get('arm_decay', 0.5)
        attack_take_pct = self.game_params.get('attack_take_pct', 40)
        conflict_cost_pct = self.game_params.get('conflict_cost_pct', 5)

        # Compute theta ratios for explicit display
        invest_self_ratio = f"1:{invest_self_return_pct/invest_self_cost_pct:.1f}" if invest_self_cost_pct > 0 else "free"
        invest_other_ratio = f"1:{invest_other_return_pct/invest_other_cost_pct:.1f}" if invest_other_cost_pct > 0 else "free"

        actions = []

        if allow_invest_self:
            net = invest_self_return_pct - invest_self_cost_pct
            actions.append(f"- invest_self: spend {invest_self_cost_pct}% of your resources, gain {invest_self_return_pct}% (net +{net}% for you, cost-to-benefit ratio {invest_self_ratio})")

        actions.append(f"- invest_other: spend {invest_other_cost_pct}% of your resources, TARGET gains {invest_other_return_pct}% of your resources (cost-to-benefit ratio {invest_other_ratio}, grows the total economy)")
        actions.append(f"- arm_self: spend {arm_cost_pct}% of your resources (removed from economy), adds that amount to your combat strength. Your total combat strength = resources + arm bonus.")
        actions.append(f"- arm_other: spend {arm_other_cost_pct}% of your resources (removed from economy), adds that amount to TARGET's combat strength. TARGET's resource count does NOT increase — only their fighting power.")
        actions.append(f"- attack: you pay {conflict_cost_pct}% of your resources, opponent pays {conflict_cost_pct}% of theirs. Winner takes {attack_take_pct}% of loser's remaining resources. Loser keeps the rest.")
        actions.append("- do_nothing: no cost, no effect")

        actions_text = "\n".join(actions)

        parts = [f"""Choose exactly ONE action this round.

AVAILABLE ACTIONS:
{actions_text}

COMBAT RULES:
- Combat strength = your resources + your arm bonus (agents not listed under ARM BONUSES have arm bonus = 0)
- arm_self adds {arm_cost_pct}% of your resources to your arm bonus
- arm_other adds {arm_other_cost_pct}% of your resources to TARGET's arm bonus
- All arm bonuses decay at the END of each round: they halve (x{arm_decay})
- Win probability = your_strength / (your_strength + opponent_strength)
- Attack expected value = win_prob x {attack_take_pct}% x opponent_resources - lose_prob x {attack_take_pct}% x your_resources - {conflict_cost_pct}% x your_resources"""]

        # Reasoning block — separate section before JSON template
        reasoning_block = REASONING_BLOCKS.get(self.reasoning_level)
        if reasoning_block:
            parts.append(reasoning_block)

        # JSON template — no reasoning field, we read thinking traces directly
        parts.append("""Your final output MUST be valid JSON with exactly these fields:
{
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"
}
target must be null (not the string "null") when no target is needed.
Do not include any text outside the JSON.""")

        return "\n\n".join(parts)


def get_prompt_style(prompt_config: Dict, game_params: Optional[Dict] = None) -> BaselinePrompt:
    """
    Create a BaselinePrompt instance.

    Keeps the same interface as before so llm_agent.py doesn't need changes.
    prompt_config is accepted but ignored for now (single baseline prompt).
    """
    objective_style = prompt_config.get('objective_style', 'maximize_resources')
    hide_resources = prompt_config.get('hide_resources', False)
    show_reputation = prompt_config.get('show_reputation', False)
    framing = prompt_config.get('framing', 'neutral')
    reasoning_level = prompt_config.get('reasoning_level', 'default')
    return BaselinePrompt(game_params=game_params, objective_style=objective_style,
                          hide_resources=hide_resources, show_reputation=show_reputation,
                          framing=framing, reasoning_level=reasoning_level)
