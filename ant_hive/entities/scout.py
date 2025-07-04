from __future__ import annotations

import random

from ..constants import ANT_SIZE, MOVE_STEP, WINDOW_WIDTH, WINDOW_HEIGHT, SCOUT_PHEROMONE_AMOUNT
from .base_ant import BaseAnt


class ScoutAnt(BaseAnt):
    """Ant that explores randomly, remembering visited positions."""

    def __init__(self, sim: "AntSim", x: int, y: int, color: str = "black") -> None:
        super().__init__(sim, x, y, color)
        self.visited: set[tuple[float, float]] = {(float(x), float(y))}

    def update(self) -> None:
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        moves = []
        for dx in (-MOVE_STEP, 0, MOVE_STEP):
            for dy in (-MOVE_STEP, 0, MOVE_STEP):
                if dx == 0 and dy == 0:
                    continue
                new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
                new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))
                if (new_x1, new_y1) not in self.visited:
                    moves.append((dx, dy, new_x1, new_y1))
        if moves:
            dx, dy, new_x1, new_y1 = random.choice(moves)
            self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)
        else:
            self.move_random()
        coords = self.sim.canvas.coords(self.item)
        if hasattr(self.sim, "deposit_pheromone"):
            self.sim.deposit_pheromone(coords[0], coords[1], SCOUT_PHEROMONE_AMOUNT)
        self.last_pos = (coords[0], coords[1])
        self.visited.add(self.last_pos)
