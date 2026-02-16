"""
Metrics for system characterization.
Computes inequality and stability measures per round.
"""

from typing import Dict, List, Optional
import numpy as np


def gini_coefficient(resources: Dict[str, float]) -> float:
    """
    Compute Gini coefficient from resource distribution.

    Uses the standard formula:
    G = (2 * sum(i * x_i) - (n+1) * sum(x_i)) / (n * sum(x_i))
    where x is sorted ascending and i is 1-indexed rank.

    Args:
        resources: dict of agent_id -> resource amount

    Returns:
        Gini coefficient in [0, 1]. 0 = perfect equality, 1 = max inequality.
    """
    values = np.array(sorted(resources.values()))
    n = len(values)

    if n == 0 or values.sum() == 0:
        return 0.0

    # Standard formula using sorted values and rank
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * values) - (n + 1) * np.sum(values)) / (n * np.sum(values))


def palma_ratio(resources: Dict[str, float]) -> float:
    """
    Compute Palma ratio: share of top 10% / share of bottom 40%.

    For small n, uses max(1, round(n*fraction)) to ensure at least 1 agent
    in each group. With 30 agents: top 3 / bottom 12.

    Args:
        resources: dict of agent_id -> resource amount

    Returns:
        Palma ratio. 1.0 = top 10% has same as bottom 40%.
        Higher = more inequality.
    """
    values = np.array(sorted(resources.values()))
    n = len(values)

    if n == 0:
        return 0.0

    top_count = max(1, round(n * 0.1))
    bottom_count = max(1, round(n * 0.4))

    top_share = values[-top_count:].sum()
    bottom_share = values[:bottom_count].sum()

    if bottom_share == 0:
        return float('inf')

    return top_share / bottom_share


def action_stability(current_actions: Dict[str, str],
                     previous_actions: Dict[str, str]) -> float:
    """
    Fraction of agents that chose the same action as previous round.

    Only counts agents present in both rounds.

    Args:
        current_actions: dict of agent_id -> action_type string
        previous_actions: dict of agent_id -> action_type string

    Returns:
        Fraction in [0, 1]. 1.0 = all agents repeated their action.
    """
    common_agents = set(current_actions.keys()) & set(previous_actions.keys())

    if not common_agents:
        return 0.0

    same = sum(1 for a in common_agents if current_actions[a] == previous_actions[a])
    return same / len(common_agents)


def action_distribution(round_actions: List[Dict]) -> Dict[str, int]:
    """
    Count each action type in a round.

    Args:
        round_actions: list of action dicts from round_log['actions']

    Returns:
        dict of action_type -> count
    """
    counts = {}
    for action in round_actions:
        action_type = action.get('action', 'unknown')
        counts[action_type] = counts.get(action_type, 0) + 1
    return counts


def compute_round_metrics(resources: Dict[str, float],
                          round_actions: List[Dict],
                          previous_actions_map: Optional[Dict[str, str]] = None) -> Dict:
    """
    Compute all metrics for a single round.

    Args:
        resources: current resource distribution
        round_actions: list of action dicts from round_log['actions']
        previous_actions_map: dict of agent_id -> action_type from previous round

    Returns:
        dict with gini, palma, action_stability, action_distribution
    """
    # Build current actions map
    current_actions_map = {}
    for action in round_actions:
        agent = action.get('agent')
        action_type = action.get('action', 'no_action')
        if agent:
            current_actions_map[agent] = action_type

    metrics = {
        'gini': gini_coefficient(resources),
        'palma': palma_ratio(resources),
        'action_distribution': action_distribution(round_actions),
    }

    if previous_actions_map is not None:
        metrics['action_stability'] = action_stability(current_actions_map, previous_actions_map)
    else:
        metrics['action_stability'] = None

    return metrics, current_actions_map


def cooperation_ratio(history: List[Dict]) -> float:
    """
    Compute the ratio of cooperative actions to total meaningful actions.

    Counts 'invest_other' actions divided by all actions except 'no_action'
    and 'do_nothing'.

    Args:
        history: list of round dicts, each with 'actions' key containing
                 list of action dicts with 'agent', 'action', 'target' fields

    Returns:
        Fraction of meaningful actions that were invest_other.
        Returns 0.0 if no meaningful actions found.
    """
    invest_other_count = 0
    meaningful_count = 0

    for round_dict in history:
        for action_dict in round_dict.get('actions', []):
            action_type = action_dict.get('action', '')
            if action_type not in ('no_action', 'do_nothing'):
                meaningful_count += 1
                if action_type == 'invest_other':
                    invest_other_count += 1

    if meaningful_count == 0:
        return 0.0

    return invest_other_count / meaningful_count


def first_attack_round(history: List[Dict]) -> Optional[int]:
    """
    Find the round number of the first attack action.

    Args:
        history: list of round dicts, each with 'actions' key and 'round' key

    Returns:
        Round number (int) of first round containing an 'attack' action,
        or None if no attacks occurred.
    """
    for round_dict in history:
        for action_dict in round_dict.get('actions', []):
            if action_dict.get('action') == 'attack':
                return round_dict.get('round')
    return None


def retaliation_probability(history: List[Dict], window: int = 2) -> float:
    """
    Compute probability that attacks are retaliated within a time window.

    For each attack, checks if the defender attacked the original attacker
    within the next `window` rounds.

    Args:
        history: list of round dicts, each with 'actions' key and 'round' key
        window: number of rounds to look ahead for retaliation (default: 2)

    Returns:
        Fraction of attacks that were retaliated within window.
        Returns 0.0 if no attacks occurred.
    """
    attacks = []  # List of (round_idx, attacker, target)

    # Collect all attacks with their round index
    for round_idx, round_dict in enumerate(history):
        for action_dict in round_dict.get('actions', []):
            if action_dict.get('action') == 'attack':
                attacker = action_dict.get('agent')
                target = action_dict.get('target')
                if attacker and target:
                    attacks.append((round_idx, attacker, target))

    if not attacks:
        return 0.0

    retaliated_count = 0

    for attack_round_idx, attacker, target in attacks:
        # Check if target attacked attacker in next `window` rounds
        retaliated = False
        for check_round_idx in range(attack_round_idx + 1,
                                       min(attack_round_idx + 1 + window, len(history))):
            for action_dict in history[check_round_idx].get('actions', []):
                if (action_dict.get('action') == 'attack' and
                    action_dict.get('agent') == target and
                    action_dict.get('target') == attacker):
                    retaliated = True
                    break
            if retaliated:
                break

        if retaliated:
            retaliated_count += 1

    return retaliated_count / len(attacks)


def coalition_stability(history: List[Dict]) -> float:
    """
    Compute mean Jaccard similarity of coalition structure across consecutive rounds.

    For each consecutive pair of rounds, computes Jaccard similarity of the set
    of (agent, target) pairs for 'arm_other' actions. Higher values indicate
    more stable coalition structure.

    Args:
        history: list of round dicts, each with 'actions' key

    Returns:
        Mean Jaccard similarity across all consecutive round pairs.
        Returns 0.0 if fewer than 2 rounds.
    """
    if len(history) < 2:
        return 0.0

    jaccard_similarities = []

    for i in range(len(history) - 1):
        # Extract arm_other pairs from current and next round
        current_pairs = set()
        for action_dict in history[i].get('actions', []):
            if action_dict.get('action') == 'arm_other':
                agent = action_dict.get('agent')
                target = action_dict.get('target')
                if agent and target:
                    current_pairs.add((agent, target))

        next_pairs = set()
        for action_dict in history[i + 1].get('actions', []):
            if action_dict.get('action') == 'arm_other':
                agent = action_dict.get('agent')
                target = action_dict.get('target')
                if agent and target:
                    next_pairs.add((agent, target))

        # Compute Jaccard similarity
        if not current_pairs and not next_pairs:
            # Both empty: perfect similarity
            jaccard = 1.0
        elif not current_pairs or not next_pairs:
            # One empty, one not: zero similarity
            jaccard = 0.0
        else:
            intersection = len(current_pairs & next_pairs)
            union = len(current_pairs | next_pairs)
            jaccard = intersection / union if union > 0 else 0.0

        jaccard_similarities.append(jaccard)

    return np.mean(jaccard_similarities) if jaccard_similarities else 0.0
