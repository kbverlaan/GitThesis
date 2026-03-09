"""
Game engine for multi-agent coordination game.
Handles game state, action resolution, and combat mechanics.

All costs/returns are percentages of the acting agent's current resources.
Arm bonuses are additive (combat strength = resources + arm bonus) and
decay by a configurable factor each round.

Design references:
- Game structure: N-agent resource game with invest/arm/attack actions,
  inspired by Sugarscape (Epstein & Axtell, 1996) and the cooperation-conflict
  dilemma in Axelrod (1984) and Skyrms (2004, Stag Hunt).
- Combat resolution: probabilistic, strength-proportional (Lanchester-type).
  Win probability = attacker_strength / total_strength. Coalition attacks:
  when multiple agents attack the same target, strengths combine (snapshot-based
  simultaneous resolution).
- Arm decay: exponential decay models transient military advantage,
  creating pressure for repeated investment (cf. arms race dynamics,
  Baliga & Sjöström, 2004).
- Parameter space: cost/benefit ratios (theta) determine the cooperation-conflict
  gradient. invest_other_return > invest_other_cost creates a social dilemma:
  cooperation is collectively optimal but individually costly.
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class ActionType(Enum):
    INVEST_SELF = "invest_self"
    INVEST_OTHER = "invest_other"
    ARM_SELF = "arm_self"
    ARM_OTHER = "arm_other"
    ATTACK = "attack"
    DO_NOTHING = "do_nothing"


@dataclass
class Action:
    """Represents a single agent action."""
    agent_id: str
    action_type: ActionType
    target_id: Optional[str] = None  # None for self-actions, agent_id for other-actions


@dataclass
class GameState:
    """Complete game state with resources and history."""
    agents: List[str]
    resources: Dict[str, float]
    round_number: int = 1
    max_rounds: Optional[int] = None
    history: List[Dict] = field(default_factory=list)
    arm_bonuses: Dict[str, float] = field(default_factory=dict)  # agent_id -> combat bonus (decays each round)

    def get_observation(self, agent_id: str, history_length: int = 10) -> Dict:
        """Get complete information observation for an agent."""
        return {
            "agent_id": agent_id,
            "round": self.round_number,
            "max_rounds": self.max_rounds,
            "resources": self.resources.copy(),
            "arm_bonuses": self.arm_bonuses.copy(),
            "recent_history": self.history[-history_length:] if len(self.history) > history_length else self.history.copy()
        }


class GameEngine:
    """Core game engine managing state transitions and action resolution.

    Parameter names match the prompt exactly (see prompts.py _format_actions).
    All costs are percentages of the acting agent's current resources.
    """

    def __init__(self,
                 agent_ids: List[str],
                 initial_resources,  # float (equal) or Dict[str, float] (per-agent)
                 invest_self_pct: float = 2,
                 invest_self_cost_pct: float = None,  # Legacy — ignored if invest_self_pct is set
                 invest_self_return_pct: float = None,  # Legacy — ignored if invest_self_pct is set
                 invest_other_cost_pct: float = 10,
                 invest_other_return_pct: float = 15,
                 arm_cost_pct: float = 10,
                 arm_multiplier: float = 2.0,
                 arm_other_cost_pct: float = None,  # defaults to arm_cost_pct
                 arm_decay: float = 0.5,
                 attack_take_pct: float = 40,
                 conflict_cost_pct: float = 5,
                 resource_decay_pct: float = 0,
                 invest_saturation_decay: float = 1.0,  # 1.0 = no diminishing returns
                 invest_saturation_window: int = 5,
                 max_rounds: int = None,
                 # Legacy params — ignored, kept for backward compat with old configs
                 **kwargs):
        """
        Initialize game engine with parameters.

        All cost/return values are percentages of the acting agent's resources.

        Args:
            agent_ids: List of agent identifiers
            initial_resources: Starting resources (float for equal, dict for per-agent)
            invest_self_pct: flat % gain from invest_self (e.g., 2 = gain 2% of own resources)
            invest_self_cost_pct: Legacy param, ignored if invest_self_pct is set
            invest_self_return_pct: Legacy param, ignored if invest_self_pct is set
            invest_other_cost_pct: % of resources spent on invest_other
            invest_other_return_pct: % of YOUR resources the target receives
                (e.g., 15 means you pay 10%, target gets 15%)
            arm_cost_pct: % of resources spent on arm_self
            arm_multiplier: combat bonus = cost × multiplier (e.g., 2.0 = pay 10, get +20 bonus)
            arm_other_cost_pct: % of resources spent on arm_other (defaults to arm_cost_pct)
            arm_decay: decay factor per round (0.5 = halve each round)
            attack_take_pct: % of loser's resources taken by winner
            conflict_cost_pct: % of own resources each combatant pays
            max_rounds: Maximum number of rounds
        """
        self.max_rounds = max_rounds
        self.params = {
            "invest_self_pct": invest_self_pct,
            "invest_other_cost_pct": invest_other_cost_pct,
            "invest_other_return_pct": invest_other_return_pct,
            "arm_cost_pct": arm_cost_pct,
            "arm_multiplier": arm_multiplier,
            "arm_other_cost_pct": arm_other_cost_pct if arm_other_cost_pct is not None else arm_cost_pct,
            "arm_decay": arm_decay,
            "attack_take_pct": attack_take_pct,
            "conflict_cost_pct": conflict_cost_pct,
            "resource_decay_pct": resource_decay_pct,
            "invest_saturation_decay": invest_saturation_decay,
            "invest_saturation_window": invest_saturation_window,
        }

        if isinstance(initial_resources, dict):
            resources = {aid: initial_resources[aid] for aid in agent_ids}
        else:
            resources = {aid: float(initial_resources) for aid in agent_ids}

        self.state = GameState(
            agents=agent_ids,
            resources=resources,
            max_rounds=max_rounds
        )
        self._valid_targets: Optional[Dict[str, List[str]]] = None

    def set_valid_targets(self, valid_targets: Optional[Dict[str, List[str]]]):
        """Set per-agent valid targets for network-restricted actions.

        Args:
            valid_targets: Dict mapping agent_id -> list of neighbor IDs, or None to disable.
        """
        self._valid_targets = valid_targets

    def _pct(self, agent_id: str, pct_value: float) -> float:
        """Compute pct_value% of agent's current resources."""
        return self.state.resources[agent_id] * (pct_value / 100.0)

    def can_afford_action(self, agent_id: str, action_type: ActionType) -> bool:
        """Check if agent has sufficient resources for action.

        With percentage-based costs, any action is affordable as long as
        resources are above a minimum threshold.
        """
        if action_type == ActionType.DO_NOTHING:
            return True
        return self.state.resources[agent_id] > 0.01

    def resolve_round(self, actions: List[Action]) -> Dict:
        """Resolve all actions for a single round (simultaneous)."""
        round_log = {
            "round": self.state.round_number,
            "actions": [],
            "resource_changes": {},
            "bilateral_flows": defaultdict(float),  # (from, to) -> net resource flow
            "combat_results": [],
            "resource_breakdown": {},  # agent -> {invest_self, invest_received, invest_cost, arm_cost, conflict_cost, combat_transfer, decay}
        }

        # Validate actions
        valid_actions = []
        for action in actions:
            if self.can_afford_action(action.agent_id, action.action_type):
                valid_actions.append(action)
                round_log["actions"].append({
                    "agent": action.agent_id,
                    "action": action.action_type.value,
                    "target": action.target_id
                })
            else:
                round_log["actions"].append({
                    "agent": action.agent_id,
                    "action": "no_action",
                    "reason": "insufficient_resources"
                })

        # Initialize resource changes and breakdown
        for agent_id in self.state.agents:
            round_log["resource_changes"][agent_id] = 0.0
            round_log["resource_breakdown"][agent_id] = {
                "invest_self": 0.0, "invest_received": 0.0, "invest_cost": 0.0,
                "arm_cost": 0.0, "conflict_cost": 0.0, "combat_transfer": 0.0, "decay": 0.0,
            }

        # Process non-attack actions first
        for action in valid_actions:
            if action.action_type == ActionType.DO_NOTHING:
                pass
            elif action.action_type == ActionType.INVEST_SELF:
                self._resolve_invest_self(action, round_log)
            elif action.action_type == ActionType.INVEST_OTHER:
                self._resolve_invest_other(action, round_log)
            elif action.action_type == ActionType.ARM_SELF:
                self._resolve_arm_self(action, round_log)
            elif action.action_type == ActionType.ARM_OTHER:
                self._resolve_arm_other(action, round_log)

        # Process attacks last (after arms are updated) — coalition grouping
        attack_actions = [a for a in valid_actions if a.action_type == ActionType.ATTACK]
        if attack_actions:
            self._resolve_attacks_grouped(attack_actions, round_log)

        # Apply resource changes
        for agent_id, change in round_log["resource_changes"].items():
            self.state.resources[agent_id] = max(0, self.state.resources[agent_id] + change)

        # Resource decay: everyone loses a % of resources each round
        decay_pct = self.params["resource_decay_pct"]
        if decay_pct > 0:
            for agent_id in self.state.agents:
                decay_amount = self.state.resources[agent_id] * (decay_pct / 100.0)
                self.state.resources[agent_id] = max(0, self.state.resources[agent_id] - decay_amount)
                round_log["resource_changes"][agent_id] -= decay_amount
                round_log["resource_breakdown"][agent_id]["decay"] += decay_amount

        # Decay arm bonuses
        self._decay_arms()

        # Add to history and increment round
        self.state.history.append(round_log)
        self.state.round_number += 1

        return round_log

    def _resolve_invest_self(self, action: Action, round_log: Dict):
        """Resolve invest-self action: flat % gain of own resources."""
        agent_id = action.agent_id
        gain = self._pct(agent_id, self.params["invest_self_pct"])
        round_log["resource_changes"][agent_id] += gain
        round_log["resource_breakdown"][agent_id]["invest_self"] += gain

    def _count_recent_investments(self, investor: str, target: str) -> int:
        """Count how many times investor→target occurred in recent history."""
        window = self.params["invest_saturation_window"]
        recent = self.state.history[-window:] if self.state.history else []
        count = 0
        for rd in recent:
            for act in rd.get("actions", []):
                if (act.get("agent") == investor and
                    act.get("action") == "invest_other" and
                    act.get("target") == target):
                    count += 1
        return count

    def _resolve_invest_other(self, action: Action, round_log: Dict):
        """Resolve invest-other action.

        Investor pays invest_other_cost_pct% of own resources (always full cost).
        Target receives invest_other_return_pct% × saturation_decay^prior_investments.
        Diminishing returns per pair — diversification restores full returns.
        """
        agent_id = action.agent_id
        target_id = action.target_id

        if target_id not in self.state.agents:
            return
        # Network restriction: target must be a neighbor
        if self._valid_targets and target_id not in self._valid_targets.get(agent_id, []):
            return

        # Cost is always full (you pay the same regardless of saturation)
        cost = self._pct(agent_id, self.params["invest_other_cost_pct"])
        round_log["resource_changes"][agent_id] -= cost
        round_log["resource_breakdown"][agent_id]["invest_cost"] += cost

        # Return diminishes with repeated investment in same pair
        decay = self.params["invest_saturation_decay"]
        prior = self._count_recent_investments(agent_id, target_id)
        effective_return_pct = self.params["invest_other_return_pct"] * (decay ** prior)
        transfer = self.state.resources[agent_id] * (effective_return_pct / 100.0)

        round_log["resource_changes"][target_id] += transfer
        round_log["resource_breakdown"][target_id]["invest_received"] += transfer
        # Bilateral: agent gave resources to target
        round_log["bilateral_flows"][(agent_id, target_id)] += transfer

    def _resolve_arm_self(self, action: Action, round_log: Dict):
        """Resolve arm-self: pay arm_cost_pct%, gain cost × arm_multiplier as combat bonus."""
        agent_id = action.agent_id
        cost = self._pct(agent_id, self.params["arm_cost_pct"])
        bonus = cost * self.params["arm_multiplier"]
        round_log["resource_changes"][agent_id] -= cost
        round_log["resource_breakdown"][agent_id]["arm_cost"] += cost
        # Add to existing bonus (stacking allowed)
        self.state.arm_bonuses[agent_id] = self.state.arm_bonuses.get(agent_id, 0.0) + bonus

    def _resolve_arm_other(self, action: Action, round_log: Dict):
        """Resolve arm-other: pay arm_other_cost_pct%, target gets cost × arm_multiplier as combat bonus."""
        agent_id = action.agent_id
        target_id = action.target_id

        if target_id not in self.state.agents:
            return
        # Network restriction: target must be a neighbor
        if self._valid_targets and target_id not in self._valid_targets.get(agent_id, []):
            return

        cost = self._pct(agent_id, self.params["arm_other_cost_pct"])
        bonus = cost * self.params["arm_multiplier"]
        round_log["resource_changes"][agent_id] -= cost
        round_log["resource_breakdown"][agent_id]["arm_cost"] += cost
        self.state.arm_bonuses[target_id] = self.state.arm_bonuses.get(target_id, 0.0) + bonus

    def _resolve_attacks_grouped(self, attack_actions: List[Action], round_log: Dict):
        """Group attacks by target and resolve as coalition combats.

        Snapshot-based simultaneous resolution: all combat strengths are frozen
        before any combat resolves, so an agent involved in multiple combats
        (e.g., attacking one target while being attacked by others) uses the
        same strength everywhere. No order dependence.
        """
        # Network restriction: filter out attacks on non-neighbors
        if self._valid_targets:
            attack_actions = [
                a for a in attack_actions
                if a.target_id in self._valid_targets.get(a.agent_id, [])
            ]
            if not attack_actions:
                return

        # Snapshot combat strengths for all agents involved in any attack
        involved = set()
        for action in attack_actions:
            involved.add(action.agent_id)
            involved.add(action.target_id)

        snapshots = {}
        for aid in involved:
            if aid in self.state.agents:
                snapshots[aid] = self.state.resources[aid] + round_log["resource_changes"].get(aid, 0.0) + self.state.arm_bonuses.get(aid, 0.0)

        # Group attacks by target
        attack_map = {}  # attacker → target
        groups = defaultdict(list)  # target → [Action]
        for action in attack_actions:
            if action.target_id in self.state.agents:
                attack_map[action.agent_id] = action.target_id
                groups[action.target_id].append(action)

        # Merge mutual/connected conflicts:
        # If defender D also attacks one of their own attackers, D's attack
        # is absorbed — it's the same fight, not a separate engagement.
        # Process larger groups first (coalition = primary conflict).
        absorbed = set()  # agents whose attack action is absorbed (they're defending)
        for target in sorted(groups.keys(), key=lambda t: len(groups[t]), reverse=True):
            if target in absorbed:
                continue
            attacker_ids = {a.agent_id for a in groups[target]} - absorbed
            if not attacker_ids:
                continue
            if target in attack_map:
                counter_target = attack_map[target]
                if counter_target in attacker_ids:
                    # Defender counter-attacks one of their attackers — same fight
                    absorbed.add(target)

        # Build final groups, filtering out absorbed attackers
        # Note: absorbed agents can still be DEFENDERS — only their attack
        # action is absorbed, not their role as target.
        final_groups = {}
        for target, actions in groups.items():
            remaining = [a for a in actions if a.agent_id not in absorbed]
            if remaining:
                final_groups[target] = remaining

        # Resolve each coalition attack
        for defender_id, attacker_actions in final_groups.items():
            self._resolve_coalition_attack(attacker_actions, defender_id, snapshots, round_log)

    def _resolve_coalition_attack(self, attacker_actions: List[Action],
                                   defender_id: str, snapshots: Dict[str, float],
                                   round_log: Dict):
        """Resolve coalition attack: multiple attackers vs one defender.

        When a single attacker targets the defender, this is equivalent to
        the old 1v1 combat. When multiple attackers target the same defender,
        their combat strengths combine. Spoils are split proportionally.
        """
        attacker_ids = [a.agent_id for a in attacker_actions]

        # Combat strengths from snapshot
        attacker_powers = {aid: snapshots.get(aid, 0.0) for aid in attacker_ids}
        coalition_power = sum(attacker_powers.values())
        defender_power = snapshots.get(defender_id, 0.0)

        # Probabilistic combat resolution (single roll for the group)
        total_power = coalition_power + defender_power
        if total_power > 0:
            attacker_win_prob = coalition_power / total_power
        else:
            attacker_win_prob = 0.5

        coalition_wins = np.random.random() < attacker_win_prob

        # Conflict costs: each participant pays own %
        for aid in attacker_ids:
            cc = self._pct(aid, self.params["conflict_cost_pct"])
            round_log["resource_changes"][aid] -= cc
            round_log["resource_breakdown"][aid]["conflict_cost"] += cc
        def_cc = self._pct(defender_id, self.params["conflict_cost_pct"])
        round_log["resource_changes"][defender_id] -= def_cc
        round_log["resource_breakdown"][defender_id]["conflict_cost"] += def_cc

        # Transfer resources — pot determined by DEFENDER's resources.
        # Pot = take_pct × defender's resources, capped by coalition's total resources.
        # Same pot for both outcomes — winner takes it from loser.
        # This means:
        # - Attacking a small agent: small pot (little to gain or lose)
        # - Attacking a large agent: large pot, but capped by what attackers have
        # - Being big makes you a target (your resources set the stakes)
        # - Coalitions pool resources → higher cap → can challenge big agents
        take_pct = self.params["attack_take_pct"] / 100.0
        total_transfer = 0.0

        defender_effective = max(0, self.state.resources[defender_id] + round_log["resource_changes"][defender_id])
        coalition_effective = sum(
            max(0, self.state.resources[aid] + round_log["resource_changes"][aid])
            for aid in attacker_ids
        )
        max_loss_pct = self.params.get("combat_max_loss_pct", 75) / 100.0
        pot = min(defender_effective * take_pct, coalition_effective * max_loss_pct)  # attackers always keep (1-max_loss)%

        if coalition_wins:
            total_transfer = pot
            round_log["resource_changes"][defender_id] -= total_transfer
            round_log["resource_breakdown"][defender_id]["combat_transfer"] -= total_transfer

            for aid in attacker_ids:
                share = (attacker_powers[aid] / coalition_power) if coalition_power > 0 else (1.0 / len(attacker_ids))
                aid_share = total_transfer * share
                round_log["resource_changes"][aid] += aid_share
                round_log["resource_breakdown"][aid]["combat_transfer"] += aid_share
                round_log["bilateral_flows"][(defender_id, aid)] += aid_share
        else:
            total_transfer = pot
            for aid in attacker_ids:
                share = (attacker_powers[aid] / coalition_power) if coalition_power > 0 else (1.0 / len(attacker_ids))
                aid_loss = total_transfer * share
                round_log["resource_changes"][aid] -= aid_loss
                round_log["resource_breakdown"][aid]["combat_transfer"] -= aid_loss
                round_log["resource_changes"][defender_id] += aid_loss
                round_log["resource_breakdown"][defender_id]["combat_transfer"] += aid_loss
                round_log["bilateral_flows"][(aid, defender_id)] += aid_loss

        round_log["combat_results"].append({
            "attackers": attacker_ids,
            "defender": defender_id,
            "attacker_powers": attacker_powers,
            "coalition_power": coalition_power,
            "defender_power": defender_power,
            "winner": "coalition" if coalition_wins else "defender",
            "attacker_win_prob": attacker_win_prob,
            "total_transfer": total_transfer,
        })

    def _decay_arms(self):
        """Decay all arm bonuses by arm_decay factor. Remove when negligible."""
        decay = self.params["arm_decay"]
        expired = []
        for agent_id in self.state.arm_bonuses:
            self.state.arm_bonuses[agent_id] *= decay
            if self.state.arm_bonuses[agent_id] < 0.01:
                expired.append(agent_id)
        for agent_id in expired:
            del self.state.arm_bonuses[agent_id]

    def resolve_single_action(self, action: Action) -> Dict:
        """Resolve a single action immediately (for sequential mode)."""
        round_log = {
            "actions": [],
            "resource_changes": {},
            "combat_results": []
        }

        for agent_id in self.state.agents:
            round_log["resource_changes"][agent_id] = 0.0

        if self.can_afford_action(action.agent_id, action.action_type):
            round_log["actions"].append({
                "agent": action.agent_id,
                "action": action.action_type.value,
                "target": action.target_id
            })
            if action.action_type == ActionType.DO_NOTHING:
                pass
            elif action.action_type == ActionType.INVEST_SELF:
                self._resolve_invest_self(action, round_log)
            elif action.action_type == ActionType.INVEST_OTHER:
                self._resolve_invest_other(action, round_log)
            elif action.action_type == ActionType.ARM_SELF:
                self._resolve_arm_self(action, round_log)
            elif action.action_type == ActionType.ARM_OTHER:
                self._resolve_arm_other(action, round_log)
            elif action.action_type == ActionType.ATTACK:
                # Sequential mode: single action, so always 1v1 coalition
                self._resolve_attacks_grouped([action], round_log)
        else:
            round_log["actions"].append({
                "agent": action.agent_id,
                "action": "no_action",
                "reason": "insufficient_resources"
            })

        # Apply resource changes immediately
        for agent_id, change in round_log["resource_changes"].items():
            self.state.resources[agent_id] = max(0, self.state.resources[agent_id] + change)

        return round_log

    def tick_arms(self):
        """Decay arm bonuses at end of round (call once per round in sequential mode)."""
        self._decay_arms()

    def advance_round(self, round_log: Dict):
        """Add round to history and increment round number."""
        self.state.history.append(round_log)
        self.state.round_number += 1

    def get_state(self) -> GameState:
        """Get current game state."""
        return self.state

    def is_game_over(self, max_rounds: int) -> bool:
        """Check if game should end."""
        return self.state.round_number > max_rounds
