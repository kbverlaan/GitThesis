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
    messages_received: int = 0   # Count of messages received from this neighbor
    messages_sent: int = 0       # Count of messages sent to this neighbor
    last_message_from: str = ""  # Last message text received from this neighbor

    def to_dict(self) -> dict:
        return {
            "times_seen": self.times_seen,
            "last_seen_round": self.last_seen_round,
            "last_known_resources": self.last_known_resources,
            "their_actions_toward_me": dict(self.their_actions_toward_me),
            "my_actions_toward_them": dict(self.my_actions_toward_them),
            "their_actions_general": dict(self.their_actions_general),
            "outcomes": dict(self.outcomes),
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'NeighborRecord':
        rec = cls()
        rec.times_seen = d.get("times_seen", 0)
        rec.last_seen_round = d.get("last_seen_round", 0)
        rec.last_known_resources = d.get("last_known_resources", 0.0)
        rec.their_actions_toward_me = dict(d.get("their_actions_toward_me", {}))
        rec.my_actions_toward_them = dict(d.get("my_actions_toward_them", {}))
        rec.their_actions_general = dict(d.get("their_actions_general", {}))
        rec.outcomes = dict(d.get("outcomes", {}))
        rec.messages_received = d.get("messages_received", 0)
        rec.messages_sent = d.get("messages_sent", 0)
        rec.last_message_from = d.get("last_message_from", "")
        return rec


class AgentMemory:
    """Persistent per-agent memory accumulating observations across rounds."""

    def __init__(self, agent_id: str, window_size: int = 10):
        self.agent_id = agent_id
        self.window_size = window_size
        self.action_log: List[dict] = []
        self.neighbor_observations: Dict[str, NeighborRecord] = {}
        self.note_to_self: Optional[str] = None  # Private strategic note persisted across rounds
        self.message_log: List[dict] = []  # Sliding window of sent/received messages
        self.last_round_incoming: List[dict] = []  # Actions directed at me last round

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

        # Track incoming actions this round (overwrite previous round)
        self.last_round_incoming = []

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
                # Store for per-round display
                self.last_round_incoming.append({
                    'actor': actor, 'action': act, 'round': round_num,
                })

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

    def record_messages(self, sent_message: Optional[dict],
                        received_messages: List[dict],
                        round_num: int = 0):
        """Record sent and received messages.

        Args:
            sent_message: This agent's message dict (from/message/message_to) or None.
            received_messages: List of message dicts received this round.
            round_num: Current round number (for message log).
        """
        # Track sent message
        if sent_message and sent_message.get('message'):
            msg_to = sent_message.get('message_to')
            if msg_to and msg_to != 'all':
                rec = self._get_or_create_record(msg_to)
                rec.messages_sent += 1
            # Add to message log
            self.message_log.append({
                'round': round_num,
                'dir': 'sent',
                'to': msg_to,
                'text': sent_message['message'][:200],
            })

        # Track received messages
        for msg in received_messages:
            sender = msg.get('from')
            if sender and sender != self.agent_id:
                rec = self._get_or_create_record(sender)
                rec.messages_received += 1
                rec.last_message_from = msg.get('message', '')
            # Add to message log
            self.message_log.append({
                'round': round_num,
                'dir': 'received',
                'from': msg.get('from', '?'),
                'text': msg.get('message', '')[:200],
            })

        # Keep sliding window
        self.message_log = self.message_log[-self.window_size:]

    def record_note(self, note: Optional[str]):
        """Store a private note-to-self for next round.

        Agents write these to persist long-term plans, alliance tracking,
        threat assessments, or strategic reasoning across rounds. Truncated
        to 1000 characters to bound prompt size.
        """
        if note and isinstance(note, str):
            self.note_to_self = note[:1000]
        else:
            self.note_to_self = None

    def format_note(self) -> str:
        """Format the current note-to-self for prompt injection."""
        if not self.note_to_self:
            return ""
        return f"YOUR STRATEGIC NOTEBOOK (from last round):\n{self.note_to_self}"

    def format_message_history(self) -> str:
        """Format recent message log for prompt injection."""
        if not self.message_log:
            return ""
        lines = ["RECENT MESSAGES:"]
        for m in self.message_log:
            rnd = m.get('round', '?')
            if m['dir'] == 'sent':
                lines.append(f"  Round {rnd}: You → {m.get('to', '?')}: \"{m['text']}\"")
            else:
                lines.append(f"  Round {rnd}: {m.get('from', '?')} → You: \"{m['text']}\"")
        return "\n".join(lines)

    def format_incoming_actions(self) -> str:
        """Format actions directed at this agent last round."""
        if not self.last_round_incoming:
            return ""
        rnd = self.last_round_incoming[0]['round']
        lines = [f"ACTIONS RECEIVED LAST ROUND (round {rnd}):"]
        for entry in self.last_round_incoming:
            act = entry['action'].replace('_', ' ')
            lines.append(f"  {entry['actor']} → {act} → you")
        return "\n".join(lines)

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
                # Only show resource change for attacks (won/lost context makes it clear)
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

            # Resources
            if hide_resources:
                res_str = "?"
            elif not is_visible and rec.times_seen > 0:
                rounds_stale = rounds_played - rec.last_seen_round
                if rounds_stale > 0:
                    res_str = f"was {rec.last_known_resources:.0f} at R{rec.last_seen_round}"
                else:
                    res_str = f"{rec.last_known_resources:.0f}"
            else:
                res_str = f"{rec.last_known_resources:.0f}" if rec.times_seen > 0 else "?"

            # Visibility status
            if not is_visible and rec.last_seen_round > 0:
                vis_str = f"hidden, last seen R{rec.last_seen_round}"
            elif not is_visible:
                vis_str = "hidden"
            else:
                vis_str = "visible"

            lines.append(f"  {aid} [{res_str}, {vis_str}]:")

            # Their actions toward me (most important — show first)
            toward_me = []
            for act, count in sorted(rec.their_actions_toward_me.items()):
                toward_me.append(f"{act.replace('_', ' ')} you {count}x")
            if toward_me:
                lines.append(f"    Toward you: {', '.join(toward_me)}")

            # My actions toward them
            from_me = []
            for act, count in sorted(rec.my_actions_toward_them.items()):
                from_me.append(f"{act.replace('_', ' ')} {count}x")
            if from_me:
                lines.append(f"    You toward them: {', '.join(from_me)}")

            # Combat record (if any)
            won = rec.outcomes.get("attacks_won", 0)
            lost = rec.outcomes.get("attacks_lost", 0)
            if won or lost:
                lines.append(f"    Combat record: {won}W {lost}L")

            # Message activity
            if rec.messages_received or rec.messages_sent:
                lines.append(f"    Messages: {rec.messages_received} received, {rec.messages_sent} sent")

            # If no interaction at all
            if not toward_me and not from_me and not won and not lost and not rec.messages_received and not rec.messages_sent:
                lines.append(f"    No interaction")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize for saving with results."""
        return {
            "agent_id": self.agent_id,
            "window_size": self.window_size,
            "action_log": list(self.action_log),
            "message_log": list(self.message_log),
            "note_to_self": self.note_to_self,
            "last_round_incoming": list(self.last_round_incoming),
            "neighbor_observations": {
                aid: rec.to_dict()
                for aid, rec in self.neighbor_observations.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'AgentMemory':
        """Restore from serialized dict (for resume)."""
        mem = cls(d["agent_id"], d.get("window_size", 10))
        mem.action_log = list(d.get("action_log", []))
        mem.message_log = list(d.get("message_log", []))
        mem.note_to_self = d.get("note_to_self")
        mem.last_round_incoming = list(d.get("last_round_incoming", []))
        for aid, rec_dict in d.get("neighbor_observations", {}).items():
            mem.neighbor_observations[aid] = NeighborRecord.from_dict(rec_dict)
        return mem
