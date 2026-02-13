"""
Game engine for multi-agent coordination game.
Handles game state, action resolution, and combat mechanics.
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
    active_arms: Dict[str, int] = field(default_factory=dict)  # agent_id -> rounds remaining (from arm_self)
    arm_coalitions: Dict[str, Dict[str, int]] = field(default_factory=dict)  # target_id -> {supporter_id: rounds_remaining}
    
    def get_observation(self, agent_id: str, history_length: int = 10) -> Dict:
        """Get complete information observation for an agent."""
        return {
            "agent_id": agent_id,
            "round": self.round_number,
            "max_rounds": self.max_rounds,
            "resources": self.resources.copy(),
            "active_arms": self.active_arms.copy(),
            "arm_coalitions": {k: v.copy() for k, v in self.arm_coalitions.items()},
            "recent_history": self.history[-history_length:] if len(self.history) > history_length else self.history.copy()
        }


class GameEngine:
    """Core game engine managing state transitions and action resolution."""
    
    def __init__(self, 
                 agent_ids: List[str],
                 initial_resources: float,
                 invest_self_cost: float,
                 invest_self_return: float,
                 invest_other_cost: float,
                 invest_other_return: float,
                 arm_cost: float,
                 arm_multiplier: float,
                 arm_duration: int,
                 arm_other_contribution: float,
                 arm_other_duration: int,
                 attack_take_percent: float,
                 conflict_cost: float,
                 max_rounds: int = None):
        """
        Initialize game engine with parameters.
        
        Args:
            agent_ids: List of agent identifiers
            initial_resources: Starting resources for each agent
            invest_self_cost: Cost for invest_self action
            invest_self_return: Return from invest_self action
            invest_other_cost: Cost for invest_other action
            invest_other_return: Return for target from invest_other action
            arm_cost: Cost D for arm actions
            arm_multiplier: Power multiplier M when armed
            arm_duration: Rounds that arm effect lasts
            attack_take_percent: Percentage T of loser's resources winner takes
            conflict_cost: Cost C paid by all combatants in attack
            max_rounds: Maximum number of rounds (None = unknown to agents)
        """
        self.max_rounds = max_rounds
        self.params = {
            "invest_self_cost": invest_self_cost,
            "invest_self_return": invest_self_return,
            "invest_other_cost": invest_other_cost,
            "invest_other_return": invest_other_return,
            "arm_cost": arm_cost,
            "arm_multiplier": arm_multiplier,
            "arm_duration": arm_duration,
            "arm_other_contribution": arm_other_contribution,
            "arm_other_duration": arm_other_duration,
            "attack_take_percent": attack_take_percent,
            "conflict_cost": conflict_cost
        }
        
        self.state = GameState(
            agents=agent_ids,
            resources={agent_id: initial_resources for agent_id in agent_ids},
            max_rounds=max_rounds
        )
    
    def can_afford_action(self, agent_id: str, action_type: ActionType) -> bool:
        """Check if agent has sufficient resources for action."""
        resources = self.state.resources[agent_id]
        
        if action_type == ActionType.INVEST_SELF:
            return resources >= self.params["invest_self_cost"]
        elif action_type == ActionType.INVEST_OTHER:
            return resources >= self.params["invest_other_cost"]
        elif action_type in [ActionType.ARM_SELF, ActionType.ARM_OTHER]:
            return resources >= self.params["arm_cost"]
        elif action_type == ActionType.ATTACK:
            return resources >= self.params["conflict_cost"]
        
        return False
    
    def resolve_round(self, actions: List[Action]) -> Dict:
        """
        Resolve all actions for a single round.
        
        Args:
            actions: List of actions from all agents
            
        Returns:
            Dictionary with round results
        """
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
                # Agent can't afford action - no action taken
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
            if action.action_type == ActionType.INVEST_SELF:
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
        
        # Update active arms (decrement duration)
        expired_arms = []
        for agent_id in list(self.state.active_arms.keys()):
            self.state.active_arms[agent_id] -= 1
            if self.state.active_arms[agent_id] <= 0:
                expired_arms.append(agent_id)
        
        for agent_id in expired_arms:
            del self.state.active_arms[agent_id]
        
        # Update arm coalitions (decrement duration)
        for target_id in list(self.state.arm_coalitions.keys()):
            expired_supporters = []
            for supporter_id in list(self.state.arm_coalitions[target_id].keys()):
                self.state.arm_coalitions[target_id][supporter_id] -= 1
                if self.state.arm_coalitions[target_id][supporter_id] <= 0:
                    expired_supporters.append(supporter_id)
            
            for supporter_id in expired_supporters:
                del self.state.arm_coalitions[target_id][supporter_id]
            
            # Remove empty coalition entries
            if not self.state.arm_coalitions[target_id]:
                del self.state.arm_coalitions[target_id]
        
        # Add to history and increment round
        self.state.history.append(round_log)
        self.state.round_number += 1
        
        return round_log
    
    def _resolve_invest_self(self, action: Action, round_log: Dict):
        """Resolve invest-self action."""
        agent_id = action.agent_id
        round_log["resource_changes"][agent_id] -= self.params["invest_self_cost"]
        round_log["resource_changes"][agent_id] += self.params["invest_self_return"]
    
    def _resolve_invest_other(self, action: Action, round_log: Dict):
        """Resolve invest-other action."""
        agent_id = action.agent_id
        target_id = action.target_id
        
        if target_id not in self.state.agents:
            return
        
        round_log["resource_changes"][agent_id] -= self.params["invest_other_cost"]
        round_log["resource_changes"][target_id] += self.params["invest_other_return"]
    
    def _resolve_arm_self(self, action: Action, round_log: Dict):
        """Resolve arm-self action."""
        agent_id = action.agent_id
        round_log["resource_changes"][agent_id] -= self.params["arm_cost"]
        self.state.active_arms[agent_id] = self.params["arm_duration"]
    
    def _resolve_arm_other(self, action: Action, round_log: Dict):
        """Resolve arm-other action - adds supporter's resource contribution to target."""
        agent_id = action.agent_id
        target_id = action.target_id
        
        if target_id not in self.state.agents:
            return
        
        round_log["resource_changes"][agent_id] -= self.params["arm_cost"]
        
        # Add this agent as a supporter in the coalition
        if target_id not in self.state.arm_coalitions:
            self.state.arm_coalitions[target_id] = {}
        self.state.arm_coalitions[target_id][agent_id] = self.params["arm_other_duration"]
    
    def _resolve_attack(self, action: Action, round_log: Dict):
        """Resolve attack action with probabilistic combat."""
        attacker_id = action.agent_id
        defender_id = action.target_id
        
        if defender_id not in self.state.agents:
            return
        
        # Calculate combat power (resources * multiplier + coalition support)
        attacker_power = self.state.resources[attacker_id]
        if attacker_id in self.state.active_arms:
            attacker_power *= self.params["arm_multiplier"]
        
        # Add coalition support (portion of supporters' resources)
        if attacker_id in self.state.arm_coalitions:
            for supporter_id in self.state.arm_coalitions[attacker_id]:
                attacker_power += self.state.resources[supporter_id] * self.params["arm_other_contribution"]
        
        defender_power = self.state.resources[defender_id]
        if defender_id in self.state.active_arms:
            defender_power *= self.params["arm_multiplier"]
        
        # Add coalition support
        if defender_id in self.state.arm_coalitions:
            for supporter_id in self.state.arm_coalitions[defender_id]:
                defender_power += self.state.resources[supporter_id] * self.params["arm_other_contribution"]
        
        # Probabilistic combat resolution
        total_power = attacker_power + defender_power
        if total_power > 0:
            attacker_win_prob = attacker_power / total_power
        else:
            attacker_win_prob = 0.5
        
        attacker_wins = np.random.random() < attacker_win_prob
        
        # Apply conflict costs
        round_log["resource_changes"][attacker_id] -= self.params["conflict_cost"]
        round_log["resource_changes"][defender_id] -= self.params["conflict_cost"]
        
        # Transfer resources if there are any to take
        if attacker_wins:
            defender_resources = self.state.resources[defender_id] + round_log["resource_changes"][defender_id]
            transfer = defender_resources * (self.params["attack_take_percent"] / 100.0)
            round_log["resource_changes"][defender_id] -= transfer
            round_log["resource_changes"][attacker_id] += transfer
            winner = attacker_id
        else:
            attacker_resources = self.state.resources[attacker_id] + round_log["resource_changes"][attacker_id]
            transfer = attacker_resources * (self.params["attack_take_percent"] / 100.0)
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
    
    def get_state(self) -> GameState:
        """Get current game state."""
        return self.state
    
    def is_game_over(self, max_rounds: int) -> bool:
        """Check if game should end."""
        return self.state.round_number > max_rounds
