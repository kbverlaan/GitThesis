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
                 hide_resources: bool = False, show_reputation: bool = False, framing: str = 'neutral'):
        self.game_params = game_params or {}
        self.objective_style = objective_style
        self.hide_resources = hide_resources
        self.show_reputation = show_reputation
        self.framing = framing

    def format_observation(self, observation: Dict, agent_id: str) -> str:
        """Format game observation into a minimal prompt."""
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

        # History
        history = self._format_history(observation)
        if history:
            parts.append(history)

        # Reputation summary (pre-computed from history)
        if self.show_reputation:
            reputation = self._format_reputation(observation, agent_id)
            if reputation:
                parts.append(reputation)

        # Actions
        parts.append(self._format_actions())

        return "\n\n".join(parts)

    def _format_state(self, observation: Dict, agent_id: str) -> str:
        """Format current game state."""
        round_num = observation['round']
        max_rounds = observation.get('max_rounds')
        round_info = f"Round {round_num}/{max_rounds}" if max_rounds else f"Round {round_num}"

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

        # Active arms
        if observation['active_arms']:
            lines.append("")
            lines.append("ARMED:")
            for aid, rounds_left in sorted(observation['active_arms'].items()):
                lines.append(f"  {aid}: {rounds_left} rounds remaining")

        # Coalitions
        if observation.get('arm_coalitions'):
            lines.append("")
            lines.append("COALITIONS:")
            arm_other_contrib = self.game_params.get('arm_other_contribution', 0.5)
            for target_id, supporters in sorted(observation['arm_coalitions'].items()):
                supporter_parts = []
                for supporter_id, rounds_left in sorted(supporters.items()):
                    contrib = observation['resources'].get(supporter_id, 0) * arm_other_contrib
                    supporter_parts.append(f"{supporter_id} (+{contrib:.1f}, {rounds_left}r)")
                lines.append(f"  {target_id}: {', '.join(supporter_parts)}")

        return "\n".join(lines)

    def _format_history(self, observation: Dict) -> str:
        """Format recent action history."""
        if not observation['recent_history']:
            return ""

        lines = ["RECENT ACTIONS:"]
        for hist in observation['recent_history']:
            lines.append(f"  Round {hist['round']}:")
            for action in hist['actions']:
                if action.get('action') != 'no_action':
                    target_str = f" -> {action['target']}" if action.get('target') else ""
                    lines.append(f"    {action['agent']}: {action['action']}{target_str}")

        return "\n".join(lines)

    def _format_reputation(self, observation: Dict, agent_id: str) -> str:
        """Pre-computed reputation summary from history.

        Counts how many times each other agent invested in / attacked / armed
        the current agent, and vice versa.  Only includes agents with at least
        one interaction.
        """
        if not observation.get('recent_history'):
            return ""

        # {other_id: {"invested_in_you": n, "attacked_you": n, "armed_you": n,
        #             "you_invested": n, "you_attacked": n, "you_armed": n}}
        counts: Dict[str, Dict[str, int]] = {}

        for hist in observation['recent_history']:
            for action in hist['actions']:
                actor = action.get('agent')
                act = action.get('action', '')
                target = action.get('target')

                if actor == agent_id and target and target != agent_id:
                    entry = counts.setdefault(target, {})
                    if act == 'invest_other':
                        entry['you_invested'] = entry.get('you_invested', 0) + 1
                    elif act == 'attack':
                        entry['you_attacked'] = entry.get('you_attacked', 0) + 1
                    elif act == 'arm_other':
                        entry['you_armed'] = entry.get('you_armed', 0) + 1

                elif target == agent_id and actor and actor != agent_id:
                    entry = counts.setdefault(actor, {})
                    if act == 'invest_other':
                        entry['invested_in_you'] = entry.get('invested_in_you', 0) + 1
                    elif act == 'attack':
                        entry['attacked_you'] = entry.get('attacked_you', 0) + 1
                    elif act == 'arm_other':
                        entry['armed_you'] = entry.get('armed_you', 0) + 1

        if not counts:
            return ""

        # Only show agents in spatial visibility (if applicable)
        visible = observation.get('visible_agents', None)

        lines = ["YOUR INTERACTION HISTORY:"]
        for other_id in sorted(counts):
            if visible is not None and other_id not in visible:
                continue
            c = counts[other_id]
            parts = []
            if c.get('invested_in_you'):
                parts.append(f"invested in you {c['invested_in_you']}x")
            if c.get('attacked_you'):
                parts.append(f"attacked you {c['attacked_you']}x")
            if c.get('armed_you'):
                parts.append(f"armed you {c['armed_you']}x")
            if c.get('you_invested'):
                parts.append(f"you invested {c['you_invested']}x")
            if c.get('you_attacked'):
                parts.append(f"you attacked {c['you_attacked']}x")
            if c.get('you_armed'):
                parts.append(f"you armed {c['you_armed']}x")
            if parts:
                lines.append(f"  {other_id}: {', '.join(parts)}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_actions(self) -> str:
        """Format available actions with costs from game params."""
        allow_invest_self = self.game_params.get('allow_invest_self', True)
        invest_self_cost = self.game_params.get('invest_self_cost', 0)
        invest_self_return = self.game_params.get('invest_self_return', 2)
        invest_other_cost = self.game_params.get('invest_other_cost', 0)
        invest_other_return = self.game_params.get('invest_other_return', 5)
        arm_cost = self.game_params.get('arm_cost', 5)
        arm_multiplier = self.game_params.get('arm_multiplier', 2)
        arm_duration = self.game_params.get('arm_duration', 3)
        arm_other_contrib = self.game_params.get('arm_other_contribution', 0.5)
        attack_take = self.game_params.get('attack_take_percent', 40)
        conflict_cost = self.game_params.get('conflict_cost', 3)

        actions = []

        if allow_invest_self:
            net = invest_self_return - invest_self_cost
            actions.append(f"- invest_self: spend {invest_self_cost}, gain {invest_self_return} (net +{net})")

        actions.append(f"- invest_other: spend {invest_other_cost}, target gains {invest_other_return}")
        actions.append(f"- arm_self: spend {arm_cost}, combat power x{arm_multiplier} for {arm_duration} rounds")
        actions.append(f"- arm_other: spend {arm_cost}, add {arm_other_contrib*100:.0f}% of your resources to target's combat power")
        actions.append(f"- attack: both pay {conflict_cost}, winner takes {attack_take:.0f}% of loser's resources")
        actions.append("- do_nothing: pass this round, no cost")

        actions_text = "\n".join(actions)

        return f"""AVAILABLE ACTIONS:
{actions_text}

Combat: win probability = your power / (your power + opponent power).
Power = resources x multiplier (if armed) + coalition support.
You can only perform actions you can afford.

Respond with valid JSON only:
{{
  "action": "<action_type>",
  "target": "<agent_id or null>",
  "reasoning": "<brief explanation>"
}}"""


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
    return BaselinePrompt(game_params=game_params, objective_style=objective_style,
                          hide_resources=hide_resources, show_reputation=show_reputation,
                          framing=framing)
