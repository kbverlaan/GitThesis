"""
Prompt harness for LLM agents.

A single baseline prompt drives all conditions. The experimental axis is
mechanics complexity (the complexity ladder); memory and communication are a
fixed base substrate. Reasoning style (the ToM blocks below) is held CONSTANT,
not manipulated — it is part of the substrate, not the IV. Feature flags
(communication scope, rewiring, hide_resources) are driven by game_params.

Design references:
- ToM blocks L0-L3 per de Weerd et al. (2013, 2017, 2022): depth of
  MENTAL-STATE modelling (beliefs, desires, intentions), not K-level
  action-forecasting. Retained as a selectable but fixed reasoning baseline
  (default level0); earlier work found reasoning-depth effects unreliable, so
  it is no longer a manipulated axis.
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


# Minimal recursive-ToM nudge (a chain-of-thought aid), held CONSTANT across all
# rungs — part of the substrate, NOT an experimental IV. Kept lean and free of
# outcome priming: it points at reasoning one step ahead about others, without
# anthropomorphism or any steer toward cooperation/conflict.
SOCIAL_SETTING = (
    "The other agents decide on their own and can observe what you do. When you "
    "choose, it can help to think a step ahead: what each relevant agent is likely "
    "to want and do, that they are reasoning about you in the same way, and that "
    "your own actions and messages become information they will act on."
)


class BaselinePrompt:
    """Single baseline prompt. Mechanics complexity is the experimental axis;
    the recursive theory-of-mind framing (SOCIAL_SETTING) is a fixed, neutral
    part of the substrate — no outcome priming — not an IV."""

    OBJECTIVE = "Maximize your absolute resource count."

    def __init__(self, game_params: Optional[Dict] = None,
                 hide_resources: bool = False,
                 comm_scope: str = "none",
                 network_enabled: bool = True):
        self.game_params = game_params or {}
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

        # 2. Memory (recent rounds)
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
        take_on = self.game_params.get("take_enabled", True)

        lines.append("")
        if not take_on:
            lines.append("AGENTS (resources):")
        elif show_arm:
            lines.append("AGENTS (resources + arm bonus = combat strength):")
        else:
            lines.append("AGENTS (resources = combat strength):")

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

        commons = observation.get("commons")
        if commons:
            lines.append("")
            if commons.get("collapsed"):
                lines.append("SHARED STOCK: COLLAPSED (0% — permanently depleted, nothing left to harvest).")
            else:
                lines.append(f"SHARED STOCK: {commons['stock_pct']:.0f}% of capacity.")
            last = commons.get("last_harvests_pct") or {}
            if last:
                parts_h = ", ".join(
                    f"{a} {p:.0f}%" for a, p in sorted(last.items(), key=lambda kv: -kv[1])
                )
                lines.append(f"  Harvests last round (% of capacity): {parts_h}")

        received_messages = observation.get("received_messages", [])
        if received_messages:
            lines.append("")
            lines.append("INCOMING MESSAGES (sent to you LAST round — your reply arrives NEXT round):")
            for msg in received_messages:
                sender = msg.get("from", "?")
                text = msg.get("message", "")
                n = int(msg.get("n_recipients", 1) or 1)
                scope = "to you only" if n <= 1 else f"to you + {n - 1} others"
                lines.append(f"  {sender} ({scope}): {text}")

        return "\n".join(lines)

    def _format_intro(self) -> str:
        n_agents = self.game_params.get("num_agents", 30)
        rewiring_on = self.game_params.get("rewiring_prob", 0.0) > 0
        comm_on = self.comm_scope != "none"
        decay_on = self.game_params.get("delta_R", 1.0) < 1.0
        commons_on = self.game_params.get("commons_enabled", False)

        # List only the rule-blocks that are actually rendered for this config.
        rules_items = ["available actions"]
        if decay_on:
            rules_items.append("resource decay")
        rules_items.append("combat (incl. coalitions)")
        if self.network_enabled:
            rules_items.append("network and rewiring" if rewiring_on else "the network")
        if comm_on:
            rules_items.append("communication")
        if commons_on:
            rules_items.append("the shared stock")
        rules_summary = ", ".join(rules_items)

        return (
            f"INTRODUCTION:\n"
            f"You are one of {n_agents} agents playing a repeated multi-agent "
            f"game. You will receive a new prompt like this every round. The "
            f"sections below appear in this order:\n"
            f"  1. Game rules — {rules_summary}.\n"
            f"  2. The other agents — how to reason about them.\n"
            f"  3. Identity — who you are and your objective.\n"
            f"  4. Your memory — your own notes (kept across the whole game) plus detailed events from recent rounds.\n"
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
        take_enabled = self.game_params.get("take_enabled", True)

        actions = []
        saturation_decay = self.game_params.get("gamma_sat", 1.0)
        saturation_window = self.game_params.get("tau_sat", 5)
        invest_desc = (
            f"- transfer: you pay {invest_other_cost_pct}% of your resources, "
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
                f"- strengthen: you pay {arm_other_cost_pct}% of your resources, "
                f"TARGET (must be a connected neighbor) gains combat bonus = cost x "
                f"{arm_multiplier}. TARGET's resources do NOT increase — only their "
                f"fighting power. Example: you have 25.0 → you pay {arm_cost_ex:.1f}, "
                f"target gains {arm_bonus_ex:.1f} combat bonus. You CANNOT arm "
                f"yourself — combat strength can only be raised by others arming you."
            )

        if take_enabled:
            actions.append(
                f"- take: TARGET must be a connected neighbor. Both sides pay "
                f"{conflict_cost_pct}% conflict cost. "
                f"Win probability = your combat strength / (your strength + target's strength)."
            )
        actions.append("- hold: no cost, no effect")

        actions_text = "\n".join(actions)

        commons_on = self.game_params.get("commons_enabled", False)
        harvest_aside = (
            " (Harvesting from the shared stock is separate and does NOT use up "
            "your action — see SHARED STOCK below.)" if commons_on else ""
        )
        parts = [f"""Choose exactly ONE action this round.{harvest_aside}

AVAILABLE ACTIONS:
{actions_text}"""]

        # Resource decay — continuous pressure, stated early so agents know
        # inaction shrinks them before they read the rest.
        if resource_decay_pct > 0:
            decay_ex = 25.0 * resource_decay_pct / 100
            parts.append(
                f"""RESOURCE DECAY:
- Every agent loses {resource_decay_pct}% of their resources at the END of each round.
- Example: 25.0 → lose {decay_ex:.1f}, left with {25.0 - decay_ex:.1f}."""
            )

        cs_label = "resources + arm bonus" if mu_arm > 0 else "resources"

        lethal_pot = self.game_params.get("lethal_pot", False)
        inv_alpha = (1.0 / alpha) if alpha > 0 else 99.0
        kill_ratio = round(inv_alpha, 1)
        kill_n = int(inv_alpha) + (0 if inv_alpha == int(inv_alpha) else 1)
        if lethal_pot:
            combat_spoils = (
                f"Winner takes a fraction of the LOSER's resources that SCALES with the strength gap.\n"
                f"- Fraction taken = min(100%, {attack_take_pct}% × winner_strength ÷ loser_strength). "
                f"At equal strength it is {attack_take_pct}%; the more you outmatch the loser, the larger your cut.\n"
                f"- KILL: if the winner's strength is at least {kill_ratio}× the loser's, the fraction reaches 100% — "
                f"the loser is drained to zero and ELIMINATED (permanent, see bankruptcy).\n"
                f"- This is SYMMETRIC and also applies to YOU: if you attack and LOSE, the defender takes "
                f"min(100%, {attack_take_pct}% × defender_strength ÷ your_strength) of your resources. "
                f"A far stronger defender can wipe you out for attacking.\n"
                f"- Example (1 vs 1, both 100): win → take {100*alpha:.0f}; lose → give up {100*alpha:.0f}.\n"
                f"- Example (you 100 vs target 30, ratio 3.3 ≥ {kill_ratio}): you take ALL 30 → target eliminated.\n"
                f"- Example (you 30 attack a 100 and lose): they take 100% of your 30 → YOU are eliminated.\n"
                f"- Coalition: attacker strengths ADD; a coalition at least {kill_ratio}× the defender's strength "
                f"kills it (spoils split by each attacker's strength share). With equal-sized members, "
                f"{kill_n} of them are enough to kill."
            )
        elif symmetric_stakes:
            combat_spoils = (
                f"THE POT is always {attack_take_pct}% of the DEFENDER's resources, regardless of who wins.\n"
                f"- Attackers win → defender loses the pot; each attacker gains pot × (their strength / total attacker strength).\n"
                f"- Defender wins → each attacker loses an equal share of the pot (pot / number of attackers). "
                f"If an attacker cannot cover their share, they go bankrupt (see above).\n"
                f"- Example (1 vs 1): you take from an agent with 50 resources. "
                f"Pot = {attack_take_pct}% × 50 = {50 * attack_take_pct / 100:.1f}. "
                f"If you win → you gain {50 * attack_take_pct / 100:.1f} (defender loses it). "
                f"If you lose → you lose {50 * attack_take_pct / 100:.1f} (defender gains it).\n"
                f"- Example (3 vs 1): three agents each with 30 take from a target with 100 resources. "
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

        # Combat rules only exist when taking is available (rung ≥ predation).
        if take_enabled:
            parts.append(f"""COMBAT RULES:
- Combat strength = {cs_label}.{arm_decay_line}
- Win probability = attacker_strength / (attacker_strength + defender_strength).
- {conflict_cost_line}
- {combat_spoils}
- BANKRUPTCY: if you lose a combat and cannot cover what you owe, you forfeit ALL your remaining resources and are eliminated — permanently, no longer able to act or send messages.

COALITIONS (multi-attacker combat):
- If multiple agents attack the same target in the same round, their combat strengths ADD into a coalition vs the defender.
- This is the ONLY way to share spoils from a take — you must both choose "take" with the same target, on the same round.
- Investing in an attacker does NOT give you a share of their spoils — only co-attackers share.""")

        # Resolution order — always shown; attack/spoils steps only when taking
        # is available, harvest/regeneration steps only when the commons is on.
        steps = [f"{1}. {resolution_invest} resolve first."]
        if take_enabled:
            steps.append(f"{len(steps) + 1}. Attacks resolve next. Each participant first pays their conflict cost, THEN combat strength is computed as {resolution_strength}.")
            steps.append(f"{len(steps) + 1}. Spoils transfer according to the combat outcome.")
        if commons_on:
            steps.append(f"{len(steps) + 1}. Harvests from the shared stock are taken and added to your resources.")
        eor = f"{len(steps) + 1}. End-of-round: resource decay applies to everyone (-{resource_decay_pct}% of current resources)."
        if mu_arm > 0:
            eor += f" Arm bonuses decay (×{arm_decay})."
        if commons_on:
            eor += " The shared stock then regenerates (whatever remains doubles, capped at capacity)."
        steps.append(eor)
        parts.append("RESOLUTION ORDER (each round, after all agents submit actions simultaneously):\n" + "\n".join(steps))

        # Network + rewiring grouped together — same mechanism, two knobs.
        rewiring_prob = self.game_params.get("rewiring_prob", 0.0)
        if self.network_enabled:
            nb_verbs = ["transfer to"]
            if take_enabled:
                nb_verbs.append("take from")
            if mu_arm > 0:
                nb_verbs.append("strengthen")
            if len(nb_verbs) == 1:
                nb_phrase = nb_verbs[0]
            elif len(nb_verbs) == 2:
                nb_phrase = f"{nb_verbs[0]} or {nb_verbs[1]}"
            else:
                nb_phrase = ", ".join(nb_verbs[:-1]) + ", or " + nb_verbs[-1]
            network_block = [
                "NETWORK:",
                f"Agents are connected through a network. You can ONLY {nb_phrase} agents you are directly connected to. You can message any agent regardless of connection.",
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

        # Communication rules (if enabled). Language is decoupled from the
        # 1-hop action graph: address anyone you know of, by listing their ids.
        if self.comm_scope != "none":
            comm_lines = [
                "COMMUNICATION:",
                "You may send ONE message this round, addressed to one or more agents. List the recipients' agent_ids in message_to. Messages have no resource cost.",
                "You can message any agent you KNOW OF — not only your network neighbours. You come to know an agent by being connected to them, by receiving a message from them, or by seeing them act. There is NO global directory: you can only reach agents whose id you have learned. To reach several agents at once, list several ids.",
                "",
                "MESSAGE TIMING (important — easy to miscompute):",
                "- Messages CROSS: if you and another agent both write to each other this round, neither of you has read the other's yet — you are both responding to their PREVIOUS round state, not their current plan.",
                "- Messages you RECEIVE this round were sent LAST round (before the sender saw your latest action).",
                "- Messages you SEND this round will be delivered NEXT round — they can influence the recipient's action then, not this round.",
                "- Each recipient sees how many others also received the message (whether it was for them only, or sent more widely) — but not the full recipient list.",
            ]
            parts.append("\n".join(comm_lines))

        # Commons rules (if enabled). One shared stock all agents draw from; the
        # level is shown as a % of capacity (the absolute capacity is never stated).
        if self.game_params.get("commons_enabled", False):
            cats = self.game_params.get("commons_harvest_pct", [0, 1, 2, 4, 8])
            cat_str = ", ".join(f"{c:g}%" for c in cats)
            commons_lines = [
                "SHARED STOCK:",
                "Beyond your dealings with other agents, there is ONE shared stock that "
                "everyone draws from. Its level is shown to you as a PERCENTAGE of its full capacity.",
                f"- HARVEST: each round you may take one of these amounts from it: {cat_str} of capacity. "
                "What you take is added to YOUR own resources, in absolute units.",
                "- Everyone harvests simultaneously, and at the END of each round every agent's harvest is revealed to all.",
                "- If the combined harvest is more than what is left, the remaining stock is split at random among the claimants until it runs out.",
                "- REGENERATION: at the end of each round whatever remains DOUBLES, up to full capacity. Much left → it refills; little left → it can only double a little.",
                "- COLLAPSE: if the stock falls too low it collapses permanently — it stays empty and nobody can harvest for the rest of the game.",
            ]
            parts.append("\n".join(commons_lines))

        parts.append("OTHER AGENTS:\n" + SOCIAL_SETTING)
        return "\n\n".join(parts)

    def _format_json_template(self) -> str:
        """Build the JSON output schema. Field order: comm → action → target →
        rewire → memory. Memory last so it reflects on a just-decided action.
        """
        rewiring_prob = self.game_params.get("rewiring_prob", 0.0)
        has_rewire = rewiring_prob > 0
        commons_enabled = self.game_params.get("commons_enabled", False)
        cats = self.game_params.get("commons_harvest_pct", [0, 1, 2, 4, 8])
        cat_str = "/".join(f"{c:g}" for c in cats)

        # Assemble fields in the preferred order
        fields: list[str] = []
        if self.comm_scope != "none":
            fields.append('  "message": "<your message (delivered NEXT round, not this one), or null to stay silent>"')
            fields.append('  "message_to": "<list of recipient agent_ids you know of, e.g. [\\"Red\\", \\"Blue\\"]; or null to stay silent>"')
        fields.append('  "action": "<one of the action names above>"')
        fields.append('  "target": "<agent_id or null>"')
        if has_rewire:
            fields.append('  "rewire_drop": "<neighbour agent_id to disconnect from, or null>"')
            fields.append('  "rewire_invite": "<any agent_id (including non-neighbours) to connect with, or null>"')
        if commons_enabled:
            fields.append(f'  "harvest": "<how much of the shared stock to take this round: one of {cat_str} (percent of capacity); 0 for none>"')
        fields.append('  "memory": "<brief note for your future self — see below>"')

        fields_block = ",\n".join(fields)

        # Per-field notes
        notes: list[str] = [
            'target must be null (not the string "null") when no target is needed.',
        ]
        if commons_enabled:
            notes.append(
                "harvest: the percent of the shared stock you take this round — one of "
                f"the listed values ({cat_str}). Use 0 to take nothing. This is separate "
                "from your action: you may both act and harvest in the same round."
            )
        if self.comm_scope != "none":
            notes.append(
                "message_to: a list of the agent_ids you are sending to (one or "
                "more). You can only name agents you know of — your neighbours, "
                "anyone who has messaged you, or anyone you have seen act. There "
                "is no \"all\" shortcut: to reach many agents, list their ids. "
                "Messaging is optional — set message to null to stay silent."
            )
        notes.append(
            "memory (REQUIRED): a note for your future self. Your detailed view "
            "of actions and messages only reaches back a few rounds, but THIS "
            "note is kept for the rest of the game — so it is your lasting "
            "record. Capture what mattered this round AND refresh your running "
            "understanding: any standing agreements or arrangements, recurring "
            "patterns you have noticed, your current plan, and who you trust or "
            "distrust right now. Write freely, in your own voice, and make it "
            "legible to yourself many rounds from now."
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
        hide_resources: bool
    game_params keys (consumed here):
        comm_scope: 'none' (off) | any other value (on). Communication uses a
            single mechanism: a message with an explicit list of target ids
            (no broadcast channel). Legacy values dm/broadcast/choice all map
            to "on".
    """
    hide_resources = prompt_config.get("hide_resources", False)
    gp = game_params or {}
    comm_scope = gp.get("comm_scope", "none")
    network_enabled = gp.get("network_enabled", gp.get("spatial_enabled", False))
    return BaselinePrompt(
        game_params=game_params,
        hide_resources=hide_resources,
        comm_scope=comm_scope,
        network_enabled=network_enabled,
    )
