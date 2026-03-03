"""
Persistent per-agent memory accumulating observations across rounds.

Each agent maintains:
1. Own action history (sliding window of last N rounds)
2. Per-neighbor observation summaries (accumulated over entire simulation)

Information is local: agents only learn about what they personally observe
or experience. Actions directed at you are always known (you feel the impact),
and your own actions are always known. Third-party actions are only observed
when both actors are in your visibility radius.

Design references:
- Memory stream architecture inspired by Generative Agents (Park et al., 2023),
  simplified for game-theoretic settings: sliding window + per-agent summaries
  instead of retrieval scoring (recency/importance/relevance).
- Local information principle: agents observe only within their visibility radius,
  implementing Harsanyi's (1967-68) incomplete information framework.
  This replaces "god view" neighbor profiles with local observations.
- Memory as IV: no existing game-theory LLM paper uses memory architecture as
  an experimental variable. This is a methodological contribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class NeighborRecord:
    """Accumulated observations about a single neighbor."""
    times_seen: int = 0
    last_seen_round: int = 0
    last_known_resources: float = 0.0
    their_actions_toward_me: Dict[str, int] = field(default_factory=dict)
    my_actions_toward_them: Dict[str, int] = field(default_factory=dict)
    their_actions_general: Dict[str, int] = field(default_factory=dict)
    outcomes: Dict[str, int] = field(default_factory=lambda: {
        "attacks_won": 0, "attacks_lost": 0
    })

    def to_dict(self) -> dict:
        return {
            "times_seen": self.times_seen,
            "last_seen_round": self.last_seen_round,
            "last_known_resources": self.last_known_resources,
            "their_actions_toward_me": dict(self.their_actions_toward_me),
            "my_actions_toward_them": dict(self.my_actions_toward_them),
            "their_actions_general": dict(self.their_actions_general),
            "outcomes": dict(self.outcomes),
        }


class AgentMemory:
    """Persistent per-agent memory accumulating observations across rounds."""

    def __init__(self, agent_id: str, window_size: int = 10):
        self.agent_id = agent_id
        self.window_size = window_size
        self.action_log: List[dict] = []
        self.neighbor_observations: Dict[str, NeighborRecord] = {}

    def _get_or_create_record(self, agent_id: str) -> NeighborRecord:
        if agent_id not in self.neighbor_observations:
            self.neighbor_observations[agent_id] = NeighborRecord()
        return self.neighbor_observations[agent_id]

    def record_action(self, round_num: int, action: str, target: Optional[str],
                      outcome: Optional[dict] = None):
        """Record this agent's own action and its result.

        Args:
            round_num: Current round number.
            action: Action type string (e.g. 'invest_self', 'attack').
            target: Target agent ID or None.
            outcome: Dict with outcome details, e.g.
                     {'resource_change': 2.4} or {'combat_won': True, 'resource_change': 10.0}.
        """
        entry = {
            "round": round_num,
            "action": action,
            "target": target,
            "outcome": outcome or {},
        }
        self.action_log.append(entry)

        # Record in my_actions_toward_them
        if target and target != self.agent_id:
            rec = self._get_or_create_record(target)
            rec.my_actions_toward_them[action] = rec.my_actions_toward_them.get(action, 0) + 1

            # Track combat outcomes
            if action == "attack" and outcome:
                if outcome.get("combat_won"):
                    rec.outcomes["attacks_won"] = rec.outcomes.get("attacks_won", 0) + 1
                elif "combat_won" in outcome:
                    rec.outcomes["attacks_lost"] = rec.outcomes.get("attacks_lost", 0) + 1

    def update_observations(self, round_num: int, visible_agents: Optional[List[str]],
                            round_actions: List[dict], resource_changes: Dict[str, float],
                            combat_results: List[dict], all_resources: Dict[str, float]):
        """Update neighbor observations after a round.

        Called after each round with what this agent could see/experience.

        Args:
            round_num: Current round number.
            visible_agents: List of agent IDs visible this round (None = all visible).
            round_actions: List of action dicts from the round log.
            resource_changes: Per-agent resource changes this round.
            combat_results: List of combat result dicts.
            all_resources: Current resources for all agents (post-round).
        """
        visible_set = set(visible_agents) if visible_agents is not None else None

        # Mark visible agents as seen, update their resources
        agents_to_mark = visible_agents if visible_agents is not None else []
        for aid in agents_to_mark:
            if aid == self.agent_id:
                continue
            rec = self._get_or_create_record(aid)
            rec.times_seen += 1
            rec.last_seen_round = round_num
            if aid in all_resources:
                rec.last_known_resources = all_resources[aid]

        # Process round actions
        for action_entry in round_actions:
            actor = action_entry.get("agent")
            act = action_entry.get("action", "")
            target = action_entry.get("target")

            if act in ("no_action", ""):
                continue

            # Case 1: Actions directed AT me (always known)
            if target == self.agent_id and actor != self.agent_id:
                rec = self._get_or_create_record(actor)
                rec.their_actions_toward_me[act] = rec.their_actions_toward_me.get(act, 0) + 1
                # If actor was not in visible_agents, we still learn about them
                # but only this specific interaction (times_seen not incremented)
                if actor in all_resources:
                    rec.last_known_resources = all_resources[actor]

            # Case 2: Third-party actions (only if both actor and target in radius)
            elif actor != self.agent_id:
                actor_visible = visible_set is None or actor in visible_set
                target_visible = target is None or target == actor or visible_set is None or target in visible_set
                if actor_visible and target_visible:
                    rec = self._get_or_create_record(actor)
                    rec.their_actions_general[act] = rec.their_actions_general.get(act, 0) + 1

        # Process combat results involving me as defender (always known)
        # Coalition format: attackers is a list, winner is "coalition" or "defender"
        for combat in combat_results:
            attackers = combat.get("attackers", [])
            defender = combat.get("defender")
            winner = combat.get("winner")

            if defender == self.agent_id:
                coalition_won = (winner == "coalition")
                for attacker in attackers:
                    if attacker != self.agent_id:
                        rec = self._get_or_create_record(attacker)
                        if coalition_won:
                            rec.outcomes["attacks_won"] = rec.outcomes.get("attacks_won", 0) + 1
                        else:
                            rec.outcomes["attacks_lost"] = rec.outcomes.get("attacks_lost", 0) + 1

    def format_own_history(self) -> str:
        """Format last N actions for the prompt."""
        recent = self.action_log[-self.window_size:]
        if not recent:
            return ""

        lines = ["YOUR RECENT ACTIONS:"]
        for entry in recent:
            action = entry["action"]
            target = entry.get("target")
            outcome = entry.get("outcome", {})

            desc = action
            if target:
                desc += f" -> {target}"

            # Add outcome details
            details = []
            if "combat_won" in outcome and action == "attack":
                details.append("won" if outcome["combat_won"] else "lost")
            rc = outcome.get("resource_change")
            if rc is not None:
                sign = "+" if rc >= 0 else ""
                details.append(f"{sign}{rc:.1f}")

            if details:
                desc += f" ({', '.join(details)})"

            lines.append(f"  Round {entry['round']}: {desc}")

        return "\n".join(lines)

    def format_neighbor_memory(self, currently_visible: Optional[List[str]],
                               current_round: int,
                               hide_resources: bool = False) -> str:
        """Format neighbor observations for the prompt.

        Args:
            currently_visible: Agent IDs visible this round (None = all).
            current_round: Current round number (engine round, i.e. next round to play).
                           Rounds played = current_round - 1.
            hide_resources: If True, show '?' instead of remembered resource values.
        """
        if not self.neighbor_observations:
            return ""

        visible_set = set(currently_visible) if currently_visible is not None else None

        rounds_played = max(current_round - 1, 1)
        lines = ["NEIGHBOR MEMORY:"]

        # Sort: currently visible first, then by last_seen_round descending
        def sort_key(aid_rec):
            aid, rec = aid_rec
            is_visible = visible_set is None or aid in visible_set
            return (not is_visible, -rec.last_seen_round, aid)

        for aid, rec in sorted(self.neighbor_observations.items(), key=sort_key):
            is_visible = visible_set is None or aid in visible_set

            # Build entry
            parts = []

            # Resources and seen count
            if hide_resources:
                res_str = "?"
            else:
                res_str = f"{rec.last_known_resources:.0f}" if rec.times_seen > 0 else "?"
            seen_str = f"seen {rec.times_seen}/{rounds_played} rounds"
            if not is_visible and rec.last_seen_round > 0:
                seen_str += f", last seen round {rec.last_seen_round}"

            header = f"  {aid} [{res_str}, {seen_str}]:"

            # Their actions toward me
            toward_me = []
            for act, count in sorted(rec.their_actions_toward_me.items()):
                label = act.replace("_", " ")
                toward_me.append(f"{label} you {count}x")

            # My actions toward them
            from_me = []
            for act, count in sorted(rec.my_actions_toward_them.items()):
                label = act.replace("_", " ")
                from_me.append(f"you {label} them {count}x")

            # Combine interactions
            interactions = toward_me + from_me
            if interactions:
                parts.append(" | ".join(interactions))
            else:
                parts.append("no interaction with you")

            # Observed general actions (third-party)
            if rec.their_actions_general:
                obs = []
                for act, count in sorted(rec.their_actions_general.items()):
                    label = act.replace("_", " ")
                    obs.append(f"{label} {count}x")
                parts.append("observed: " + ", ".join(obs))

            lines.append(f"{header} {' | '.join(parts)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize for saving with results."""
        return {
            "agent_id": self.agent_id,
            "window_size": self.window_size,
            "action_log": list(self.action_log),
            "neighbor_observations": {
                aid: rec.to_dict()
                for aid, rec in self.neighbor_observations.items()
            },
        }
