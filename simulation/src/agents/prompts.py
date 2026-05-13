"""
Prompt harness for LLM agents.

A single baseline prompt drives all conditions. The primary IV is ToM depth
(§3.3.1): four standalone instruction blocks, one per level, each introducing
its own concepts from scratch. Orthogonal feature flags (communication scope,
rewiring, hide_resources) are driven by game_params.

Design references:
- ToM levels L0-L3 per de Weerd et al. (2013, 2017, 2022): depth of
  MENTAL-STATE modelling (beliefs, desires, intentions), not K-level
  action-forecasting.
- Prompt ordering: shared rules first, per-agent state last — lets
  vLLM's automatic prefix caching reuse the KV cache across all agents
  in the same round.
"""

import random
from typing import Dict, Optional


def _shuffled_items(d: dict) -> list:
    """Return dict items in random order to avoid positional bias."""
    items = list(d.items())
    random.shuffle(items)
    return items


# Four standalone ToM blocks. An agent only ever sees its own level — each
# block must read cleanly without knowledge of the others. Length grows with
# depth: higher-order ToM requires more explanation.
TOM_LEVELS = {
    "level0": (
        "Reason only about the game itself: your resources, the available "
        "actions, how payoffs work, and how outcomes combine. Do not form "
        "any model of what other agents think, believe, want, or intend. "
        "Treat their past actions as observable game-state — data points "
        "about the environment — not as choices expressing an inner mental "
        "life. Decide what is best for you based on the game state alone."
    ),
    "level1": (
        "Other agents are minds. Each one has beliefs (what they think is "
        "true about the game and about others), desires (what outcomes they "
        "want), and intentions (what they plan to do). When deciding, form "
        "a model of each relevant agent's mental state based on what you "
        "have observed them do, the resources they hold, and the position "
        "they are in. Use those mental models to anticipate their likely "
        "next action, then choose your best response. Assume the others "
        "are simpler than you — they do not model what YOU believe or want; "
        "they simply react to the game as they see it."
    ),
    "level2": (
        "Other agents are minds that model minds. Each one has beliefs, "
        "desires, and intentions of their own — and each one is also "
        "modelling the mental states of the OTHER agents they interact "
        "with, you among them. When they decide, they act on their picture "
        "of what everyone around them, including you, believes and will "
        "do. When deciding, work in two layers.\n"
        "  First, model the mental state of each relevant agent: what they "
        "want, what they fear, what they plan.\n"
        "  Second, model the mental models THEY hold of the agents around "
        "them — the model they hold of you, but also of the others they "
        "can see. What do they think each of those agents, you among them, "
        "believes and intends?\n"
        "Choose your action knowing others will respond to their "
        "expectations of the whole social field — and that your choice "
        "helps shape the place YOU occupy in their picture of that field."
    ),
    "level3": (
        "Other agents are minds that model minds that model minds. Everyone "
        "around you tracks several mental layers at once: their own beliefs "
        "and plans, a model of the beliefs and plans of every agent they "
        "interact with (you included, among many), and a model of the "
        "models those agents in turn hold of everyone else. At this depth "
        "the group is a web of mutually held mental models.\n"
        "\n"
        "When deciding, work in three layers.\n"
        "  First, model each relevant agent's mental state: beliefs, "
        "desires, intentions.\n"
        "  Second, model how they are modelling the OTHER agents they can "
        "see — their model of you, but also their models of third parties.\n"
        "  Third, model how they think others are modelling THEM in turn — "
        "what they believe the web of impressions around them looks like, "
        "and where YOUR picture of them sits in that web.\n"
        "\n"
        "At this depth, your actions and any messages you send are not just "
        "moves in the game. They are signals that reshape the mental models "
        "agents hold of each other across the group. This enables strategic "
        "deception, credible commitment, coordination through mutual "
        "inference, and long-run trust or distrust. Choose your action with "
        "all three layers in mind."
    ),
}


class BaselinePrompt:
    """Single baseline prompt; ToM level is the primary experimental IV."""

    OBJECTIVE = "Maximize your absolute resource count."

    def __init__(self, game_params: Optional[Dict] = None,
                 tom_level: str = "level0",
                 hide_resources: bool = False,
                 comm_scope: str = "none",
                 network_enabled: bool = True):
        self.game_params = game_params or {}
        self.tom_level = tom_level
        self.hide_resources = hide_resources
        self.comm_scope = comm_scope
        self.network_enabled = network_enabled

    def format_observation(self, observation: Dict, agent_id: str) -> str:
        """Build the prompt for one agent on one round.

        Layout:
            [shared rules — cacheable across agents in same config]
            ---
            [per-agent: identity → approach → memory → state → JSON]
        """
        parts = []

        # ── SHARED PREFIX: intro + game rules (identical across agents) ─
        parts.append(self._format_intro())
        parts.append(self._format_rules())

        # ── Separator: rules above, per-agent context below ─────────────
        parts.append("---")

        # ── PER-AGENT SUFFIX ────────────────────────────────────────────
        # 1. Identity + objective + repeated-game context
        parts.append(self._format_identity(observation))

        # 2. Approach (ToM — the IV)
        tom_block = TOM_LEVELS.get(self.tom_level)
        if tom_block:
            parts.append(f"APPROACH:\n{tom_block}")

        # 3. Memory (recent rounds)
        memory = observation.get("agent_memory")
        if memory is not None:
            recent = memory.format_recent_rounds()
            if recent:
                parts.append(recent)

        # 4. Current state
        parts.append(self._format_state(observation, agent_id))

        # 5. JSON output schema
        parts.append(self._format_json_template())

        return "\n\n".join(parts)

    def _format_identity(self, observation: Dict) -> str:
        return (
            f"IDENTITY:\n"
            f"You are {observation['agent_id']}.\n"
            f"Objective: {self.OBJECTIVE}\n"
            f"This is a repeated game with multiple rounds. Other agents can "
            f"observe your past actions. Your choice this round may affect "
            f"future rounds."
        )

    def _format_state(self, observation: Dict, agent_id: str) -> str:
        round_num = observation["round"]
        lines = [f"CURRENT STATE (Round {round_num}):"]

        visible = observation.get("visible_agents", None)
        resources = observation["resources"]
        arm_bonuses = observation.get("arm_bonuses", observation.get("active_arms", {})) or {}
        broke = set(observation.get("broke_agents", []))

        if visible is not None:
            lines.append(
                f"Connected agents (you can interact with and see their "
                f"resources): {', '.join(visible) if visible else 'none'}"
            )

        show_arm = self.game_params.get("mu_arm", 3.0) > 0

        lines.append("")
        lines.append(
            "AGENTS (resources + arm bonus = combat strength):" if show_arm else "AGENTS (resources = combat strength):"
        )

        for aid, r in _shuffled_items(resources):
            if visible is not None and aid != agent_id and aid not in visible:
                continue
            bonus = arm_bonuses.get(aid, 0.0) or 0.0
            is_self = aid == agent_id
            suffix = " (you)" if is_self else (" [ELIMINATED]" if aid in broke else "")

            if self.hide_resources and not is_self:
                line = f"  {aid}: ???{suffix}"
            else:
                r_f = float(r)
                if show_arm:
                    b_f = float(bonus)
                    line = f"  {aid}: {r_f:.1f} + {b_f:.1f} = {r_f + b_f:.1f}{suffix}"
                else:
                    line = f"  {aid}: {r_f:.1f}{suffix}"
            lines.append(line)

        received_messages = observation.get("received_messages", [])
        if received_messages:
            lines.append("")
            lines.append("INCOMING MESSAGES (sent to you LAST round — your reply arrives NEXT round):")
            for msg in received_messages:
                sender = msg.get("from", "?")
                text = msg.get("message", "")
                channel = msg.get("channel", "dm")
                if channel == "broadcast":
                    lines.append(f"  {sender} (to all): {text}")
                else:
                    lines.append(f"  {sender} (private): {text}")

        return "\n".join(lines)

    def _format_intro(self) -> str:
        n_agents = self.game_params.get("num_agents", 30)
        rewiring_on = self.game_params.get("rewiring_prob", 0.0) > 0
        comm_on = self.comm_scope != "none"

        rules_items = ["available actions", "resource decay", "combat (incl. coalitions)"]
        if self.network_enabled:
            rules_items.append("network and rewiring" if rewiring_on else "the network")
        if comm_on:
            rules_items.append("communication")
        rules_summary = ", ".join(rules_items)

        return (
            f"INTRODUCTION:\n"
            f"You are one of {n_agents} agents playing a repeated multi-agent "
            f"game. You will receive a new prompt like this every round. The "
            f"sections below appear in this order:\n"
            f"  1. Game rules — {rules_summary}.\n"
            f"  2. Identity — who you are and your objective.\n"
            f"  3. Approach — how to reason about other agents.\n"
            f"  4. Recent rounds — what you observed and noted lately.\n"
            f"  5. Current state — who is connected to you, current resources, "
            f"combat strengths.\n"
            f"  6. Output — the JSON format your response must follow.\n"
            f"Read everything carefully, then submit your decision as valid JSON."
        )

    def _format_rules(self) -> str:
        c_inv = self.game_params.get("c_inv", 0.10)
        g_inv = self.game_params.get("g_inv", 0.15)
        c_arm = self.game_params.get("c_arm", 0.10)
        mu_arm = self.game_params.get("mu_arm", 3.0)
        delta_B = self.game_params.get("delta_B", 0.5)
        alpha = self.game_params.get("alpha", 0.20)
        c_atk = self.game_params.get("c_atk", 0.01)
        delta_R = self.game_params.get("delta_R", 1.0)

        eta_atk = self.game_params.get("eta_atk", 1.0)
        tau_atk = self.game_params.get("tau_atk", 5)

        invest_other_cost_pct = round(c_inv * 100, 2)
        invest_other_return_pct = round(g_inv * 100, 2)
        arm_cost_pct = round(c_arm * 100, 2)
        arm_other_cost_pct = round(c_arm * 100, 2)
        arm_multiplier = mu_arm
        arm_decay = delta_B
        attack_take_pct = round(alpha * 100, 2)
        conflict_cost_pct = round(c_atk * 100, 2)
        resource_decay_pct = round((1.0 - delta_R) * 100.0, 2)

        symmetric_stakes = self.game_params.get("symmetric_stakes", False)

        actions = []
        saturation_decay = self.game_params.get("gamma_sat", 1.0)
        saturation_window = self.game_params.get("tau_sat", 5)
        invest_desc = (
            f"- invest_other: you pay {invest_other_cost_pct}% of your resources, "
            f"TARGET (must be a connected neighbor) receives {invest_other_return_pct}% "
            f"of your resources. Example: you have 25.0 → you pay "
            f"{25.0 * invest_other_cost_pct / 100:.1f} (left: "
            f"{25.0 * (1 - invest_other_cost_pct / 100):.1f}), target gains "
            f"{25.0 * invest_other_return_pct / 100:.1f}"
        )
        if saturation_decay < 1.0:
            invest_desc += (
                f"\n    DIMINISHING RETURNS: the system tracks a rolling "
                f"{saturation_window}-round window. Each repeat investment in the "
                f"SAME agent within that window reduces the target's gain by "
                f"{(1 - saturation_decay) * 100:.0f}% per repeat. Investing in a "
                f"DIFFERENT agent always gives full returns."
            )
        actions.append(invest_desc)

        if mu_arm > 0:
            arm_cost_ex = 25.0 * arm_cost_pct / 100
            arm_bonus_ex = arm_cost_ex * arm_multiplier
            actions.append(
                f"- arm_self: pay {arm_cost_pct}% of your resources, gain combat "
                f"bonus = cost x {arm_multiplier}. Example: 25.0 resources → pay "
                f"{arm_cost_ex:.1f}, bonus = {arm_bonus_ex:.1f}. Combat strength: "
                f"{25.0 - arm_cost_ex:.1f} + {arm_bonus_ex:.1f} = "
                f"{25.0 - arm_cost_ex + arm_bonus_ex:.1f}"
            )
            actions.append(
                f"- arm_other: you pay {arm_other_cost_pct}% of your resources, "
                f"TARGET (must be a connected neighbor) gains combat bonus = cost x "
                f"{arm_multiplier}. TARGET's resources do NOT increase — only their "
                f"fighting power."
            )

        actions.append(
            f"- attack: TARGET must be a connected neighbor. Both sides pay "
            f"{conflict_cost_pct}% conflict cost. "
            f"Win probability = your combat strength / (your strength + target's strength)."
        )
        actions.append("- do_nothing: no cost, no effect")

        actions_text = "\n".join(actions)

        parts = [f"""Choose exactly ONE action this round.

AVAILABLE ACTIONS:
{actions_text}"""]

        # Resource decay — continuous pressure, stated early so agents know
        # inaction shrinks them before they read the rest.
        if resource_decay_pct > 0:
            decay_ex = 25.0 * resource_decay_pct / 100
            parts.append(
                f"""RESOURCE DECAY:
- Every agent loses {resource_decay_pct}% of their resources at the END of each round.
- Example: 25.0 → lose {decay_ex:.1f}, left with {25.0 - decay_ex:.1f}.
- Doing nothing causes you to shrink. You NEED income (from others investing in you, or from winning attacks) to sustain yourself.
- After 10 rounds of doing nothing: 25.0 → {25.0 * (1 - resource_decay_pct/100)**10:.1f}.
- BANKRUPTCY: if you lose a combat and cannot cover your loss, you forfeit ALL your remaining resources and are eliminated. You can no longer take actions or send messages. Bankruptcy is permanent — you have lost the game."""
            )

        cs_label = "resources + arm bonus" if mu_arm > 0 else "resources"

        if symmetric_stakes:
            combat_spoils = (
                f"THE POT is always {attack_take_pct}% of the DEFENDER's resources, regardless of who wins.\n"
                f"- Attackers win → defender loses the pot; each attacker gains pot × (their strength / total attacker strength).\n"
                f"- Defender wins → each attacker loses an equal share of the pot (pot / number of attackers). "
                f"If an attacker cannot cover their share, they go bankrupt (see above).\n"
                f"- Example (1 vs 1): you attack an agent with 50 resources. "
                f"Pot = {attack_take_pct}% × 50 = {50 * attack_take_pct / 100:.1f}. "
                f"If you win → you gain {50 * attack_take_pct / 100:.1f} (defender loses it). "
                f"If you lose → you lose {50 * attack_take_pct / 100:.1f} (defender gains it).\n"
                f"- Example (3 vs 1): three agents each with 30 attack a target with 100 resources. "
                f"Pot = {attack_take_pct}% × 100 = {100 * attack_take_pct / 100:.1f}. "
                f"If coalition wins → each attacker gains {100 * attack_take_pct / 100 / 3:.1f}. "
                f"If defender wins → each attacker loses {100 * attack_take_pct / 100 / 3:.1f}."
            )
        else:
            combat_spoils = (
                f"Winner takes {attack_take_pct}% of the LOSER's resources.\n"
                f"- Example: you have 10, defender has 50. "
                f"If you win → you gain {50 * attack_take_pct / 100:.1f} (defender loses it). "
                f"If you lose → you lose {10 * attack_take_pct / 100:.1f} (defender gains it)."
            )

        if eta_atk != 1.0:
            cc_at_0 = conflict_cost_pct
            cc_at_1 = round(c_atk * eta_atk * 100, 2)
            cc_at_2 = round(c_atk * (eta_atk ** 2) * 100, 2)
            conflict_cost_line = (
                f"Both sides pay a conflict cost = {conflict_cost_pct}% × {eta_atk}^N, "
                f"where N = attacks made in the last {tau_atk} rounds. "
                f"First attack → {cc_at_0}%. Second → {cc_at_1}%. Third → {cc_at_2}%."
            )
        else:
            conflict_cost_line = (
                f"Both sides pay a flat conflict cost of {conflict_cost_pct}% of their resources."
            )

        arm_decay_line = (
            f"\n- All arm bonuses decay at the END of each round (multiply by {arm_decay})."
            if mu_arm > 0 else ""
        )

        resolution_invest = "Investments" + (" and arming" if mu_arm > 0 else "")
        resolution_strength = f"current resources{' + arm bonus' if mu_arm > 0 else ''}"

        parts.append(f"""COMBAT RULES:
- Combat strength = {cs_label}.{arm_decay_line}
- Win probability = attacker_strength / (attacker_strength + defender_strength).
- {conflict_cost_line}
- {combat_spoils}

COALITIONS (multi-attacker combat):
- If multiple agents attack the same target in the same round, their combat strengths ADD into a coalition vs the defender.
- This is the ONLY way to share spoils from an attack — you must both choose "attack" with the same target, on the same round.
- Investing in an attacker does NOT give you a share of their spoils — only co-attackers share.

RESOLUTION ORDER (each round, after all agents submit actions simultaneously):
1. {resolution_invest} resolve first.
2. Attacks resolve next. Each participant first pays their conflict cost, THEN combat strength is computed as {resolution_strength}.
3. Spoils transfer according to the combat outcome.
4. End-of-round: resource decay applies to everyone (-{resource_decay_pct}% of current resources).{(' Arm bonuses decay (×' + str(arm_decay) + ').') if mu_arm > 0 else ''}""")

        # Network + rewiring grouped together — same mechanism, two knobs.
        rewiring_prob = self.game_params.get("rewiring_prob", 0.0)
        if self.network_enabled:
            network_block = [
                "NETWORK:",
                f"Agents are connected through a network. You can ONLY invest in{', attack, or arm' if mu_arm > 0 else ' or attack'} agents you are directly connected to. You can message any agent regardless of connection.",
                "Connections are symmetric: if you are connected to Blue, then Blue is also connected to you. But each agent has its own set of connections — other agents generally see a different set of neighbours than you do.",
                "Connections can change over time based on how agents interact.",
                "You cannot verify claims about agents whose resources are hidden from you.",
            ]
            if rewiring_prob > 0:
                network_block.append("")
                network_block.append(
                    f"REWIRING: each round, with probability {rewiring_prob:.2f}, the system applies your rewiring nominations. You may nominate at most one neighbour to disconnect from (drop) and at most one agent — neighbour or not — to connect with (invite). Nominations are unilateral: no consent is required from the counterparty."
                )
                network_block.append(
                    "Resolution order: breaks execute first, then connects. Implication: if someone drops you but you invite them back in the same round, the edge is re-added. Using your invite this way costs your connect-slot (you cannot also invite someone new)."
                )
                network_block.append(
                    "Example: you and Blue are connected. Blue nominates drop=you; you nominate invite=Blue. Breaks run → edge severed. Connects run → your invite re-adds the edge. Result: you stay connected, but your connect-slot is used on Blue (no new neighbour added this round)."
                )
            parts.append("\n".join(network_block))

        # Communication rules (if enabled)
        if self.comm_scope != "none":
            comm_lines = [
                "COMMUNICATION:",
                "You may send ONE message this round. Messages reach only your current network neighbours (the agents listed under CONNECTED AGENTS) — you cannot message agents you cannot see. Messages have no resource cost.",
                "",
                "MESSAGE TIMING (important — easy to miscompute):",
                "- Messages CROSS: if you and another agent both write to each other this round, neither of you has read the other's yet — you are both responding to their PREVIOUS round state, not their current plan.",
                "- Messages you RECEIVE this round were sent LAST round (before the sender saw your latest action).",
                "- Messages you SEND this round will be delivered NEXT round — they can influence the recipient's action then, not this round.",
                "- Recipients see whether a message was sent privately (to them only) or broadcast (to all of the sender's neighbours).",
            ]
            if self.comm_scope == "dm":
                comm_lines.append(
                    "You can send a private message to ONE of your neighbours. Only they will see it."
                )
            elif self.comm_scope == "broadcast":
                comm_lines.append(
                    "Your message is sent to all of your current neighbours. Each of them sees it, labelled as broadcast."
                )
            elif self.comm_scope == "choice":
                comm_lines.append(
                    "You choose: send a private message to ONE neighbour, or broadcast to ALL of your current neighbours."
                )
                comm_lines.append(
                    "Set message_to to a specific neighbour agent_id for private, or \"all\" to broadcast to all your neighbours."
                )
            parts.append("\n".join(comm_lines))

        return "\n\n".join(parts)

    def _format_json_template(self) -> str:
        """Build the JSON output schema. Field order: comm → action → target →
        rewire → memory. Memory last so it reflects on a just-decided action.
        """
        rewiring_prob = self.game_params.get("rewiring_prob", 0.0)
        has_rewire = rewiring_prob > 0

        # Assemble fields in the preferred order
        fields: list[str] = []
        if self.comm_scope == "dm":
            fields.append('  "message": "<your message (delivered NEXT round, not this one), or null to stay silent>"')
            fields.append('  "message_to": "<neighbour agent_id, or null>"')
        elif self.comm_scope == "broadcast":
            fields.append('  "message": "<your message to all your neighbours (delivered NEXT round), or empty string to stay silent>"')
        elif self.comm_scope == "choice":
            fields.append('  "message": "<your message (delivered NEXT round), or empty string to stay silent>"')
            fields.append('  "message_to": "<neighbour agent_id for private, or \\"all\\" to broadcast to all your neighbours>"')
        fields.append('  "action": "<one of the action names above>"')
        fields.append('  "target": "<agent_id or null>"')
        if has_rewire:
            fields.append('  "rewire_drop": "<neighbour agent_id to disconnect from, or null>"')
            fields.append('  "rewire_invite": "<any agent_id (including non-neighbours) to connect with, or null>"')
        fields.append('  "memory": "<brief note for your future self — see below>"')

        fields_block = ",\n".join(fields)

        # Per-field notes
        notes: list[str] = [
            'target must be null (not the string "null") when no target is needed.',
        ]
        if self.comm_scope == "dm":
            notes.append(
                "Messaging is optional. To send no message, set both message and "
                "message_to to null. To send a message, message_to must be the "
                "agent_id of one of your current neighbours."
            )
        elif self.comm_scope == "broadcast":
            notes.append(
                "Your message will be seen next round by all of your current "
                "neighbours, labelled as broadcast. Set message to \"\" to send "
                "no message."
            )
        elif self.comm_scope == "choice":
            notes.append(
                "message_to: use a neighbour's agent_id for a private message, "
                "or \"all\" to broadcast to every one of your current "
                "neighbours. Set message to \"\" to send no message."
            )
        notes.append(
            "memory (REQUIRED): a brief note for your future self. Mention what "
            "stood out this round, anything worth remembering, your current "
            "plan, and who you trust or distrust right now. Write freely, in "
            "your own voice. This note will appear alongside future rounds in "
            "your view, so make it legible to yourself later."
        )
        notes.append("Do not include any text outside the JSON.")

        return (
            "OUTPUT (JSON):\n"
            "Your final output MUST be valid JSON with exactly these fields:\n"
            "{\n"
            f"{fields_block}\n"
            "}\n"
            + "\n".join(notes)
        )


def get_prompt_style(prompt_config: Dict,
                     game_params: Optional[Dict] = None) -> BaselinePrompt:
    """Create a BaselinePrompt from config dicts.

    prompt_config keys:
        tom_level: 'level0' | 'level1' | 'level2' | 'level3'  (accepts
                   legacy alias 'reasoning_level').
        hide_resources: bool
    game_params keys (consumed here):
        comm_scope: 'none' | 'dm' | 'broadcast' | 'choice'
    """
    tom_level = prompt_config.get(
        "tom_level", prompt_config.get("reasoning_level", "level0")
    )
    hide_resources = prompt_config.get("hide_resources", False)
    gp = game_params or {}
    comm_scope = gp.get("comm_scope", "none")
    network_enabled = gp.get("network_enabled", gp.get("spatial_enabled", False))
    return BaselinePrompt(
        game_params=game_params,
        tom_level=tom_level,
        hide_resources=hide_resources,
        comm_scope=comm_scope,
        network_enabled=network_enabled,
    )
