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

    def rewire(self, bilateral_flows_history: List[Dict]) -> dict:
        """
        Bilateral payoff-based rewiring (Zimmermann & Eguíluz, 2004).

        Each agent rewires with probability w:
          1. Compute cumulative bilateral payoff per neighbour over the
             payoff window: how much did this neighbour GIVE me (invest_other)
             minus how much did they TAKE from me (attack wins)?
          2. Drop the neighbour with the lowest bilateral payoff
          3. Add a random non-neighbour

        This is unilateral: either side of an edge can sever it. A "bully"
        wants to keep a victim (high payoff), but the victim can leave
        (negative payoff from being attacked). This naturally produces
        cooperator clustering and defector isolation.

        Constraints: break-one-make-one (edge conservation), min degree >= 1.

        Args:
            bilateral_flows_history: List of bilateral_flows dicts from
                recent rounds (most recent last). Each dict maps
                (from_agent, to_agent) -> net resource flow (positive =
                gave resources via invest, negative = took via attack).

        Returns:
            Dict with rewiring stats: {edges_dropped, edges_added, agents_rewired}
        """
        if self.rewiring_prob <= 0 or self.n <= 2:
            return {"edges_dropped": 0, "edges_added": 0, "agents_rewired": 0}

        # Use the last payoff_window rounds
        window = bilateral_flows_history[-self.payoff_window:]

        # Compute cumulative bilateral payoff: what did each neighbour
        # do FOR me over the window?
        #
        # Convention: flows[(A, B)] > 0 means resources moved from A to B.
        # Two types of flow:
        #   invest_other: voluntary — A chose to give to B. Positive for B.
        #   combat: involuntary — loser's resources flow to winner.
        #
        # We track BOTH sides so agents can evaluate neighbors properly:
        #   - Received investment from X → X is valuable (+)
        #   - Lost combat resources to X → X is harmful (-)
        #   - Gave investment to X → my choice, doesn't affect X's score
        #   - Won combat against X → X was profitable (+)
        #
        # Implementation: use separate invest/combat flow dicts in engine,
        # but since we only have total flows here, we use a simpler rule:
        #   payoff[me][them] = flows[(them, me)] - flows[(me, them)]
        # This means:
        #   Mutual invest: A→B=3, B→A=3 → payoff[A][B]=3-3=0 (neutral)
        #   One-way invest: A→B=3 → payoff[B][A]=3 (B likes A), payoff[A][B]=-3
        #
        # Problem: one-way invest penalizes the investor. But that's actually
        # correct for rewiring: if I invest in you and you never reciprocate,
        # I SHOULD drop you and find someone who does.
        bilateral_payoff: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for flows in window:
            for (from_id, to_id), amount in flows.items():
                bilateral_payoff[to_id][from_id] += amount
                bilateral_payoff[from_id][to_id] -= amount

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
                # Can't drop only neighbour (min degree >= 1)
                continue

            # Find non-neighbours
            non_neighbors = [
                x for x in self.agent_ids
                if x != aid and x not in self.adj[aid]
            ]
            if not non_neighbors:
                # Fully connected — can't add new edge
                continue

            # Find neighbour who gave me the least (or took the most)
            # Skip neighbours who would be left at degree 0 if dropped
            droppable = [x for x in neighbors if len(self.adj[x]) > 1]
            if not droppable:
                continue
            worst_neighbor = min(
                droppable,
                key=lambda x: bilateral_payoff[aid].get(x, 0.0)
            )

            # Pick best non-neighbour (highest bilateral payoff) — connect
            # to whoever has been most beneficial. Falls back to random if
            # no interaction history exists with any non-neighbour.
            best_non = max(
                non_neighbors,
                key=lambda x: bilateral_payoff[aid].get(x, 0.0)
            )
            if bilateral_payoff[aid].get(best_non, 0.0) > 0:
                new_neighbor = best_non
            else:
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

    def restore_edges(self, edge_list: List):
        """Restore network from saved edge list (for resume)."""
        # Clear existing adjacency
        for aid in self.adj:
            self.adj[aid] = set()
        # Rebuild from edges
        for edge in edge_list:
            a, b = edge[0], edge[1]
            if a in self.adj and b in self.adj:
                self.adj[a].add(b)
                self.adj[b].add(a)

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
