"""
Analysis tools for simulation results.
Visualize resource trajectories and interaction networks.
"""

import json
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path
from collections import defaultdict


def load_simulation_results(run_id: str, data_dir: Path) -> tuple:
    """Load simulation results from files."""
    history_file = data_dir / f"{run_id}_history.json"
    traces_file = data_dir / f"{run_id}_traces.json"
    
    with open(history_file, 'r') as f:
        history_data = json.load(f)
    
    with open(traces_file, 'r') as f:
        traces_data = json.load(f)
    
    return history_data, traces_data


def plot_resource_trajectories(history_data: dict, output_path: Path):
    """Plot resource trajectories over time."""
    agents = history_data['agents']
    history = history_data['history']
    
    # Extract resource trajectories
    trajectories = {agent: [] for agent in agents}
    rounds = []
    
    for round_data in history:
        rounds.append(round_data['round'])
        # Reconstruct resources at end of each round
        round_resources = history_data['final_resources'].copy()
        
        # Work backwards from final state
        for i in range(len(history) - 1, round_data['round'], -1):
            for agent, change in history[i]['resource_changes'].items():
                round_resources[agent] -= change
        
        for agent in agents:
            trajectories[agent].append(round_resources[agent])
    
    # Plot
    plt.figure(figsize=(12, 6))
    for agent in agents:
        plt.plot(rounds, trajectories[agent], marker='o', label=agent, linewidth=2)
    
    plt.xlabel('Round', fontsize=12)
    plt.ylabel('Resources', fontsize=12)
    plt.title('Resource Trajectories Over Time', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    print(f"Saved resource trajectory plot to {output_path}")


def build_interaction_network(history_data: dict) -> nx.DiGraph:
    """Build directed network from interaction history."""
    G = nx.DiGraph()
    
    agents = history_data['agents']
    for agent in agents:
        G.add_node(agent)
    
    # Count interactions
    edge_weights = defaultdict(lambda: {'invest': 0, 'arm': 0, 'attack': 0})
    
    for round_data in history_data['history']:
        for action in round_data['actions']:
            if action.get('action') == 'no_action':
                continue
            
            source = action['agent']
            target = action.get('target')
            action_type = action['action']
            
            if target and target in agents:
                if 'invest' in action_type:
                    edge_weights[(source, target)]['invest'] += 1
                elif 'arm' in action_type:
                    edge_weights[(source, target)]['arm'] += 1
                elif action_type == 'attack':
                    edge_weights[(source, target)]['attack'] += 1
    
    # Add edges with weights
    for (source, target), weights in edge_weights.items():
        total = sum(weights.values())
        G.add_edge(source, target, 
                   invest=weights['invest'],
                   arm=weights['arm'],
                   attack=weights['attack'],
                   total=total)
    
    return G


def plot_interaction_network(history_data: dict, output_path: Path):
    """Visualize interaction network."""
    G = build_interaction_network(history_data)
    
    plt.figure(figsize=(10, 10))
    
    # Layout
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                          node_size=2000, alpha=0.9)
    
    # Draw edges colored by interaction type
    edges = G.edges(data=True)
    
    # Separate edge types
    invest_edges = [(u, v) for u, v, d in edges if d.get('invest', 0) > 0]
    arm_edges = [(u, v) for u, v, d in edges if d.get('arm', 0) > 0]
    attack_edges = [(u, v) for u, v, d in edges if d.get('attack', 0) > 0]
    
    # Draw different edge types
    nx.draw_networkx_edges(G, pos, edgelist=invest_edges, 
                          edge_color='green', width=2, alpha=0.6,
                          label='Invest', arrows=True, arrowsize=20)
    nx.draw_networkx_edges(G, pos, edgelist=arm_edges,
                          edge_color='blue', width=2, alpha=0.6,
                          label='Arm', arrows=True, arrowsize=20,
                          connectionstyle='arc3,rad=0.1')
    nx.draw_networkx_edges(G, pos, edgelist=attack_edges,
                          edge_color='red', width=2, alpha=0.6,
                          label='Attack', arrows=True, arrowsize=20,
                          connectionstyle='arc3,rad=0.2')
    
    # Labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    plt.title('Agent Interaction Network', fontsize=14)
    plt.legend()
    plt.axis('off')
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    print(f"Saved interaction network plot to {output_path}")


def generate_summary_stats(history_data: dict) -> dict:
    """Generate summary statistics."""
    stats = {
        'total_rounds': history_data['total_rounds'],
        'final_resources': history_data['final_resources'],
        'action_counts': defaultdict(int),
        'attack_count': 0,
        'cooperation_count': 0
    }
    
    for round_data in history_data['history']:
        for action in round_data['actions']:
            action_type = action.get('action', 'no_action')
            stats['action_counts'][action_type] += 1
            
            if action_type == 'attack':
                stats['attack_count'] += 1
            elif action_type in ['invest_other', 'arm_other']:
                stats['cooperation_count'] += 1
    
    return dict(stats)


def analyze_run(run_id: str, data_dir: Path = None):
    """Complete analysis of a simulation run."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent / "data" / "runs"
    
    print(f"\n{'='*60}")
    print(f"Analyzing run: {run_id}")
    print(f"{'='*60}\n")
    
    # Load data
    history_data, traces_data = load_simulation_results(run_id, data_dir)
    
    # Generate stats
    stats = generate_summary_stats(history_data)
    
    print("Summary Statistics:")
    print(f"  Total rounds: {stats['total_rounds']}")
    print(f"  Attacks: {stats['attack_count']}")
    print(f"  Cooperative actions: {stats['cooperation_count']}")
    print(f"\nAction counts:")
    for action, count in sorted(stats['action_counts'].items()):
        print(f"  {action}: {count}")
    
    print(f"\nFinal resources:")
    for agent, resources in sorted(stats['final_resources'].items()):
        print(f"  {agent}: {resources:.1f}")
    
    # Create plots
    output_dir = data_dir / "plots"
    output_dir.mkdir(exist_ok=True)
    
    plot_resource_trajectories(history_data, 
                               output_dir / f"{run_id}_trajectories.png")
    plot_interaction_network(history_data,
                            output_dir / f"{run_id}_network.png")
    
    print(f"\nAnalysis complete!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.analysis.visualize <run_id>")
        sys.exit(1)
    
    run_id = sys.argv[1]
    analyze_run(run_id)
