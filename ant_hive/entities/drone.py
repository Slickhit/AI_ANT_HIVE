from __future__ import annotations

from ..constants import ANT_SIZE
from .base_ant import BaseAnt


class DroneAnt(BaseAnt):
    """Simple breeder ant that can mate with the queen."""

    def __init__(self, sim: "AntSim", x: int, y: int, color: str = "purple", energy: int = 100) -> None:
        super().__init__(sim, x, y, color, energy)
        self.role = "Drone"
        self.cooldown = 0

    def update(self) -> None:
        if self.energy <= 0 or getattr(self, "alive", True) is False:
            return
        if self.cooldown > 0:
            self.cooldown -= 1
        self.move_random()
        qx1, qy1, qx2, qy2 = self.sim.canvas.coords(self.sim.queen.item)
        ax1, ay1, ax2, ay2 = self.sim.canvas.coords(self.item)
        close = (abs((ax1 + ax2) / 2 - (qx1 + qx2) / 2) <= ANT_SIZE and
                 abs((ay1 + ay2) / 2 - (qy1 + qy2) / 2) <= ANT_SIZE)
        if close and self.cooldown <= 0 and getattr(self.sim.queen, "ready_to_mate", True):
            if getattr(self.sim.queen, "begin_reproduction_cycle", None):
                self.sim.queen.begin_reproduction_cycle()
            self.cooldown = int(getattr(self.sim.queen, "base_spawn_time", 300))
