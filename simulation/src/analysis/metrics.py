"""
Metrics for system characterization.
Computes inequality and stability measures per round.

Design references:
- Gini coefficient: standard inequality measure (Atkinson, 1970).
- Palma ratio: ratio of top 10% to bottom 40% income share
  (Palma, 2011; Cobham & Sumner, 2013). More sensitive to tail inequality
  than Gini, relevant for wealth concentration in agent systems.
- Theil T index: information-theoretic inequality measure (Theil, 1967).
  Decomposable into between-group and within-group components.
- Atkinson index: welfare-based inequality with aversion parameter epsilon
  (Atkinson, 1970). epsilon controls sensitivity to bottom of distribution.
- Cooperation ratio: fraction of meaningful actions that are invest_other.
  Operationalizes cooperation as revealed preference (behavioral, not stated).
- Retaliation probability: measures tit-for-tat dynamics (Axelrod, 1984).
- Stabilisation detection: rolling window std threshold, inspired by
  early warning signals methodology (Scheffer et al., 2009).
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


def theil_t_index(resources: Dict[str, float]) -> float:
    """
    Compute Theil T index (Theil's entropy measure) of resource inequality.

    Formula: T = (1/n) * sum(x_i/mean * ln(x_i/mean)) for x_i > 0

    The Theil index measures inequality using information theory. It ranges
    from 0 (perfect equality) to ln(n) (maximum inequality). Values closer
    to 0 indicate more equal distributions.

    Args:
        resources: dict of agent_id -> resource amount

    Returns:
        Theil T index (float >= 0). Returns 0.0 if resources empty or all zero.
    """
    values = np.array([v for v in resources.values() if v > 0])

    if len(values) == 0:
        return 0.0

    mean = values.mean()
    if mean == 0:
        return 0.0

    # T = (1/n) * sum((x_i / mean) * ln(x_i / mean))
    ratios = values / mean
    return np.mean(ratios * np.log(ratios))


def atkinson_index(resources: Dict[str, float], epsilon: float = 1.0) -> float:
    """
    Compute Atkinson index of resource inequality.

    The Atkinson index is a welfare-based inequality measure with parameter
    epsilon controlling inequality aversion. Higher epsilon = more sensitive
    to changes at the lower end of distribution.

    For epsilon=1: A = 1 - (geometric_mean / arithmetic_mean)
    For other epsilon: A = 1 - (1/mean) * ((1/n) * sum(x_i^(1-eps)))^(1/(1-eps))

    Args:
        resources: dict of agent_id -> resource amount
        epsilon: inequality aversion parameter (default: 1.0)
                epsilon=0 means no aversion, higher values = more aversion

    Returns:
        Atkinson index in [0, 1]. 0 = perfect equality, 1 = maximum inequality.
        Returns 0.0 if resources empty or all zero.
    """
    values = np.array([v for v in resources.values() if v > 0])

    if len(values) == 0:
        return 0.0

    mean = values.mean()
    if mean == 0:
        return 0.0

    if epsilon == 1.0:
        # Special case: geometric mean formula
        # A = 1 - (geometric_mean / arithmetic_mean)
        geometric_mean = np.exp(np.mean(np.log(values)))
        return 1.0 - (geometric_mean / mean)
    else:
        # General case
        # A = 1 - (1/mean) * ((1/n) * sum(x_i^(1-eps)))^(1/(1-eps))
        powered = values ** (1 - epsilon)
        ede = (np.mean(powered)) ** (1 / (1 - epsilon))  # equally distributed equivalent
        return 1.0 - (ede / mean)


def cooperation_rate_timeseries(history: List[Dict]) -> List[float]:
    """
    Compute cooperation rate per round (not cumulative).

    Returns a timeseries showing how cooperation rate evolves round-by-round.
    Each value is the cooperation ratio for that specific round.

    Args:
        history: list of round dicts, each with 'actions' key

    Returns:
        List of floats, one per round. Each is the cooperation_ratio for that round.
        Empty list if history is empty.
    """
    timeseries = []

    for round_dict in history:
        invest_other_count = 0
        meaningful_count = 0

        for action_dict in round_dict.get('actions', []):
            action_type = action_dict.get('action', '')
            if action_type not in ('no_action', 'do_nothing'):
                meaningful_count += 1
                if action_type == 'invest_other':
                    invest_other_count += 1

        if meaningful_count == 0:
            rate = 0.0
        else:
            rate = invest_other_count / meaningful_count

        timeseries.append(rate)

    return timeseries


def stabilisation_round(timeseries: List[float],
                        window: int = 10,
                        threshold: float = 0.02) -> Optional[int]:
    """
    Detect the round at which a timeseries stabilises.

    Uses a rolling window: the system is "stabilised" when the standard
    deviation of the metric within the window drops below threshold AND
    stays below for all subsequent windows.

    Args:
        timeseries: List of metric values, one per round (e.g. Gini per round).
        window: Rolling window size (default 10 rounds).
        threshold: Max std within window to count as stable (default 0.02).

    Returns:
        Round index (0-indexed) at which stabilisation begins, or None if
        the system never stabilises.
    """
    if len(timeseries) < window:
        return None

    # Compute rolling std
    for start in range(len(timeseries) - window + 1):
        segment = timeseries[start:start + window]
        if np.std(segment) > threshold:
            continue
        # Check all subsequent windows also stable
        all_stable = True
        for check_start in range(start, len(timeseries) - window + 1):
            if np.std(timeseries[check_start:check_start + window]) > threshold:
                all_stable = False
                break
        if all_stable:
            return start

    return None


def compute_stabilisation_metrics(round_metrics: List[Dict],
                                  window: int = 10,
                                  threshold: float = 0.02) -> Dict:
    """
    Compute stabilisation metrics for a completed run.

    Checks whether key metrics (Gini, cooperation rate, action distribution)
    converge by the end of the simulation.

    Args:
        round_metrics: List of per-round metric dicts (from compute_round_metrics).
                       Each must have 'gini', 'action_distribution', and optionally
                       'resources' keys.
        window: Rolling window for stabilisation detection.
        threshold: Std threshold for stabilisation.

    Returns:
        Dict containing:
            - 'gini_stabilisation_round': round where Gini stabilised (or None)
            - 'gini_stabilised': bool
            - 'gini_final_std': std of Gini over last `window` rounds
            - 'coop_rate_stabilisation_round': round where coop rate stabilised
            - 'coop_rate_stabilised': bool
            - 'coop_rate_final_std': std over last window
            - 'action_entropy_stabilisation_round': round where action entropy stabilised
            - 'action_entropy_stabilised': bool
            - 'action_entropy_final_std': std over last window
            - 'overall_stabilised': True if ALL key metrics stabilised
            - 'latest_stabilisation_round': max of all stabilisation rounds (or None)
    """
    if not round_metrics:
        return {
            'gini_stabilisation_round': None, 'gini_stabilised': False,
            'gini_final_std': 0.0,
            'coop_rate_stabilisation_round': None, 'coop_rate_stabilised': False,
            'coop_rate_final_std': 0.0,
            'action_entropy_stabilisation_round': None, 'action_entropy_stabilised': False,
            'action_entropy_final_std': 0.0,
            'overall_stabilised': False, 'latest_stabilisation_round': None,
        }

    # Extract timeseries
    gini_ts = [m['gini'] for m in round_metrics]

    # Cooperation rate per round
    coop_ts = []
    for m in round_metrics:
        dist = m.get('action_distribution', {})
        invest = dist.get('invest_other', 0)
        meaningful = sum(v for k, v in dist.items() if k not in ('no_action', 'do_nothing'))
        coop_ts.append(invest / meaningful if meaningful > 0 else 0.0)

    # Action distribution entropy per round (Shannon)
    entropy_ts = []
    for m in round_metrics:
        dist = m.get('action_distribution', {})
        total = sum(dist.values())
        if total == 0:
            entropy_ts.append(0.0)
            continue
        probs = np.array([v / total for v in dist.values() if v > 0])
        entropy_ts.append(float(-np.sum(probs * np.log2(probs))))

    # Detect stabilisation
    gini_stab = stabilisation_round(gini_ts, window, threshold)
    coop_stab = stabilisation_round(coop_ts, window, threshold * 2)  # coop rate more volatile
    entropy_stab = stabilisation_round(entropy_ts, window, threshold * 5)  # entropy wider range

    # Final window stats
    def final_std(ts):
        if len(ts) >= window:
            return float(np.std(ts[-window:]))
        return float(np.std(ts)) if ts else 0.0

    stab_rounds = [r for r in [gini_stab, coop_stab, entropy_stab] if r is not None]

    return {
        'gini_stabilisation_round': gini_stab,
        'gini_stabilised': gini_stab is not None,
        'gini_final_std': final_std(gini_ts),
        'coop_rate_stabilisation_round': coop_stab,
        'coop_rate_stabilised': coop_stab is not None,
        'coop_rate_final_std': final_std(coop_ts),
        'action_entropy_stabilisation_round': entropy_stab,
        'action_entropy_stabilised': entropy_stab is not None,
        'action_entropy_final_std': final_std(entropy_ts),
        'overall_stabilised': all(r is not None for r in [gini_stab, coop_stab, entropy_stab]),
        'latest_stabilisation_round': max(stab_rounds) if stab_rounds else None,
    }


def check_early_stopping(round_metrics: List[Dict],
                         min_rounds: int = 15,
                         patience: int = 5,
                         gini_threshold: float = 0.01,
                         entropy_threshold: float = 0.05) -> tuple:
    """
    Online early stopping check — call after each round.

    Two-phase adaptive stopping inspired by Lee et al. (2015, JASSS 18(4))
    rolling-window variance for ABM convergence detection. No published
    LLM multi-agent paper uses online convergence detection — Akata et al.
    (2025), Park et al. (2023), Kuusela & Roy (AAMAS 2024) all use fixed
    horizons. This is a methodological contribution.

    Phase 1: Always run at least min_rounds (exploration).
    Phase 2: Stop if Gini AND action entropy are stable for `patience`
             consecutive rounds (relative change criterion).

    Stability is defined as: range(metric) over last `patience` rounds
    is below the threshold (absolute, scale-invariant for 0-1 metrics).

    Args:
        round_metrics: list of per-round metric dicts (must have 'gini'
                       and 'action_distribution' keys)
        min_rounds: minimum rounds before early stopping can trigger
        patience: number of consecutive stable rounds required
        gini_threshold: max allowed range of Gini over patience window
        entropy_threshold: max allowed range of action entropy over patience window

    Returns:
        (should_stop: bool, reason: str or None)
    """
    n = len(round_metrics)

    # Phase 1: never stop before min_rounds
    if n < min_rounds:
        return (False, None)

    # Need at least `patience` rounds of data
    if n < patience:
        return (False, None)

    window = round_metrics[-patience:]

    # Check Gini stability
    ginis = [m['gini'] for m in window]
    gini_range = max(ginis) - min(ginis)
    gini_stable = gini_range < gini_threshold

    # Check action entropy stability (Shannon entropy of action distribution)
    entropies = []
    for m in window:
        dist = m.get('action_distribution', {})
        total = sum(dist.values())
        if total == 0:
            entropies.append(0.0)
            continue
        probs = np.array(list(dist.values()), dtype=float) / total
        probs = probs[probs > 0]
        entropies.append(float(-np.sum(probs * np.log2(probs))))

    entropy_range = max(entropies) - min(entropies)
    entropy_stable = entropy_range < entropy_threshold

    if gini_stable and entropy_stable:
        reason = (f"converged over {patience} rounds: "
                  f"gini_range={gini_range:.4f}<{gini_threshold}, "
                  f"entropy_range={entropy_range:.4f}<{entropy_threshold}")
        return (True, reason)

    return (False, None)


def fc_variance_across_runs(run_histories: List[List[Dict]]) -> Dict:
    """
    Compute variance of cooperation rate across runs at each round.

    For experiments with multiple runs at the same condition, this measures
    how much cooperation rate varies across runs at each time point.
    High variance indicates unstable/unpredictable dynamics.

    Args:
        run_histories: list of histories, each from a different run at same condition.
                      Each history is a list of round dicts with 'actions' key.

    Returns:
        dict with:
        - 'per_round_variance': list of variance values, one per round index
        - 'mean_variance': mean variance across all rounds (float)
        - 'peak_variance_round': round index with highest variance (int)

        Returns empty dict with zeros if < 2 runs or no rounds.
    """
    if len(run_histories) < 2:
        return {
            'per_round_variance': [],
            'mean_variance': 0.0,
            'peak_variance_round': 0
        }

    # Get cooperation rate timeseries for each run
    timeseries_per_run = [cooperation_rate_timeseries(hist) for hist in run_histories]

    if not timeseries_per_run or len(timeseries_per_run[0]) == 0:
        return {
            'per_round_variance': [],
            'mean_variance': 0.0,
            'peak_variance_round': 0
        }

    # Find minimum length (in case runs have different lengths)
    min_length = min(len(ts) for ts in timeseries_per_run)

    # Compute variance at each round index
    per_round_variance = []
    for round_idx in range(min_length):
        rates_at_round = [ts[round_idx] for ts in timeseries_per_run]
        variance = np.var(rates_at_round)
        per_round_variance.append(variance)

    mean_variance = np.mean(per_round_variance) if per_round_variance else 0.0
    peak_variance_round = int(np.argmax(per_round_variance)) if per_round_variance else 0

    return {
        'per_round_variance': per_round_variance,
        'mean_variance': float(mean_variance),
        'peak_variance_round': peak_variance_round
    }
