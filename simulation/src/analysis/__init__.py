"""Analysis package — pure log-readers for §3.5 metrics + network structure."""
from .network import analyze_run_networks, compute_ingroup_outgroup
from .metrics import (
    load_run, gini, cooperation_rate, action_distribution,
    action_stability, network_churn, first_attack_round,
    coalition_sizes, rewire_intent_outcome,
    truncation_count, retry_count,
    cooperation_rate_timeseries, gini_timeseries, action_distribution_timeseries,
)

__all__ = [
    'analyze_run_networks', 'compute_ingroup_outgroup',
    'load_run', 'gini', 'cooperation_rate', 'action_distribution',
    'action_stability', 'network_churn', 'first_attack_round',
    'coalition_sizes', 'rewire_intent_outcome',
    'truncation_count', 'retry_count',
    'cooperation_rate_timeseries', 'gini_timeseries', 'action_distribution_timeseries',
]
