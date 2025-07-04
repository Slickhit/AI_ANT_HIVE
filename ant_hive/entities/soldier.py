import random

from ..constants import ANT_SIZE, MOVE_STEP, WINDOW_WIDTH, WINDOW_HEIGHT
from ..terrain import TILE_SIZE
from .base_ant import BaseAnt


class SoldierAnt(BaseAnt):
    """Simple soldier ant that patrols around the queen."""

    def update(self) -> None:
        if getattr(self.sim, "is_night", False):
            self.move_towards(self.sim.queen.item)
            coords = self.sim.canvas.coords(self.item)
            self.last_pos = (coords[0], coords[1])
            return
        if self.energy <= 0:
            self.rest()
        else:
            qx1, qy1, qx2, qy2 = self.sim.canvas.coords(self.sim.queen.item)
            ax1, ay1, _, _ = self.sim.canvas.coords(self.item)
            cx = (qx1 + qx2) / 2
            cy = (qy1 + qy2) / 2
            if abs(ax1 - cx) > TILE_SIZE * 3 or abs(ay1 - cy) > TILE_SIZE * 3:
                self.move_towards(self.sim.queen.item)
            else:
                self.move_random()
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])
