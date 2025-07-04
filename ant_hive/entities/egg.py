from __future__ import annotations

import random

from ..constants import ANT_SIZE
from .worker import WorkerAnt
from .scout import ScoutAnt
from .soldier import SoldierAnt
from .nurse import NurseAnt
from .drone import DroneAnt


def hatch_random_ant(sim: "AntSim", x: int, y: int):
    """Return a new ant instance using weighted role probabilities."""
    r = random.random()
    if r < 0.4:
        return WorkerAnt(sim, x, y, "blue")
    if r < 0.6:
        return ScoutAnt(sim, x, y, "black")
    if r < 0.8:
        return SoldierAnt(sim, x, y, "orange")
    if r < 0.95:
        return NurseAnt(sim, x, y, "pink")
    return DroneAnt(sim, x, y, "purple")


class Egg:
    """Represents an egg that hatches into a random ant role."""

    def __init__(self, sim: "AntSim", x: int, y: int, hatch_time: int = 200) -> None:
        self.sim = sim
        self.hatch_time = hatch_time
        self.item = sim.canvas.create_oval(
            x, y, x + ANT_SIZE, y + ANT_SIZE, fill="white"
        )

    def update(self) -> None:
        self.hatch_time -= 1
        if self.hatch_time <= 0:
            x1, y1, _, _ = self.sim.canvas.coords(self.item)
            self.sim.canvas.delete(self.item)
            self.sim.eggs.remove(self)
            # Delegate role selection and spawning to the queen
            ant = self.sim.queen.hatch_ant(int(x1), int(y1))
            if hasattr(self.sim, "log_event"):
                self.sim.log_event(f"Egg hatched into {ant.role}")
