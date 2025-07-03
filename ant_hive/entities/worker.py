import random

from ..constants import (
    ANT_SIZE,
    ENERGY_MAX,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from ..terrain import TILE_SIZE
from .base_ant import BaseAnt
from ..terrain import TILE_SIZE, TILE_TUNNEL, TILE_SAND, TILE_ROCK, TILE_COLLAPSED


class WorkerAnt(BaseAnt):
    """Ant focused on collecting food and feeding the queen."""

    def update(self) -> None:
        if self.energy <= 0:
            self.rest()
            coords = self.sim.canvas.coords(self.item)
            self.last_pos = (coords[0], coords[1])
            return
        start = self.sim.canvas.coords(self.item)
        best_dir = None
        best_value = -1.0
        if not self.carrying_food:
            for drop in getattr(self.sim, "food_drops", []):
                if self.sim.check_collision(self.item, drop.item):
                    if drop.take_charge():
                        self.energy = min(ENERGY_MAX, self.energy + 20)
                        self.carrying_food = True
                        cx = start[0] + ANT_SIZE / 2
                        cy = start[1] + ANT_SIZE / 2
                        self.sim.sparkle(cx, cy)
                    if drop.charges <= 0:
                        self.sim.food_drops.remove(drop)
                    break
            if not self.carrying_food:
                x1, y1, _, _ = self.sim.canvas.coords(self.item)
                for dx in (-TILE_SIZE, 0, TILE_SIZE):
                    for dy in (-TILE_SIZE, 0, TILE_SIZE):
                        if dx == 0 and dy == 0:
                            continue
                        nx = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
                        ny = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))
                        val = self.sim.get_pheromone(nx, ny)
                        if val > best_value:
                            best_value = val
                            best_dir = (nx - x1, ny - y1)
            if best_value > 0 and best_dir is not None:
                self.sim.canvas.move(self.item, best_dir[0], best_dir[1])
                self.sim.canvas.move(self.image_id, best_dir[0], best_dir[1])
            else:
                self.move_towards(self.sim.food)
            if self.sim.check_collision(self.item, self.sim.food):
                self.carrying_food = True
                self.sim.food_collected += 1
                self.sim.move_food()
                cx = start[0] + ANT_SIZE / 2
                cy = start[1] + ANT_SIZE / 2
                self.sim.sparkle(cx, cy)
        else:
            self.move_towards(self.sim.queen.item)
            if self.sim.check_collision(self.item, self.sim.queen.item):
                self.sim.queen.feed()
                self.sim.queen.fed += 1
                self.sim.queen_fed += 1
                if random.random() < 0.3:
                    qx1, qy1, _, _ = self.sim.canvas.coords(self.sim.queen.item)
                    self.sim.queen.lay_egg(int(qx1 + 20), int(qy1))
                self.carrying_food = False
                coords = self.sim.canvas.coords(self.item)
                cx = coords[0] + ANT_SIZE / 2
                cy = coords[1] + ANT_SIZE / 2
                self.sim.sparkle(cx, cy)
        coords = self.sim.canvas.coords(self.item)
        if coords[:2] != start[:2]:
            x1 = start[0] + ANT_SIZE / 2
            y1 = start[1] + ANT_SIZE / 2
            x2 = coords[0] + ANT_SIZE / 2
            y2 = coords[1] + ANT_SIZE / 2
            trail = self.sim.canvas.create_line(x1, y1, x2, y2, fill=self.color)
            self.sim.canvas.after(300, lambda t=trail: self.sim.canvas.delete(t))
        self.last_pos = (coords[0], coords[1])
