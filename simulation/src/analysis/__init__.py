"""Analysis package — metrics, network analysis, EWS, and statistics."""
from .visualize import analyze_run, plot_resource_trajectories, build_interaction_network
from .network import analyze_run_networks, compute_ingroup_outgroup

__all__ = [
    'analyze_run', 'plot_resource_trajectories', 'build_interaction_network',
    'analyze_run_networks', 'compute_ingroup_outgroup',
]

