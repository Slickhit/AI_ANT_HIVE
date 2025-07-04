from __future__ import annotations
import random

from ..constants import ANT_SIZE, MOVE_STEP, WINDOW_WIDTH, WINDOW_HEIGHT, PALETTE
from .base_ant import BaseAnt


class SpiderBrain:
    """Very small neural controller for spider movement."""

    def __init__(self) -> None:
        self.weights = [[0.5, -0.25, 0.3], [-0.25, 0.5, 0.3]]

    def decide(self, inputs: tuple[float, float, float]) -> tuple[int, int]:
        raw = []
        for row in self.weights:
            val = sum(i * w for i, w in zip(inputs, row))
            raw.append(val)
        dx = MOVE_STEP if raw[0] > 0.1 else -MOVE_STEP if raw[0] < -0.1 else 0
        dy = MOVE_STEP if raw[1] > 0.1 else -MOVE_STEP if raw[1] < -0.1 else 0
        return dx, dy


class Spider:
    """Predator equipped with a simple neural network brain."""

    def __init__(self, sim: "AntSim", x: int, y: int, energy: int = 50, health: int = 30) -> None:
        self.sim = sim
        self.energy = energy
        self.health = health
        self.vitality = float(health)
        self.hunger = 0
        self.consumed = 0
        self.brain = SpiderBrain()
        self.item = sim.canvas.create_oval(x, y, x + ANT_SIZE, y + ANT_SIZE, fill="brown")
        self.life_bar_bg = sim.canvas.create_rectangle(x, y - 4, x + ANT_SIZE, y - 2, fill=PALETTE["bar_bg"])
        self.life_bar = sim.canvas.create_rectangle(x, y - 4, x + ANT_SIZE, y - 2, fill=PALETTE["bar_green"])
        self.hunger_bar_bg = sim.canvas.create_rectangle(x, y + ANT_SIZE + 2, x + ANT_SIZE, y + ANT_SIZE + 4, fill=PALETTE["bar_bg"])
        self.hunger_bar = sim.canvas.create_rectangle(x, y + ANT_SIZE + 2, x + ANT_SIZE, y + ANT_SIZE + 4, fill=PALETTE["bar_green"])
        self.visible = True

    def set_visible(self, visible: bool) -> None:
        """Show or hide the spider and its UI elements."""
        state = "normal" if visible else "hidden"
        for item in (
            self.item,
            self.life_bar_bg,
            self.life_bar,
            self.hunger_bar_bg,
            self.hunger_bar,
        ):
            self.sim.canvas.itemconfigure(item, state=state)
        self.visible = visible

    def life_color(self) -> str:
        if self.vitality > 60:
            return PALETTE["bar_green"]
        if self.vitality > 30:
            return PALETTE["bar_yellow"]
        return PALETTE["bar_red"]

    def hunger_color(self) -> str:
        if self.hunger < 3:
            return PALETTE["bar_green"]
        if self.hunger < 6:
            return PALETTE["bar_yellow"]
        return PALETTE["bar_red"]

    def update_bars(self) -> None:
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        self.sim.canvas.coords(self.life_bar_bg, x1, y1 - 4, x2, y1 - 2)
        width = (self.vitality / self.health) * (x2 - x1)
        self.sim.canvas.coords(self.life_bar, x1, y1 - 4, x1 + width, y1 - 2)
        self.sim.canvas.itemconfigure(self.life_bar, fill=self.life_color())
        self.sim.canvas.coords(self.hunger_bar_bg, x1, y2 + 2, x2, y2 + 4)
        hwidth = min(1.0, self.hunger / 10) * (x2 - x1)
        self.sim.canvas.coords(self.hunger_bar, x1, y2 + 2, x1 + hwidth, y2 + 4)
        self.sim.canvas.itemconfigure(self.hunger_bar, fill=self.hunger_color())

    def brain_move(self) -> None:
        if not self.sim.ants:
            return
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        ant = min(self.sim.ants, key=lambda a: ((self.sim.canvas.coords(a.item)[0] - cx) ** 2 + (self.sim.canvas.coords(a.item)[1] - cy) ** 2))
        ax1, ay1, ax2, ay2 = self.sim.canvas.coords(ant.item)
        ax = (ax1 + ax2) / 2
        ay = (ay1 + ay2) / 2
        dx_in = ax - cx
        dy_in = ay - cy
        inputs = (dx_in, dy_in, float(self.hunger))
        dx, dy = self.brain.decide(inputs)
        new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
        new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))
        self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)

    def attack_ants(self) -> None:
        for ant in self.sim.ants[:]:
            if self.sim.check_collision(self.item, ant.item):
                ant.consume_energy(20)
                if ant.energy <= 0:
                    self.sim.canvas.delete(ant.item)
                    if hasattr(ant, "image_id"):
                        self.sim.canvas.delete(ant.image_id)
                    self.sim.ants.remove(ant)
                    self.consumed += 1
                    if self.consumed % 3 == 0:
                        self.hunger += 1

    def update(self) -> None:
        if self.vitality <= 0:
            if self in self.sim.predators:
                self.sim.predators.remove(self)
            for item in (self.item, self.life_bar_bg, self.life_bar, self.hunger_bar_bg, self.hunger_bar):
                self.sim.canvas.delete(item)
            return
        self.vitality -= 0.05
        if getattr(self.sim, "is_night", True):
            self.brain_move()
            self.attack_ants()
        self.update_bars()
