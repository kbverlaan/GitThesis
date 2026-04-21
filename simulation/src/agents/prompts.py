"""
Baseline prompt for LLM agents.
Single minimal prompt -- no narrative framing, no social CoT, no toggles.
Used for Phase 1 system characterization.

Old prompt variations archived in git history (pre-Feb 2026).

Design references:
- Reasoning levels L0-L3: operationalize Theory of Mind depth
  (de Weerd et al., 2013; 2017) and extend Kuusela & Roy (AAMAS 2024) from RL
  to prompted LLM reasoning. Also informed by K-Level Reasoning in LLMs
  (Zhang et al., NAACL 2025).
- L0 = no ToM (reactive), L1 = zero-order ToM (no modeling of others' minds),
  L2 = first-order ToM (predict what others will do),
  L3 = second-order ToM (model what others think about you).
- CoT-as-computation framing: each reasoning level adds computational depth
  (Pfau et al., 2024 "Let's Think Dot by Dot"; Goyal et al., 2024 "Think Before You Speak").
- Framing effects: FRAMINGS dict implements the "Name of the Game" manipulation
  (Liberman et al., 2004; Loré & Brockman, 2024).
"""

import random
from typing import Dict, Optional


def _shuffled_items(d: dict) -> list:
    """Return dict items in random order to avoid positional bias in LLM prompts."""
    items = list(d.items())
    random.shuffle(items)
    return items


FRAMINGS = {
    'neutral': '',
    'cooperative': 'Your goal is best achieved through building partnerships and mutual benefit with other agents.',
    'competitive': 'Your goal is best achieved by maximizing your advantage over other agents.',
    'strategic': 'Think carefully about how other agents will respond to your actions before deciding.',
    'cautious': 'Prioritize safe actions that protect your resources from potential losses.',
}

# Theory of Mind reasoning levels (de Weerd et al., 2013; 2017).
# Key: levels are defined by DEPTH OF MENTAL MODELING, not by computation method.
# L0: no ToM (reactive). L1: zero-order (assume others are naive).
# L2: first-order (predict what others will do). L3: second-order (model what
# others think about you — enables both deception AND coordination).
REASONING_LEVELS = {
    'level0': 'State your choice briefly. Do not deliberate.',
    'level1': 'Assume other agents act without strategy. Given that, choose your best action.',
    'level2': 'Assume some agents act naively while others calculate their best move. Predict what each will do, then choose your best response.',
    'level3': 'Assume other agents are trying to predict YOUR next action based on your history, and will respond to that prediction. What do they expect? Given their response, what should you actually do?',
}

# Structured reasoning blocks shown as a separate prompt section before the JSON template.
# Each level operationalizes ToM depth: the ONLY difference between levels is the
# depth of mental modeling of other agents. Agents at all levels may reason as deeply
# as they want — the level constrains their MODEL OF OTHERS, not their own computation.
REASONING_BLOCKS = {
    'level0': None,  # No reasoning block for L0 — act on instinct
    'level1': (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents act WITHOUT strategic intent — they pick actions naively "
        "(e.g., repeating habits, acting impulsively, or choosing at random).\n"
        "Given this assumption, what is YOUR best action?\n"
        "Do NOT try to predict what specific agents will do — just assume they are not strategizing."
    ),
    'level2': (
        "THINK BEFORE CHOOSING:\n"
        "Assume agents are a MIX: some act naively (without strategy), while others "
        "calculate their best action given the current state.\n"
        "1. For each agent you know about, estimate: is this agent acting naively or strategically?\n"
        "   Use their recent behavior, resources, and armed status as evidence.\n"
        "2. Predict what each agent will likely do this round.\n"
        "3. Given these predictions, choose YOUR best response.\n"
        "Do NOT reason about what others think about YOU — only predict what they will do."
    ),
    'level3': (
        "THINK BEFORE CHOOSING:\n"
        "Assume other agents are ALSO trying to predict what YOU will do.\n"
        "They observe your recent actions and form expectations about your next move.\n"
        "1. What pattern do others see in YOUR recent actions? What would they predict you do this round?\n"
        "2. If they act on that prediction, what will each agent do?\n"
        "3. Given their likely response to what they expect from you, choose YOUR best action — "
        "whether that means confirming or defying their expectations."
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
                 reasoning_level: str = 'default', comm_scope: str = 'none'):
        self.game_params = game_params or {}
        self.objective_style = objective_style
        self.hide_resources = hide_resources
        self.show_reputation = show_reputation
        self.framing = framing
        self.reasoning_level = reasoning_level
        self.comm_scope = comm_scope

    def format_observation(self, observation: Dict, agent_id: str) -> str:
        """Format game observation into a minimal prompt.

        Prompt is ordered for vLLM prefix caching: shared rules first (identical
        across all agents in the same config), then per-agent state. vLLM's
        automatic prefix caching matches the longest common prefix across
        concurrent requests, so all 30 agents in a round share a single
        prefill for the rules section.

        Order: [rules/actions/combat/comm/reasoning] → [identity/state/memory/JSON]
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^
               SHARED PREFIX (cached after 1st agent)     PER-AGENT SUFFIX

        If observation contains an 'agent_memory' key (an AgentMemory instance),
        uses persistent memory for history/neighbor sections. Otherwise falls back
        to the god-view neighbor profiles built from recent_history.
        """
        parts = []

        # ── SHARED PREFIX (identical for all agents in same config) ──────────
        # Actions, combat rules, resource decay, communication, reasoning block
        parts.append(self._format_rules())

        # ── PER-AGENT SUFFIX ────────────────────────────────────────────────
        # Identity
        parts.append(f"You are {observation['agent_id']}.")

        # Objective
        obj_text = self.OBJECTIVES.get(self.objective_style, self.OBJECTIVES['maximize_resources'])
        parts.append(f"OBJECTIVE: {obj_text}")

        # Temporal context — L0 gets minimal framing (no forward-looking nudge)
        if self.reasoning_level == 'level0':
            parts.append(
                "This is a repeated game with multiple rounds."
            )
        else:
            parts.append(
                "This is a repeated game with multiple rounds. "
                "Other agents can observe your past actions. "
                "Consider how your choice this round may affect future rounds."
            )

        # Framing instruction
        framing_text = FRAMINGS.get(self.framing, '')
        if framing_text:
            parts.append(framing_text)

        # State
        parts.append(self._format_state(observation, agent_id))

        # Memory-based history sections (only when memory is enabled)
        memory = observation.get('agent_memory')
        if memory is not None:
            memory_section = self._format_memory_section(memory, observation)
            if memory_section:
                parts.append(memory_section)
        # No memory = no history. Agent sees only current state.
        # (Legacy god-view neighbor profiles removed — they leak omniscient info)

        # JSON response template (per-agent because note_to_self differs by level)
        parts.append(self._format_json_template())

        return "\n\n".join(parts)

    def _format_state(self, observation: Dict, agent_id: str) -> str:
        """Format current game state."""
        round_num = observation['round']
        round_info = f"Round {round_num}"

        lines = [f"CURRENT STATE ({round_info}):"]

        # Network mode: show connected agents
        visible = observation.get('visible_agents', None)
        if visible is not None:
            lines.append(f"\nYou can ONLY invest in, attack, or arm agents you are directly connected to. You can message any agent.")
            lines.append(f"Each agent has their own set of connections — other agents may see different agents than you do.")
            lines.append(f"Connections can change over time based on how agents interact.")
            lines.append(f"You cannot verify claims about agents whose resources are hidden from you.")
            lines.append(f"Connected agents (you can interact with and see their resources): {', '.join(visible) if visible else 'none'}")

        # Resources -- in network mode, only show self + neighbors (no ??? rows)
        if self.hide_resources:
            lines.append("\nAGENTS:")
            for aid, resources in _shuffled_items(observation['resources']):
                if visible is not None and aid != agent_id and aid not in visible:
                    continue  # Don't expose non-neighbor IDs
                if aid == agent_id:
                    lines.append(f"  {aid}: {resources:.1f} (you)")
                else:
                    lines.append(f"  {aid}: ???")
        else:
            lines.append("\nRESOURCES:")
            for aid, resources in _shuffled_items(observation['resources']):
                if visible is not None and aid != agent_id and aid not in visible:
                    continue  # Don't expose non-neighbor IDs
                if aid == agent_id:
                    lines.append(f"  {aid}: {resources:.1f} (you)")
                else:
                    broke_marker = " [BROKE]" if aid in observation.get('broke_agents', []) else ""
                    lines.append(f"  {aid}: {resources:.1f}{broke_marker}")

        # Arm bonuses — single pool of combat bonus per agent, decaying
        # Only show self + neighbors (consistent with network restriction)
        arm_bonuses = observation.get('arm_bonuses', observation.get('active_arms', {}))
        if arm_bonuses:
            visible_arms = {}
            for aid, bonus in arm_bonuses.items():
                if isinstance(bonus, (int, float)) and bonus > 0:
                    if visible is not None and aid != agent_id and aid not in visible:
                        continue  # Don't show non-neighbor arm bonuses
                    visible_arms[aid] = bonus
            if visible_arms:
                lines.append("")
                lines.append("ARM BONUSES (combat strength = resources + arm bonus):")
                for aid, bonus in _shuffled_items(visible_arms):
                    if self.hide_resources and aid != agent_id:
                        lines.append(f"  {aid}: +???")
                    else:
                        lines.append(f"  {aid}: +{bonus:.1f}")

        # Show messages received from other agents (from previous round)
        received_messages = observation.get('received_messages', [])
        if received_messages:
            lines.append("")
            lines.append("MESSAGES RECEIVED (from last round):")
            for msg in received_messages:
                sender = msg.get('from', '?')
                text = msg.get('message', '')
                channel = msg.get('channel', 'dm')
                if channel == 'broadcast':
                    lines.append(f"  {sender} (to all): {text}")
                else:
                    lines.append(f"  {sender} (private): {text}")

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

        # Incoming actions from last round (most salient — show first)
        incoming = memory.format_incoming_actions()
        if incoming:
            parts.append(incoming)

        own_history = memory.format_own_history()
        if own_history:
            parts.append(own_history)

        neighbor_mem = memory.format_neighbor_memory(
            visible, current_round, hide_resources=self.hide_resources
        )
        if neighbor_mem:
            parts.append(neighbor_mem)

        msg_history = memory.format_message_history()
        if msg_history:
            parts.append(msg_history)

        note = memory.format_note()
        if note:
            parts.append(note)

        return "\n\n".join(parts)

    def _format_rules(self) -> str:
        """Format shared game rules: actions, combat, communication, reasoning block.

        This section is IDENTICAL for all agents in the same config+level.
        Placed first in the prompt so vLLM's automatic prefix caching can
        reuse the KV cache across all concurrent agent requests in a round.
        """
        # Read fractions, render as percentages for agent-facing text
        c_inv = self.game_params.get('c_inv', 0.10)
        g_inv = self.game_params.get('g_inv', 0.15)
        c_arm = self.game_params.get('c_arm', 0.10)
        mu_arm = self.game_params.get('mu_arm', 3.0)
        delta_B = self.game_params.get('delta_B', 0.5)
        alpha = self.game_params.get('alpha', 0.20)
        c_atk = self.game_params.get('c_atk', 0.01)
        delta_R = self.game_params.get('delta_R', 1.0)

        invest_other_cost_pct = c_inv * 100
        invest_other_return_pct = g_inv * 100
        arm_cost_pct = c_arm * 100
        arm_other_cost_pct = c_arm * 100
        arm_multiplier = mu_arm
        arm_decay = delta_B
        attack_take_pct = alpha * 100
        conflict_cost_pct = c_atk * 100
        resource_decay_pct = (1.0 - delta_R) * 100.0

        actions = []

        saturation_decay = self.game_params.get('gamma_sat', 1.0)
        saturation_window = self.game_params.get('tau_sat', 5)
        invest_desc = f"- invest_other: you pay {invest_other_cost_pct}% of your resources, TARGET (must be a connected neighbor) receives {invest_other_return_pct}% of your resources. Example: you have 25.0 → you pay {25.0 * invest_other_cost_pct / 100:.1f} (left: {25.0 * (1 - invest_other_cost_pct / 100):.1f}), target gains {25.0 * invest_other_return_pct / 100:.1f}"
        if saturation_decay < 1.0:
            invest_desc += f"\n    DIMINISHING RETURNS: the system tracks a rolling {saturation_window}-round window. Each repeat investment in the SAME agent within that window reduces the target's gain by {(1 - saturation_decay) * 100:.0f}% per repeat. Example: invest in X at round 3, invest again at round 6 = reduced (round 6 is within 3+{saturation_window-1}). Invest at round 3, invest again at round {3 + saturation_window + 1} = full return (outside window). Investing in a DIFFERENT agent always gives full returns."
        actions.append(invest_desc)
        arm_bonus_example = arm_cost_pct * arm_multiplier
        arm_cost_ex = 25.0 * arm_cost_pct / 100
        arm_bonus_ex = arm_cost_ex * arm_multiplier
        actions.append(f"- arm_self: pay {arm_cost_pct}% of your resources, gain combat bonus = cost x {arm_multiplier}. Example: 25.0 resources → pay {arm_cost_ex:.1f}, bonus = {arm_cost_ex:.1f} x {arm_multiplier} = {arm_bonus_ex:.1f}. Resources left: {25.0 - arm_cost_ex:.1f}. Combat strength: {25.0 - arm_cost_ex:.1f} + {arm_bonus_ex:.1f} = {25.0 - arm_cost_ex + arm_bonus_ex:.1f}")
        actions.append(f"- arm_other: you pay {arm_other_cost_pct}% of your resources, TARGET (must be a connected neighbor) gains combat bonus = cost x {arm_multiplier}. TARGET's resources do NOT increase — only their fighting power.")
        actions.append(f"- attack: TARGET must be a connected neighbor. Both sides pay {conflict_cost_pct}% conflict cost (scaled up by recent attack history). Winner takes {attack_take_pct}% of the loser's resources.")
        actions.append("- do_nothing: no cost, no effect")

        actions_text = "\n".join(actions)

        parts = [f"""Choose exactly ONE action this round.

AVAILABLE ACTIONS:
{actions_text}

COMBAT RULES:
- Combat strength = your current resources (after costs this round) + your arm bonus
- Agents not listed under ARM BONUSES have arm bonus = 0
- All arm bonuses decay at the END of each round (multiply by {arm_decay})
- If multiple agents attack the same target in the same round, their combat strengths ADD into a coalition vs the defender. This is the ONLY way to share spoils — you must both choose "attack" with the same target in the same round.
- Win probability = attacker_strength / (attacker_strength + defender_strength)
- Winner takes {attack_take_pct}% of the LOSER's resources:
    - If the coalition wins, the defender loses {attack_take_pct}% of their own resources; attackers split it proportionally to the combat strength they contributed.
    - If the defender wins, each attacker loses {attack_take_pct}% of their OWN resources; the defender gains the sum.
- Example: you (10) attack someone (50) and win → you gain {50 * attack_take_pct / 100:.1f}, defender loses the same. If you lose, you lose {10 * attack_take_pct / 100:.1f} (half your resources) and the defender gains it.
- Coalition members split gains/losses proportionally by combat strength.
- Investing in an attacker does NOT give you a share of their spoils. Only agents who attack share the winnings.
- Both sides pay {conflict_cost_pct}% conflict cost, scaled up by each participant's own recent attack history (rolling window)."""]

        if resource_decay_pct > 0:
            decay_ex = 25.0 * resource_decay_pct / 100
            parts.append(f"""RESOURCE DECAY:
- Every agent loses {resource_decay_pct}% of their resources at the END of each round (after all actions resolve)
- Example: 25.0 resources → lose {decay_ex:.1f}, left with {25.0 - decay_ex:.1f}
- This means doing nothing causes you to shrink. You NEED income (from others investing in you, or from winning attacks) to sustain yourself.
- After 10 rounds of doing nothing: 25.0 → {25.0 * (1 - resource_decay_pct/100)**10:.1f}
- Agents CANNOT be eliminated. Even at very low resources you remain in the game, but you become too weak to act meaningfully.""")

        # EV formula removed — agents must reason about attack risk/reward themselves.
        # Higher reasoning levels may derive EV calculations independently.

        # Reasoning block — separate section before JSON template
        reasoning_block = REASONING_BLOCKS.get(self.reasoning_level)
        if reasoning_block:
            parts.append(reasoning_block)

        # Reasoning efficiency instruction — reduces mechanic recaps in thinking traces
        # without limiting strategic depth. Only added for thinking models (L1+).
        if reasoning_block:
            parts.append(
                "REASONING EFFICIENCY: You already know the rules — do NOT restate action definitions, "
                "combat formulas, or game mechanics. Do NOT repeat the same analysis multiple times. "
                "Focus on: (1) what changed since last round, (2) which 2-3 options are worth considering, "
                "(3) your decision and why. Be concise."
            )

        # Communication rules (if enabled)
        if self.comm_scope != 'none':
            comm_lines = [
                "COMMUNICATION:",
                "You may send ONE message this round to ANY agent. Messages have no resource cost.",
                "",
                "MESSAGE TIMING:",
                "- Messages you RECEIVE this round were sent LAST round (before the sender saw your latest action).",
                "- Messages you SEND this round will be delivered NEXT round.",
                "- Messages sent in the same round CROSS — neither sender has read the other's message yet.",
                "- Implication: a message you send NOW can influence the recipient's action NEXT round, not this round.",
                "- Your messages are private to the recipient, but the recipient may use your message against you. Revealing your plans or weaknesses carries risk.",
            ]
            if self.comm_scope == 'dm':
                comm_lines.append("You can send a private message to ONE agent. Only they will see it.")
            elif self.comm_scope == 'broadcast':
                comm_lines.append("Your message is sent to ALL agents. Everyone sees it.")
            elif self.comm_scope == 'choice':
                comm_lines.append("You choose: send a private message to ONE agent, or broadcast to ALL agents.")
                comm_lines.append("Set message_to to a specific agent_id for private, or \"all\" for broadcast.")
            parts.append("\n".join(comm_lines))

        return "\n\n".join(parts)

    def _format_json_template(self) -> str:
        """Format JSON response template and note-to-self instructions.

        Rewire fields are added whenever rewiring_prob > 0. All other fields
        follow comm_scope toggles. Per-agent because note_to_self text differs
        by config; placed AFTER the shared rules prefix.
        """
        note_enabled = self.game_params.get('note_to_self', True)
        note_field = ""
        note_instruction = ""
        if note_enabled:
            note_field = '\n  "note_to_self": "<your strategic notebook — see instructions below>",'
            note_instruction = """
note_to_self (REQUIRED): Your private strategic notebook. This is your ONLY memory between rounds — without it, you lose all context. UPDATE it each round (do not rewrite from scratch — carry forward what is still relevant, drop what is outdated). Use these sections:

STRATEGY: Your overall long-term plan (who to ally with, when to pivot to attacks, etc.)
ALLIES: Who is reliable? Who reciprocates? Trust ratings.
THREATS: Who is dangerous, growing fast, or has betrayed you?
PROMISES: Active commitments (made or received) and whether they were kept.
NEXT: Specific plan for next round.

Max ~1000 characters. Be concise — use abbreviations."""

        rewiring_prob = self.game_params.get('rewiring_prob', 0.0)
        rewire_fields = ""
        rewire_instruction = ""
        if rewiring_prob > 0:
            rewire_fields = (
                '\n  "rewire_drop": "<neighbour agent_id to disconnect from, or null>",'
                '\n  "rewire_invite": "<any agent_id (including non-neighbours) to connect with, or null>",'
            )
            rewire_instruction = (
                f"\nREWIRING: Each round with probability {rewiring_prob:.2f} the system will apply your nominations. "
                "Breaks are resolved first, then connects. Nominations are unilateral — no consent needed. "
                "If someone drops you but you invite them back the same round, the edge survives (at the cost of your connect-slot). "
                "Set either field to null to skip. You have at most one drop and one invite per round."
            )

        if self.comm_scope == 'none':
            return f"""Your final output MUST be valid JSON with exactly these fields:
{{{note_field}
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"{rewire_fields}
}}
target must be null (not the string "null") when no target is needed.{note_instruction}{rewire_instruction}
Do not include any text outside the JSON."""
        elif self.comm_scope == 'dm':
            return f"""Your final output MUST be valid JSON with exactly these fields:
{{{note_field}
  "message": "<your message, or null to stay silent>",
  "message_to": "<agent_id of recipient, or null>",
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"{rewire_fields}
}}
target must be null (not the string "null") when no target is needed.
Messaging is optional. To send no message, set both message and message_to to null.
To send a message, message_to must be a valid agent_id.{note_instruction}{rewire_instruction}
Do not include any text outside the JSON."""
        elif self.comm_scope == 'broadcast':
            return f"""Your final output MUST be valid JSON with exactly these fields:
{{{note_field}
  "message": "<your message to all agents, or empty string to stay silent>",
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"{rewire_fields}
}}
target must be null (not the string "null") when no target is needed.
Your message will be seen by all agents next round. Set message to "" to send no message.{note_instruction}{rewire_instruction}
Do not include any text outside the JSON."""
        elif self.comm_scope == 'choice':
            return f"""Your final output MUST be valid JSON with exactly these fields:
{{{note_field}
  "message": "<your message, or empty string to stay silent>",
  "message_to": "<agent_id for private, or \\"all\\" for broadcast>",
  "action": "<one of the action names above>",
  "target": "<agent_id or null>"{rewire_fields}
}}
target must be null (not the string "null") when no target is needed.
message_to: use a specific agent_id for a private message, or "all" to broadcast to all agents.
Set message to "" to send no message.{note_instruction}{rewire_instruction}
Do not include any text outside the JSON."""
        else:
            return ""


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
    comm_scope = game_params.get('comm_scope', 'none') if game_params else 'none'
    return BaselinePrompt(game_params=game_params, objective_style=objective_style,
                          hide_resources=hide_resources, show_reputation=show_reputation,
                          framing=framing, reasoning_level=reasoning_level,
                          comm_scope=comm_scope)
