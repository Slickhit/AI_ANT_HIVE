from __future__ import annotations

import random

from ..constants import ANT_SIZE
from .base_ant import BaseAnt


class NurseAnt(BaseAnt):
    """Ant that tends to the queen, feeding her when nearby."""

    def update(self) -> None:
        if self.energy <= 0:
            self.rest()
        else:
            self.move_towards(self.sim.queen.item)
            if self.sim.check_collision(self.item, self.sim.queen.item):
                self.sim.queen.feed()
                if hasattr(self.sim, "queen_fed"):
                    self.sim.queen.fed += 1
                    self.sim.queen_fed += 1
                if random.random() < 0.3:
                    qx1, qy1, _, _ = self.sim.canvas.coords(self.sim.queen.item)
                    self.sim.queen.lay_egg(int(qx1 + 20), int(qy1))
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])
