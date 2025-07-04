from __future__ import annotations
import random

from ..constants import (
    ANT_SIZE,
    MOVE_STEP,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PALETTE,
)
from ..utils import brightness_at
from .base_ant import BaseAnt

from .base_ant import BaseAnt

BASE_SPEED = MOVE_STEP
BASE_CONSUMPTION = 1.0


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


class Den:
    """Simple object that spawns spiderlings at creation."""

    def __init__(self, sim: "AntSim", x: int, y: int, count: int = 3) -> None:
        self.sim = sim
        self.item = sim.canvas.create_oval(x, y, x + ANT_SIZE, y + ANT_SIZE, fill="gray")
        for _ in range(count):
            spiderling = Spider(sim, x, y, energy=20, health=10, size=0.5)
            sim.predators.append(spiderling)


class Spider:
    """Predator equipped with a simple neural network brain."""

    def __init__(self, sim: "AntSim", x: int, y: int, energy: int = 50, health: int = 30, size: float = 1.0) -> None:
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
        self.sense_label: int | None = None
        self.visible = True

        self.visible = True
        self.size = size
        self.speed = BASE_SPEED * self.size
        self.food_consumption = BASE_CONSUMPTION * self.size
        self.has_laid_eggs = False
        self.alive = True
        self.last_is_night = True

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

    def _maybe_show_sense_label(self, cx: float, cy: float) -> None:
        """Display or move the 'Sensing...' label when hunting at night."""
        import time

        brightness = brightness_at(time.time() - getattr(self.sim, "start_time", 0))
        is_night = brightness < 0.8

        if is_night and self.sim.ants:
            # find distance to nearest ant
            nearest = min(
                (
                    (self.sim.canvas.coords(a.item)[0] - cx) ** 2
                    + (self.sim.canvas.coords(a.item)[1] - cy) ** 2
                )
                ** 0.5
                for a in self.sim.ants
            )
            if nearest < 150:
                if self.sense_label is None:
                    self.sense_label = self.sim.canvas.create_text(
                        cx,
                        cy - 15,
                        text="Sensing...",
                        fill="#ff4444",
                        font=("Helvetica", 8),
                    )
                else:
                    self.sim.canvas.coords(self.sense_label, cx, cy - 15)
                return

        if self.sense_label is not None:
            self.sim.canvas.delete(self.sense_label)
            self.sense_label = None

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
        scale = self.speed / MOVE_STEP
        dx *= scale
        dy *= scale
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
            self.alive = False
            if not self.has_laid_eggs:
                self.lay_eggs()
                self.has_laid_eggs = True
            if self in self.sim.predators:
                self.sim.predators.remove(self)
            for item in (
                self.item,
                self.life_bar_bg,
                self.life_bar,
                self.hunger_bar_bg,
                self.hunger_bar,
            ):
                self.sim.canvas.delete(item)
            return
        self.vitality -= 0.05 * self.food_consumption
        if not getattr(self.sim, "is_night", True) and self.last_is_night:
            self.sleep_cycle()
        self.last_is_night = getattr(self.sim, "is_night", True)
        if getattr(self.sim, "is_night", True):
            self.brain_move()
            self.attack_ants()
        self.update_bars()
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self._maybe_show_sense_label(cx, cy)

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self._maybe_show_sense_label(cx, cy)


    def lay_eggs(self) -> None:
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        x = int((x1 + x2) / 2)
        y = int((y1 + y2) / 2)
        Den(self.sim, x, y)

    def sleep_cycle(self) -> None:
        self.grow()

    def grow(self) -> None:
        self.size *= 1.20
        self.speed = BASE_SPEED * self.size
        self.food_consumption = BASE_CONSUMPTION * self.size
