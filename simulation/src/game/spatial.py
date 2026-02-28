"""
Spatial field for multi-agent game.
2D toroidal grid where agents move and interact locally.
"""

import numpy as np
from typing import Dict, List, Tuple


class SpatialField:
    """
    2D toroidal grid. Agents occupy cells and can only interact
    with others within an interaction radius. Edges wrap around.
    """

    def __init__(self, grid_size: int, agent_ids: List[str], interaction_radius: int = 2):
        self.grid_size = grid_size
        self.interaction_radius = interaction_radius
        self.positions: Dict[str, Tuple[int, int]] = {}

        # Place agents randomly (no two on the same cell)
        all_cells = [(r, c) for r in range(grid_size) for c in range(grid_size)]
        chosen = np.random.choice(len(all_cells), size=len(agent_ids), replace=False)
        for i, agent_id in enumerate(agent_ids):
            self.positions[agent_id] = all_cells[chosen[i]]

    def move_agents(self):
        """Move each agent to a random adjacent cell (8-directional + stay). Toroidal wrapping."""
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1),  (0, 0),  (0, 1),
                      (1, -1),  (1, 0),  (1, 1)]

        occupied = set(self.positions.values())

        for agent_id in list(self.positions.keys()):
            r, c = self.positions[agent_id]
            # Try random direction; if occupied, stay put
            dr, dc = directions[np.random.randint(len(directions))]
            new_r = (r + dr) % self.grid_size
            new_c = (c + dc) % self.grid_size

            if (new_r, new_c) not in occupied or (new_r, new_c) == (r, c):
                occupied.discard((r, c))
                self.positions[agent_id] = (new_r, new_c)
                occupied.add((new_r, new_c))

    def get_neighbors(self, agent_id: str) -> List[str]:
        """Get agents within interaction radius (toroidal distance)."""
        r1, c1 = self.positions[agent_id]
        neighbors = []

        for other_id, (r2, c2) in self.positions.items():
            if other_id == agent_id:
                continue
            dist = self._toroidal_distance(r1, c1, r2, c2)
            if dist <= self.interaction_radius:
                neighbors.append(other_id)

        return neighbors

    def _toroidal_distance(self, r1: int, c1: int, r2: int, c2: int) -> float:
        """Chebyshev distance on a torus (max of wrapped row/col distance)."""
        dr = min(abs(r1 - r2), self.grid_size - abs(r1 - r2))
        dc = min(abs(c1 - c2), self.grid_size - abs(c1 - c2))
        return max(dr, dc)

    def get_position(self, agent_id: str) -> Tuple[int, int]:
        return self.positions[agent_id]

    def get_all_positions(self) -> Dict[str, Tuple[int, int]]:
        return self.positions.copy()
