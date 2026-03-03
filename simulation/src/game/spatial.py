"""
Dynamic social network for multi-agent game.
Replaces the 2D toroidal grid with an Erdős-Rényi graph
and optional payoff-based rewiring.

Design references:
- Zimmermann & Eguíluz (2004, PRE 69:065102): payoff-based rewiring.
  Agents sever ties with low-payoff neighbours and form new ties randomly.
  Produces emergent hierarchy and positive assortment of cooperators.
- Santos, Pacheco & Lenaerts (2006, PLoS Comp Bio): co-evolutionary
  dynamics on adaptive networks. Dynamic topology promotes cooperation.
- Rand, Arbesman & Christakis (2011, PNAS): experimental validation
  with human subjects. Static → viscous → fluid → fully dynamic spectrum.
- Gross & Blasius (2008, J. R. Soc. Interface): adaptive networks review.
"""

import numpy as np
from typing import Dict, List, Optional
from collections import defaultdict


class NetworkTopology:
    """
    Dynamic social network. Agents are connected via an undirected graph
    that co-evolves with their interactions through payoff-based rewiring.

    Interface (drop-in replacement for SpatialField):
        get_neighbors(agent_id) -> List[str]
        rewire(payoff_history) -> dict   # replaces move_agents()
        get_edge_list() -> List[tuple]
        get_adjacency() -> Dict[str, set]
    """

    def __init__(self, agent_ids: List[str],
                 mean_degree: float = 5.0,
                 rewiring_prob: float = 0.0,
                 payoff_window: int = 5):
        """
        Args:
            agent_ids: List of agent ID strings.
            mean_degree: Expected degree ⟨k⟩ for the initial ER graph.
            rewiring_prob: Probability w that each agent rewires per round.
                w=0: static, w=0.05: viscous, w=0.3: fluid, w=1.0: fully dynamic.
            payoff_window: Number of past rounds used for cumulative payoff
                when selecting which neighbour to drop.
        """
        self.agent_ids = list(agent_ids)
        self.n = len(self.agent_ids)
        self.rewiring_prob = rewiring_prob
        self.payoff_window = payoff_window

        # Adjacency as dict of sets (undirected)
        self.adj: Dict[str, set] = {aid: set() for aid in self.agent_ids}

        # Build initial ER graph G(n, p) with connected component guarantee
        self._init_er_graph(mean_degree)

    def _init_er_graph(self, mean_degree: float):
        """Initialize Erdős-Rényi G(n, p) ensuring a connected graph."""
        if self.n <= 1:
            return

        p = mean_degree / (self.n - 1)
        p = min(p, 1.0)

        # Try ER generation; if not connected, add edges to connect components
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if np.random.random() < p:
                    self.adj[self.agent_ids[i]].add(self.agent_ids[j])
                    self.adj[self.agent_ids[j]].add(self.agent_ids[i])

        # Ensure connectivity via random spanning tree on disconnected components
        self._ensure_connected()

        # Ensure minimum degree ≥ 1 (should be satisfied after connectivity fix)
        for aid in self.agent_ids:
            if len(self.adj[aid]) == 0:
                # Connect to a random other agent
                others = [x for x in self.agent_ids if x != aid]
                target = others[np.random.randint(len(others))]
                self.adj[aid].add(target)
                self.adj[target].add(aid)

    def _ensure_connected(self):
        """Add edges to connect disconnected components."""
        visited = set()
        components = []

        for aid in self.agent_ids:
            if aid not in visited:
                # BFS
                component = set()
                queue = [aid]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    component.add(node)
                    queue.extend(self.adj[node] - visited)
                components.append(component)

        # Connect components by linking a random node from each to the next
        for i in range(len(components) - 1):
            a = list(components[i])[np.random.randint(len(components[i]))]
            b = list(components[i + 1])[np.random.randint(len(components[i + 1]))]
            self.adj[a].add(b)
            self.adj[b].add(a)

    def get_neighbors(self, agent_id: str) -> List[str]:
        """Get direct neighbours of an agent."""
        return sorted(self.adj[agent_id])

    def rewire(self, resource_changes_history: List[Dict[str, float]]) -> dict:
        """
        Payoff-based rewiring (Zimmermann & Eguíluz, 2004).

        Each agent rewires with probability w:
          1. Compute cumulative payoff (net resource change) per neighbour
             over the payoff window
          2. Drop the lowest-payoff neighbour
          3. Add a random non-neighbour

        Constraints: break-one-make-one (edge conservation), min degree ≥ 1.

        Args:
            resource_changes_history: List of resource_changes dicts from
                recent rounds (most recent last). Each dict maps agent_id
                to net resource change that round.

        Returns:
            Dict with rewiring stats: {edges_dropped, edges_added, agents_rewired}
        """
        if self.rewiring_prob <= 0 or self.n <= 2:
            return {"edges_dropped": 0, "edges_added": 0, "agents_rewired": 0}

        # Use the last payoff_window rounds
        window = resource_changes_history[-self.payoff_window:]

        # Compute cumulative payoff per agent over the window
        cumulative_payoff: Dict[str, float] = defaultdict(float)
        for rc in window:
            for aid, change in rc.items():
                cumulative_payoff[aid] += change

        edges_dropped = 0
        edges_added = 0
        agents_rewired = 0

        # Process agents in random order
        order = list(self.agent_ids)
        np.random.shuffle(order)

        for aid in order:
            if np.random.random() >= self.rewiring_prob:
                continue

            neighbors = list(self.adj[aid])
            if len(neighbors) <= 1:
                # Can't drop only neighbour (min degree ≥ 1)
                continue

            # Find non-neighbours
            non_neighbors = [
                x for x in self.agent_ids
                if x != aid and x not in self.adj[aid]
            ]
            if not non_neighbors:
                # Fully connected — can't add new edge
                continue

            # Find lowest-payoff neighbour
            worst_neighbor = min(
                neighbors,
                key=lambda x: cumulative_payoff.get(x, 0.0)
            )

            # Pick random non-neighbour
            new_neighbor = non_neighbors[np.random.randint(len(non_neighbors))]

            # Sever edge with worst neighbour
            self.adj[aid].discard(worst_neighbor)
            self.adj[worst_neighbor].discard(aid)

            # Add edge with new neighbour
            self.adj[aid].add(new_neighbor)
            self.adj[new_neighbor].add(aid)

            edges_dropped += 1
            edges_added += 1
            agents_rewired += 1

        return {
            "edges_dropped": edges_dropped,
            "edges_added": edges_added,
            "agents_rewired": agents_rewired,
        }

    def get_edge_list(self) -> List[tuple]:
        """Return all edges as sorted list of (agent_a, agent_b) tuples."""
        edges = set()
        for aid, neighbors in self.adj.items():
            for nbr in neighbors:
                edge = tuple(sorted([aid, nbr]))
                edges.add(edge)
        return sorted(edges)

    def get_adjacency(self) -> Dict[str, set]:
        """Return a copy of the adjacency dict."""
        return {aid: set(nbrs) for aid, nbrs in self.adj.items()}

    def get_degree_stats(self) -> dict:
        """Return degree statistics for the current network."""
        degrees = [len(self.adj[aid]) for aid in self.agent_ids]
        return {
            "mean": float(np.mean(degrees)),
            "std": float(np.std(degrees)),
            "min": int(np.min(degrees)),
            "max": int(np.max(degrees)),
        }
