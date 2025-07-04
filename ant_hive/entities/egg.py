from ..constants import ANT_SIZE


class Egg:
    """Represents an egg that will hatch into a new worker ant."""

    def __init__(self, sim: "AntSim", x: int, y: int, hatch_time: int = 200) -> None:
        self.sim = sim
        self.hatch_time = hatch_time
        self.item = sim.canvas.create_oval(x, y, x + ANT_SIZE, y + ANT_SIZE, fill="white")

    def update(self) -> None:
        self.hatch_time -= 1
        if self.hatch_time <= 0:
            x1, y1, _, _ = self.sim.canvas.coords(self.item)
            self.sim.canvas.delete(self.item)
            self.sim.eggs.remove(self)
            # Delegate role selection and spawning to the queen
            self.sim.queen.hatch_ant(int(x1), int(y1))
