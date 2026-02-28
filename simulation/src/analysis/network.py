"""
Network analysis module for detecting emergent social structures.

This module constructs interaction networks from simulation history and computes
structural metrics including community detection, hierarchy analysis, and temporal
stability measures.
"""

import numpy as np
import networkx as nx
from typing import List, Dict, Tuple, Set, Optional, Any

# Lazy imports for Leiden (heavy deps, may not be installed locally)
leidenalg = None
ig = None

def _ensure_leiden():
    global leidenalg, ig
    if leidenalg is None:
        import leidenalg as _la
        import igraph as _ig
        leidenalg = _la
        ig = _ig


def build_windowed_networks(history: List[Dict], window_size: int = 5) -> List[Dict]:
    """
    Construct directed weighted interaction networks using sliding windows.

    Args:
        history: List of round dicts, each with 'round' and 'actions' keys.
                Each action dict has 'agent', 'action', and 'target' fields.
        window_size: Number of rounds per window (default 5).

    Returns:
        List of dicts, each containing:
            - 'window': tuple (start_round, end_round)
            - 'cooperation_network': networkx DiGraph (invest_other edges)
            - 'conflict_network': networkx DiGraph (attack edges)
            - 'coalition_network': networkx DiGraph (arm_other edges)
            - 'full_network': networkx DiGraph (all interactions)
    """
    if not history:
        return []

    # Collect all agent IDs
    all_agents = set()
    for round_data in history:
        for action in round_data.get('actions', []):
            all_agents.add(action['agent'])
            if action.get('target'):
                all_agents.add(action['target'])

    networks = []
    n_rounds = len(history)

    # Sliding windows
    for start_idx in range(n_rounds - window_size + 1):
        end_idx = start_idx + window_size
        window_rounds = history[start_idx:end_idx]

        start_round = window_rounds[0]['round']
        end_round = window_rounds[-1]['round']

        # Initialize networks
        cooperation_net = nx.DiGraph()
        conflict_net = nx.DiGraph()
        coalition_net = nx.DiGraph()
        full_net = nx.DiGraph()

        # Add all agents as nodes
        for agent in all_agents:
            cooperation_net.add_node(agent)
            conflict_net.add_node(agent)
            coalition_net.add_node(agent)
            full_net.add_node(agent)

        # Count interactions
        for round_data in window_rounds:
            for action in round_data.get('actions', []):
                agent = action['agent']
                action_type = action['action']
                target = action.get('target')

                if not target:
                    continue

                # Cooperation: invest_other
                if action_type == 'invest_other':
                    if cooperation_net.has_edge(agent, target):
                        cooperation_net[agent][target]['weight'] += 1
                    else:
                        cooperation_net.add_edge(agent, target, weight=1)

                    # Update full network
                    if not full_net.has_edge(agent, target):
                        full_net.add_edge(agent, target, invest=0, attack=0, arm=0, total=0)
                    full_net[agent][target]['invest'] += 1
                    full_net[agent][target]['total'] += 1

                # Conflict: attack
                elif action_type == 'attack':
                    if conflict_net.has_edge(agent, target):
                        conflict_net[agent][target]['weight'] += 1
                    else:
                        conflict_net.add_edge(agent, target, weight=1)

                    # Update full network
                    if not full_net.has_edge(agent, target):
                        full_net.add_edge(agent, target, invest=0, attack=0, arm=0, total=0)
                    full_net[agent][target]['attack'] += 1
                    full_net[agent][target]['total'] += 1

                # Coalition: arm_other
                elif action_type == 'arm_other':
                    if coalition_net.has_edge(agent, target):
                        coalition_net[agent][target]['weight'] += 1
                    else:
                        coalition_net.add_edge(agent, target, weight=1)

                    # Update full network
                    if not full_net.has_edge(agent, target):
                        full_net.add_edge(agent, target, invest=0, attack=0, arm=0, total=0)
                    full_net[agent][target]['arm'] += 1
                    full_net[agent][target]['total'] += 1

        networks.append({
            'window': (start_round, end_round),
            'cooperation_network': cooperation_net,
            'conflict_network': conflict_net,
            'coalition_network': coalition_net,
            'full_network': full_net
        })

    return networks


def network_metrics(G: nx.DiGraph) -> Dict[str, Any]:
    """
    Compute structural metrics for a single networkx DiGraph.

    Args:
        G: A networkx DiGraph.

    Returns:
        Dict containing:
            - 'density': network density
            - 'reciprocity': fraction of reciprocated edges
            - 'clustering': mean clustering coefficient
            - 'betweenness_centrality': dict of node -> centrality
            - 'eigenvector_centrality': dict of node -> centrality
            - 'degree_centrality_cv': coefficient of variation of in-degree
            - 'n_edges': number of edges
            - 'n_nodes': number of nodes
    """
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes == 0 or n_edges == 0:
        return {
            'density': 0.0,
            'reciprocity': 0.0,
            'clustering': 0.0,
            'betweenness_centrality': {},
            'eigenvector_centrality': {},
            'degree_centrality_cv': 0.0,
            'n_edges': n_edges,
            'n_nodes': n_nodes
        }

    # Density
    density = nx.density(G)

    # Reciprocity
    reciprocal_edges = 0
    total_edges = 0
    for u, v in G.edges():
        total_edges += 1
        if G.has_edge(v, u):
            reciprocal_edges += 1
    reciprocity = reciprocal_edges / total_edges if total_edges > 0 else 0.0

    # Clustering (on undirected version)
    G_undirected = G.to_undirected()
    try:
        clustering = nx.average_clustering(G_undirected)
    except:
        clustering = 0.0

    # Betweenness centrality
    try:
        betweenness = nx.betweenness_centrality(G)
    except:
        betweenness = {node: 0.0 for node in G.nodes()}

    # Eigenvector centrality
    try:
        eigenvector = nx.eigenvector_centrality_numpy(G)
    except:
        eigenvector = {node: 0.0 for node in G.nodes()}

    # Degree centrality coefficient of variation
    in_degrees = dict(G.in_degree())
    if in_degrees:
        degree_values = list(in_degrees.values())
        mean_degree = np.mean(degree_values)
        std_degree = np.std(degree_values)
        degree_cv = std_degree / mean_degree if mean_degree > 0 else 0.0
    else:
        degree_cv = 0.0

    return {
        'density': density,
        'reciprocity': reciprocity,
        'clustering': clustering,
        'betweenness_centrality': betweenness,
        'eigenvector_centrality': eigenvector,
        'degree_centrality_cv': degree_cv,
        'n_edges': n_edges,
        'n_nodes': n_nodes
    }


def detect_communities(G: nx.DiGraph,
                      resolution_values: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Find communities using the Leiden algorithm at multiple resolutions.

    Args:
        G: A networkx DiGraph.
        resolution_values: List of resolution gamma values
                          (default [0.5, 0.8, 1.0, 1.5, 2.0]).

    Returns:
        Dict containing per-resolution results and best partition:
            - For each resolution: 'communities', 'modularity', 'n_communities'
            - 'best_resolution': resolution with highest modularity
            - 'best_partition': partition at best resolution
    """
    if resolution_values is None:
        resolution_values = [0.5, 0.8, 1.0, 1.5, 2.0]

    if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
        return {
            'best_resolution': resolution_values[0] if resolution_values else 1.0,
            'best_partition': [],
            **{f'resolution_{res}': {
                'communities': [],
                'modularity': 0.0,
                'n_communities': 0
            } for res in resolution_values}
        }

    _ensure_leiden()

    # Convert networkx to igraph
    # Create mapping from node IDs to indices
    node_list = list(G.nodes())
    node_to_idx = {node: idx for idx, node in enumerate(node_list)}

    # Create igraph graph
    g = ig.Graph(directed=True)
    g.add_vertices(len(node_list))

    # Add edges with weights
    edges = []
    weights = []
    for u, v, data in G.edges(data=True):
        edges.append((node_to_idx[u], node_to_idx[v]))
        weights.append(data.get('weight', 1))

    if edges:
        g.add_edges(edges)
        g.es['weight'] = weights

    results = {}
    best_modularity = -1
    best_resolution = resolution_values[0]
    best_partition = []

    for resolution in resolution_values:
        try:
            # Run Leiden algorithm
            partition = leidenalg.find_partition(
                g,
                leidenalg.RBConfigurationVertexPartition,
                weights='weight',
                resolution_parameter=resolution
            )

            # Convert partition to list of sets
            communities = []
            for community_indices in partition:
                community = {node_list[idx] for idx in community_indices}
                communities.append(community)

            modularity = partition.modularity
            n_communities = len(communities)

            results[f'resolution_{resolution}'] = {
                'communities': communities,
                'modularity': modularity,
                'n_communities': n_communities
            }

            if modularity > best_modularity:
                best_modularity = modularity
                best_resolution = resolution
                best_partition = communities

        except Exception as e:
            # Handle convergence or other errors
            results[f'resolution_{resolution}'] = {
                'communities': [],
                'modularity': 0.0,
                'n_communities': 0
            }

    results['best_resolution'] = best_resolution
    results['best_partition'] = best_partition

    return results


def _compute_nmi(partition1: List[Set], partition2: List[Set]) -> float:
    """
    Compute Normalized Mutual Information between two partitions.

    Args:
        partition1: List of sets of node IDs.
        partition2: List of sets of node IDs.

    Returns:
        NMI value between 0 and 1.
    """
    # Get all nodes
    all_nodes = set()
    for community in partition1:
        all_nodes.update(community)
    for community in partition2:
        all_nodes.update(community)

    if not all_nodes:
        return 0.0

    # Create label arrays
    node_list = sorted(all_nodes)
    labels1 = np.zeros(len(node_list), dtype=int)
    labels2 = np.zeros(len(node_list), dtype=int)

    node_to_idx = {node: idx for idx, node in enumerate(node_list)}

    for comm_idx, community in enumerate(partition1):
        for node in community:
            if node in node_to_idx:
                labels1[node_to_idx[node]] = comm_idx

    for comm_idx, community in enumerate(partition2):
        for node in community:
            if node in node_to_idx:
                labels2[node_to_idx[node]] = comm_idx

    # Build contingency table
    n = len(labels1)
    n_clusters1 = len(partition1)
    n_clusters2 = len(partition2)

    contingency = np.zeros((n_clusters1, n_clusters2), dtype=float)
    for i in range(n):
        contingency[labels1[i], labels2[i]] += 1

    # Compute marginals
    sum_rows = contingency.sum(axis=1)
    sum_cols = contingency.sum(axis=0)

    # Compute entropies
    def entropy(counts):
        counts = counts[counts > 0]
        probs = counts / counts.sum()
        return -np.sum(probs * np.log(probs))

    H1 = entropy(sum_rows)
    H2 = entropy(sum_cols)

    if H1 == 0 and H2 == 0:
        return 1.0
    if H1 == 0 or H2 == 0:
        return 0.0

    # Compute mutual information
    MI = 0.0
    for i in range(n_clusters1):
        for j in range(n_clusters2):
            if contingency[i, j] > 0:
                MI += (contingency[i, j] / n) * np.log(
                    (contingency[i, j] * n) / (sum_rows[i] * sum_cols[j])
                )

    # Normalized mutual information
    NMI = 2 * MI / (H1 + H2)
    return max(0.0, min(1.0, NMI))


def community_stability(partitions_over_time: List[List[Set]]) -> Dict[str, Any]:
    """
    Compute stability of community structure across consecutive time windows.

    Args:
        partitions_over_time: List of partitions, each a list of sets of node IDs.

    Returns:
        Dict containing:
            - 'nmi_values': list of NMI between consecutive partitions
            - 'mean_nmi': average NMI
            - 'jaccard_values': list of edge-level Jaccard indices
            - 'mean_jaccard': average Jaccard
    """
    if len(partitions_over_time) < 2:
        return {
            'nmi_values': [],
            'mean_nmi': 0.0,
            'jaccard_values': [],
            'mean_jaccard': 0.0
        }

    nmi_values = []
    for i in range(len(partitions_over_time) - 1):
        nmi = _compute_nmi(partitions_over_time[i], partitions_over_time[i + 1])
        nmi_values.append(nmi)

    mean_nmi = np.mean(nmi_values) if nmi_values else 0.0

    # Placeholder for Jaccard (requires edge sets from networks)
    # This would need the actual networks to compute edge-level Jaccard
    jaccard_values = []
    mean_jaccard = 0.0

    return {
        'nmi_values': nmi_values,
        'mean_nmi': mean_nmi,
        'jaccard_values': jaccard_values,
        'mean_jaccard': mean_jaccard
    }


def compute_elo_ratings(history: List[Dict], k_factor: int = 32) -> Dict[str, Any]:
    """
    Compute Elo ratings for agents based on attack outcomes.

    Args:
        history: List of round dicts with combat results.
        k_factor: Elo update factor (default 32).

    Returns:
        Dict containing:
            - 'final_ratings': dict of agent_id -> Elo rating
            - 'rating_history': list of rating snapshots per round
            - 'steepness': hierarchy steepness measure
            - 'landau_h': Landau's linearity index
    """
    # Initialize ratings
    all_agents = set()
    for round_data in history:
        for action in round_data.get('actions', []):
            all_agents.add(action['agent'])
            if action.get('target'):
                all_agents.add(action['target'])

    ratings = {agent: 1500.0 for agent in all_agents}
    rating_history = []

    # Track wins for hierarchy metrics
    win_matrix = {agent: {other: 0 for other in all_agents} for agent in all_agents}

    for round_data in history:
        # Process combat results if available
        combat_results = round_data.get('combat_results', [])

        for combat in combat_results:
            attacker = combat.get('attacker')
            defender = combat.get('defender')
            winner = combat.get('winner')

            if not attacker or not defender or not winner:
                continue

            # Update Elo ratings
            rating_a = ratings[attacker]
            rating_d = ratings[defender]

            expected_a = 1 / (1 + 10 ** ((rating_d - rating_a) / 400))

            if winner == attacker:
                score_a = 1.0
                win_matrix[attacker][defender] += 1
            elif winner == defender:
                score_a = 0.0
                win_matrix[defender][attacker] += 1
            else:
                score_a = 0.5

            ratings[attacker] += k_factor * (score_a - expected_a)
            ratings[defender] += k_factor * ((1 - score_a) - (1 - expected_a))

        rating_history.append(dict(ratings))

    # Compute hierarchy metrics
    n = len(all_agents)
    if n <= 1:
        return {
            'final_ratings': ratings,
            'rating_history': rating_history,
            'steepness': 0.0,
            'landau_h': 0.0
        }

    # David's Scores
    agent_list = sorted(all_agents)
    david_scores = {}

    for agent in agent_list:
        w = sum(win_matrix[agent].values())
        l = sum(win_matrix[other][agent] for other in agent_list)

        # Second order
        w2 = sum(
            win_matrix[agent][other] * sum(win_matrix[other].values())
            for other in agent_list
        )
        l2 = sum(
            win_matrix[other][agent] * sum(win_matrix[other].values())
            for other in agent_list
        )

        david_scores[agent] = w + w2 - l - l2

    # Normalize and compute steepness
    ds_values = np.array([david_scores[agent] for agent in agent_list])
    if ds_values.std() > 0:
        ds_normalized = (ds_values - ds_values.mean()) / ds_values.std()
    else:
        ds_normalized = ds_values

    ranks = np.arange(1, n + 1)
    if n > 1:
        # Sort by David's scores descending
        sorted_indices = np.argsort(-ds_values)
        ds_sorted = ds_normalized[sorted_indices]

        # Linear regression
        slope = np.polyfit(ranks, ds_sorted, 1)[0]
        steepness = abs(slope)
    else:
        steepness = 0.0

    # Landau's h'
    dominance_counts = []
    for agent in agent_list:
        dominated = sum(1 for other in agent_list
                       if win_matrix[agent][other] > win_matrix[other][agent])
        dominance_counts.append(dominated)

    v = np.array(dominance_counts)
    h_raw = (12 / (n**3 - n)) * np.sum((v - (n - 1) / 2) ** 2)
    landau_h = h_raw

    return {
        'final_ratings': ratings,
        'rating_history': rating_history,
        'steepness': steepness,
        'landau_h': landau_h
    }


def hierarchy_metrics(history: List[Dict]) -> Dict[str, Any]:
    """
    Compute dominance hierarchy metrics from interaction history.

    Args:
        history: List of round dicts with combat results.

    Returns:
        Dict containing hierarchy metrics:
            - 'david_scores': dict of agent -> David's Score
            - 'steepness': hierarchy steepness
            - 'landau_h': Landau's linearity index
            - 'triangle_transitivity': fraction of transitive triads
    """
    # Collect all agents
    all_agents = set()
    for round_data in history:
        for action in round_data.get('actions', []):
            all_agents.add(action['agent'])
            if action.get('target'):
                all_agents.add(action['target'])

    agent_list = sorted(all_agents)
    n = len(agent_list)

    if n <= 1:
        return {
            'david_scores': {},
            'steepness': 0.0,
            'landau_h': 0.0,
            'triangle_transitivity': 0.0
        }

    # Build dominance matrix
    win_matrix = {agent: {other: 0 for other in agent_list} for agent in agent_list}

    for round_data in history:
        combat_results = round_data.get('combat_results', [])
        for combat in combat_results:
            attacker = combat.get('attacker')
            defender = combat.get('defender')
            winner = combat.get('winner')

            if not attacker or not defender or not winner:
                continue

            if winner == attacker:
                win_matrix[attacker][defender] += 1
            elif winner == defender:
                win_matrix[defender][attacker] += 1

    # David's Scores
    david_scores = {}
    for agent in agent_list:
        w = sum(win_matrix[agent].values())
        l = sum(win_matrix[other][agent] for other in agent_list)

        w2 = sum(
            win_matrix[agent][other] * sum(win_matrix[other].values())
            for other in agent_list
        )
        l2 = sum(
            win_matrix[other][agent] * sum(win_matrix[other].values())
            for other in agent_list
        )

        david_scores[agent] = w + w2 - l - l2

    # Steepness
    ds_values = np.array([david_scores[agent] for agent in agent_list])
    if ds_values.std() > 0:
        ds_normalized = (ds_values - ds_values.mean()) / ds_values.std()
    else:
        ds_normalized = ds_values

    sorted_indices = np.argsort(-ds_values)
    ds_sorted = ds_normalized[sorted_indices]
    ranks = np.arange(1, n + 1)

    if n > 1:
        slope = np.polyfit(ranks, ds_sorted, 1)[0]
        steepness = abs(slope)
    else:
        steepness = 0.0

    # Landau's h'
    dominance_counts = []
    for agent in agent_list:
        dominated = sum(1 for other in agent_list
                       if win_matrix[agent][other] > win_matrix[other][agent])
        dominance_counts.append(dominated)

    v = np.array(dominance_counts)
    h_raw = (12 / (n**3 - n)) * np.sum((v - (n - 1) / 2) ** 2)
    landau_h = h_raw

    # Triangle transitivity
    transitive_count = 0
    total_triads = 0

    for i, agent_i in enumerate(agent_list):
        for j, agent_j in enumerate(agent_list):
            if i == j:
                continue
            for k, agent_k in enumerate(agent_list):
                if k == i or k == j:
                    continue

                total_triads += 1

                # Check if i -> j and j -> k implies i -> k
                i_beats_j = win_matrix[agent_i][agent_j] > win_matrix[agent_j][agent_i]
                j_beats_k = win_matrix[agent_j][agent_k] > win_matrix[agent_k][agent_j]
                i_beats_k = win_matrix[agent_i][agent_k] > win_matrix[agent_k][agent_i]

                if i_beats_j and j_beats_k and i_beats_k:
                    transitive_count += 1

    triangle_transitivity = transitive_count / total_triads if total_triads > 0 else 0.0

    return {
        'david_scores': david_scores,
        'steepness': steepness,
        'landau_h': landau_h,
        'triangle_transitivity': triangle_transitivity
    }


def compute_ingroup_outgroup(history: List[Dict],
                             partition: List[Set[str]],
                             window: tuple = None) -> Dict[str, Any]:
    """
    Compute ingroup vs outgroup interaction rates given a community partition.

    For each directed action (invest_other, attack, arm_other), classifies it as
    ingroup (agent and target in same community) or outgroup (different communities).

    Args:
        history: List of round dicts with 'actions' key.
        partition: List of sets of agent IDs (community partition from Leiden).
        window: Optional (start_round, end_round) tuple to restrict analysis.
                If None, uses all rounds.

    Returns:
        Dict containing:
            - 'ingroup_cooperation': count of invest_other within community
            - 'outgroup_cooperation': count of invest_other across communities
            - 'ingroup_attack': count of attacks within community
            - 'outgroup_attack': count of attacks across communities
            - 'ingroup_cooperation_rate': fraction of cooperation that is ingroup
            - 'outgroup_cooperation_rate': fraction of cooperation that is outgroup
            - 'ingroup_attack_rate': fraction of attacks that are ingroup
            - 'outgroup_attack_rate': fraction of attacks that are outgroup
            - 'ei_index': E-I index = (external - internal) / (external + internal)
                          Range [-1, 1]. -1 = all ingroup, +1 = all outgroup, 0 = balanced
            - 'ei_cooperation': E-I index for cooperation only
            - 'ei_conflict': E-I index for conflict only
            - 'n_communities': number of communities in partition
            - 'community_sizes': list of community sizes
    """
    if not partition:
        return {
            'ingroup_cooperation': 0, 'outgroup_cooperation': 0,
            'ingroup_attack': 0, 'outgroup_attack': 0,
            'ingroup_cooperation_rate': 0.0, 'outgroup_cooperation_rate': 0.0,
            'ingroup_attack_rate': 0.0, 'outgroup_attack_rate': 0.0,
            'ei_index': 0.0, 'ei_cooperation': 0.0, 'ei_conflict': 0.0,
            'n_communities': 0, 'community_sizes': [],
        }

    # Build agent -> community lookup
    agent_to_community = {}
    for comm_idx, community in enumerate(partition):
        for agent in community:
            agent_to_community[agent] = comm_idx

    ingroup_coop = 0
    outgroup_coop = 0
    ingroup_attack = 0
    outgroup_attack = 0
    ingroup_arm = 0
    outgroup_arm = 0

    for round_data in history:
        round_num = round_data.get('round', 0)
        if window and (round_num < window[0] or round_num > window[1]):
            continue

        for action in round_data.get('actions', []):
            agent = action.get('agent')
            target = action.get('target')
            action_type = action.get('action', '')

            if not target or agent not in agent_to_community or target not in agent_to_community:
                continue

            same_community = agent_to_community[agent] == agent_to_community[target]

            if action_type == 'invest_other':
                if same_community:
                    ingroup_coop += 1
                else:
                    outgroup_coop += 1
            elif action_type == 'attack':
                if same_community:
                    ingroup_attack += 1
                else:
                    outgroup_attack += 1
            elif action_type == 'arm_other':
                if same_community:
                    ingroup_arm += 1
                else:
                    outgroup_arm += 1

    total_coop = ingroup_coop + outgroup_coop
    total_attack = ingroup_attack + outgroup_attack
    total_directed = total_coop + total_attack + ingroup_arm + outgroup_arm
    total_ingroup = ingroup_coop + ingroup_attack + ingroup_arm
    total_outgroup = outgroup_coop + outgroup_attack + outgroup_arm

    def safe_rate(numerator, denominator):
        return numerator / denominator if denominator > 0 else 0.0

    def ei_index(external, internal):
        total = external + internal
        return (external - internal) / total if total > 0 else 0.0

    return {
        'ingroup_cooperation': ingroup_coop,
        'outgroup_cooperation': outgroup_coop,
        'ingroup_attack': ingroup_attack,
        'outgroup_attack': outgroup_attack,
        'ingroup_cooperation_rate': safe_rate(ingroup_coop, total_coop),
        'outgroup_cooperation_rate': safe_rate(outgroup_coop, total_coop),
        'ingroup_attack_rate': safe_rate(ingroup_attack, total_attack),
        'outgroup_attack_rate': safe_rate(outgroup_attack, total_attack),
        'ei_index': ei_index(total_outgroup, total_ingroup),
        'ei_cooperation': ei_index(outgroup_coop, ingroup_coop),
        'ei_conflict': ei_index(outgroup_attack, ingroup_attack),
        'n_communities': len(partition),
        'community_sizes': sorted([len(c) for c in partition], reverse=True),
    }


def analyze_run_networks(history: List[Dict],
                        window_size: int = 5,
                        resolution: float = 1.0) -> Dict[str, Any]:
    """
    Run the full network analysis pipeline on a single run's history.

    Args:
        history: List of round dicts with actions and combat results.
        window_size: Size of sliding windows for temporal analysis.
        resolution: Resolution parameter for community detection.

    Returns:
        Comprehensive dict containing:
            - 'windowed_networks': list of network snapshots
            - 'metrics_per_window': list of structural metrics
            - 'communities_per_window': list of community partitions
            - 'community_stability': temporal stability measures
            - 'hierarchy_metrics': dominance hierarchy analysis
            - 'elo_ratings': Elo rating dynamics
    """
    # Build windowed networks
    windowed_networks = build_windowed_networks(history, window_size)

    # Compute metrics per window
    metrics_per_window = []
    for window_data in windowed_networks:
        full_net = window_data['full_network']
        metrics = network_metrics(full_net)
        metrics['window'] = window_data['window']
        metrics_per_window.append(metrics)

    # Detect communities per window + ingroup/outgroup
    communities_per_window = []
    partitions_for_stability = []
    ingroup_outgroup_per_window = []

    for window_data in windowed_networks:
        full_net = window_data['full_network']
        community_results = detect_communities(full_net, resolution_values=[resolution])
        partition = community_results['best_partition']

        communities_per_window.append({
            'window': window_data['window'],
            'partition': partition,
            'modularity': community_results.get(f'resolution_{resolution}', {}).get('modularity', 0.0),
            'n_communities': len(partition),
        })
        partitions_for_stability.append(partition)

        # Ingroup/outgroup for this window
        ig_og = compute_ingroup_outgroup(
            history, partition, window=window_data['window']
        )
        ig_og['window'] = window_data['window']
        ingroup_outgroup_per_window.append(ig_og)

    # Compute community stability
    stability = community_stability(partitions_for_stability)

    # Compute hierarchy metrics
    hierarchy = hierarchy_metrics(history)

    # Compute Elo ratings
    elo = compute_elo_ratings(history)

    # Compute overall ingroup/outgroup using last window's partition
    if partitions_for_stability:
        overall_ig_og = compute_ingroup_outgroup(history, partitions_for_stability[-1])
    else:
        overall_ig_og = compute_ingroup_outgroup(history, [])

    return {
        'windowed_networks': windowed_networks,
        'metrics_per_window': metrics_per_window,
        'communities_per_window': communities_per_window,
        'community_stability': stability,
        'hierarchy_metrics': hierarchy,
        'elo_ratings': elo,
        'ingroup_outgroup_per_window': ingroup_outgroup_per_window,
        'ingroup_outgroup_overall': overall_ig_og,
    }
