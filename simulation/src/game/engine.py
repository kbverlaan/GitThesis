"""
Game engine for multi-agent coordination game.
Handles game state, action resolution, and combat mechanics.

All costs/returns are percentages of the acting agent's current resources.
Arm bonuses are additive (combat strength = resources + arm bonus) and
decay by a configurable factor each round.
"""

import numpy as np
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
                 invest_self_cost_pct: float = 10,
                 invest_self_return_pct: float = 20,
                 invest_other_cost_pct: float = 10,
                 invest_other_return_pct: float = 15,
                 arm_cost_pct: float = 10,
                 arm_other_cost_pct: float = None,  # defaults to arm_cost_pct
                 arm_decay: float = 0.5,
                 attack_take_pct: float = 40,
                 conflict_cost_pct: float = 5,
                 max_rounds: int = None,
                 # Legacy params — ignored, kept for backward compat with old configs
                 **kwargs):
        """
        Initialize game engine with parameters.

        All cost/return values are percentages of the acting agent's resources.

        Args:
            agent_ids: List of agent identifiers
            initial_resources: Starting resources (float for equal, dict for per-agent)
            invest_self_cost_pct: % of resources spent on invest_self
            invest_self_return_pct: % of resources gained from invest_self
            invest_other_cost_pct: % of resources spent on invest_other
            invest_other_return_pct: % of YOUR resources the target receives
                (e.g., 15 means you pay 10%, target gets 15%)
            arm_cost_pct: % of resources spent on arm_self (becomes combat bonus)
            arm_other_cost_pct: % of resources spent on arm_other (defaults to arm_cost_pct)
            arm_decay: decay factor per round (0.5 = halve each round)
            attack_take_pct: % of loser's resources taken by winner
            conflict_cost_pct: % of own resources each combatant pays
            max_rounds: Maximum number of rounds
        """
        self.max_rounds = max_rounds
        self.params = {
            "invest_self_cost_pct": invest_self_cost_pct,
            "invest_self_return_pct": invest_self_return_pct,
            "invest_other_cost_pct": invest_other_cost_pct,
            "invest_other_return_pct": invest_other_return_pct,
            "arm_cost_pct": arm_cost_pct,
            "arm_other_cost_pct": arm_other_cost_pct if arm_other_cost_pct is not None else arm_cost_pct,
            "arm_decay": arm_decay,
            "attack_take_pct": attack_take_pct,
            "conflict_cost_pct": conflict_cost_pct,
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
            "combat_results": []
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

        # Initialize resource changes
        for agent_id in self.state.agents:
            round_log["resource_changes"][agent_id] = 0.0

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

        # Process attacks last (after arms are updated)
        for action in valid_actions:
            if action.action_type == ActionType.ATTACK:
                self._resolve_attack(action, round_log)

        # Apply resource changes
        for agent_id, change in round_log["resource_changes"].items():
            self.state.resources[agent_id] = max(0, self.state.resources[agent_id] + change)

        # Decay arm bonuses
        self._decay_arms()

        # Add to history and increment round
        self.state.history.append(round_log)
        self.state.round_number += 1

        return round_log

    def _resolve_invest_self(self, action: Action, round_log: Dict):
        """Resolve invest-self action: pay cost%, gain return%."""
        agent_id = action.agent_id
        round_log["resource_changes"][agent_id] -= self._pct(agent_id, self.params["invest_self_cost_pct"])
        round_log["resource_changes"][agent_id] += self._pct(agent_id, self.params["invest_self_return_pct"])

    def _resolve_invest_other(self, action: Action, round_log: Dict):
        """Resolve invest-other action.

        Investor pays invest_other_cost_pct% of own resources.
        Target receives invest_other_return_pct% of investor's resources.
        """
        agent_id = action.agent_id
        target_id = action.target_id

        if target_id not in self.state.agents:
            return

        round_log["resource_changes"][agent_id] -= self._pct(agent_id, self.params["invest_other_cost_pct"])
        round_log["resource_changes"][target_id] += self._pct(agent_id, self.params["invest_other_return_pct"])

    def _resolve_arm_self(self, action: Action, round_log: Dict):
        """Resolve arm-self: pay arm_cost_pct%, that amount becomes combat bonus."""
        agent_id = action.agent_id
        bonus = self._pct(agent_id, self.params["arm_cost_pct"])
        round_log["resource_changes"][agent_id] -= bonus
        # Add to existing bonus (stacking allowed)
        self.state.arm_bonuses[agent_id] = self.state.arm_bonuses.get(agent_id, 0.0) + bonus

    def _resolve_arm_other(self, action: Action, round_log: Dict):
        """Resolve arm-other: pay arm_other_cost_pct%, that amount becomes TARGET's combat bonus."""
        agent_id = action.agent_id
        target_id = action.target_id

        if target_id not in self.state.agents:
            return

        bonus = self._pct(agent_id, self.params["arm_other_cost_pct"])
        round_log["resource_changes"][agent_id] -= bonus
        self.state.arm_bonuses[target_id] = self.state.arm_bonuses.get(target_id, 0.0) + bonus

    def _resolve_attack(self, action: Action, round_log: Dict):
        """Resolve attack: probabilistic combat based on strength = resources + arm bonus."""
        attacker_id = action.agent_id
        defender_id = action.target_id

        if defender_id not in self.state.agents:
            return

        # Combat strength = resources + arm bonus (additive)
        attacker_power = self.state.resources[attacker_id] + self.state.arm_bonuses.get(attacker_id, 0.0)
        defender_power = self.state.resources[defender_id] + self.state.arm_bonuses.get(defender_id, 0.0)

        # Probabilistic combat resolution
        total_power = attacker_power + defender_power
        if total_power > 0:
            attacker_win_prob = attacker_power / total_power
        else:
            attacker_win_prob = 0.5

        attacker_wins = np.random.random() < attacker_win_prob

        # Apply conflict costs (each fighter pays own %)
        round_log["resource_changes"][attacker_id] -= self._pct(attacker_id, self.params["conflict_cost_pct"])
        round_log["resource_changes"][defender_id] -= self._pct(defender_id, self.params["conflict_cost_pct"])

        # Transfer resources
        take_pct = self.params["attack_take_pct"] / 100.0
        if attacker_wins:
            defender_resources = self.state.resources[defender_id] + round_log["resource_changes"][defender_id]
            transfer = defender_resources * take_pct
            round_log["resource_changes"][defender_id] -= transfer
            round_log["resource_changes"][attacker_id] += transfer
            winner = attacker_id
        else:
            attacker_resources = self.state.resources[attacker_id] + round_log["resource_changes"][attacker_id]
            transfer = attacker_resources * take_pct
            round_log["resource_changes"][attacker_id] -= transfer
            round_log["resource_changes"][defender_id] += transfer
            winner = defender_id

        round_log["combat_results"].append({
            "attacker": attacker_id,
            "defender": defender_id,
            "attacker_power": attacker_power,
            "defender_power": defender_power,
            "winner": winner,
            "attacker_win_prob": attacker_win_prob
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
                self._resolve_attack(action, round_log)
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
