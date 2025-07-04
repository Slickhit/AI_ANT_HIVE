import json
import os
import random
from typing import Tuple

import tkinter as tk

from ..constants import (
    ANT_SIZE,
    ENERGY_MAX,
    MOVE_ENERGY_COST,
    DIG_ENERGY_COST,
    REST_ENERGY_GAIN,
    MOVE_STEP,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PALETTE,
)
from ..sprites import ANT_SPRITES
from ..terrain import (
    Terrain,
    TILE_SIZE,
    TILE_SAND,
    TILE_TUNNEL,
    TILE_ROCK,
    TILE_COLLAPSED,
)
from ..ai_interface import chat_completion


class BaseAnt:
    def __init__(
        self, sim: "AntSim", x: int, y: int, color: str = "black", energy: int = 100
    ) -> None:
        self.sim = sim
        self.color = color
        self.item: int = sim.canvas.create_rectangle(
            x,
            y,
            x + ANT_SIZE,
            y + ANT_SIZE,
            outline="",
            fill="",
        )
        self.image_id = sim.canvas.create_image(
            x,
            y,
            image=ANT_SPRITES[0],
            anchor="nw",
        )
        self.sprite_frames = ANT_SPRITES
        self.frame_index = 0

        self.energy_bar_bg = sim.canvas.create_rectangle(
            x,
            y + 4,
            x + ANT_SIZE,
            y + 2,
            fill=PALETTE["bar_bg"],
        )
        self.energy_bar = sim.canvas.create_rectangle(
            x,
            y + 4,
            x + ANT_SIZE,
            y + 2,
            fill=PALETTE["bar_green"],
        )

        self.carrying_food: bool = False
        self.energy: float = min(ENERGY_MAX, energy)
        self.alive: bool = True
        self.status: str = "Active"
        self.command: str | None = None
        self.role: str = self.__class__.__name__
        self.ant_id: int = self.item
        self.terrain: Terrain | None = getattr(sim, "terrain", None)

    def attempt_move(self, dx: int, dy: int) -> None:
        if self.energy <= 0:
            return
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
        new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))

        cost = MOVE_ENERGY_COST
        if self.terrain:
            # Check the tile the ant is currently on and convert sand to a tunnel
            tile_x_current = int((x1 + ANT_SIZE / 2) // TILE_SIZE)
            tile_y_current = int((y1 + ANT_SIZE / 2) // TILE_SIZE)
            if self.terrain.get_cell(tile_x_current, tile_y_current) == TILE_SAND:
                self.terrain.set_cell(tile_x_current, tile_y_current, TILE_TUNNEL)

            tile_x = int((new_x1 + ANT_SIZE / 2) // TILE_SIZE)
            tile_y = int((new_y1 + ANT_SIZE / 2) // TILE_SIZE)
            tile = self.terrain.get_cell(tile_x, tile_y)
            if tile in (TILE_ROCK, TILE_COLLAPSED):
                return
            if tile == TILE_SAND:
                self.terrain.set_cell(tile_x, tile_y, TILE_TUNNEL)
                cost += 1
        if self.energy < cost:
            return
        self.energy -= cost
        dx_move = new_x1 - x1
        dy_move = new_y1 - y1
        self.sim.canvas.move(self.item, dx_move, dy_move)
        self.sim.canvas.move(self.image_id, dx_move, dy_move)

    def move_random(self) -> None:
        dx = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        dy = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        self.attempt_move(dx, dy)

    def move_towards(self, target: int) -> None:
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        tx1, ty1, _, _ = self.sim.canvas.coords(target)
        dx = MOVE_STEP if x1 < tx1 else -MOVE_STEP if x1 > tx1 else 0
        dy = MOVE_STEP if y1 < ty1 else -MOVE_STEP if y1 > ty1 else 0
        self.attempt_move(dx, dy)

    def consume_energy(self, amount: int) -> None:
        self.energy = max(0, self.energy - amount)

    def rest(self) -> None:
        self.energy = min(ENERGY_MAX, self.energy + REST_ENERGY_GAIN)

    def dig(self) -> None:
        self.consume_energy(DIG_ENERGY_COST)

    def die(self) -> None:
        """Remove the ant from the simulation."""
        if not self.alive:
            return
        self.alive = False
        if hasattr(self.sim, "ants") and self in self.sim.ants:
            self.sim.ants.remove(self)
        for item in [self.item, self.image_id, self.energy_bar_bg, self.energy_bar]:
            try:
                self.sim.canvas.delete(item)
            except Exception:
                pass

    def energy_color(self) -> str:
        if self.energy > 60:
            return PALETTE.get("bar_green", "#4caf50")
        if self.energy > 30:
            return PALETTE.get("bar_yellow", "#c4b000")
        return PALETTE.get("bar_red", "#8b0000")

    def update_energy_bar(self) -> None:
        x1, y1, x2, _ = self.sim.canvas.coords(self.item)
        self._set_coords(self.energy_bar_bg, x1, y1 - 4, x2, y1 - 2)
        width = (self.energy / ENERGY_MAX) * (x2 - x1)
        self._set_coords(self.energy_bar, x1, y1 - 4, x1 + width, y1 - 2)
        self.sim.canvas.itemconfigure(self.energy_bar, fill=self.energy_color())

    def _set_coords(
        self, item: int, x1: float, y1: float, x2: float, y2: float
    ) -> None:
        try:
            self.sim.canvas.coords(item, x1, y1, x2, y2)
        except TypeError:
            if hasattr(self.sim.canvas, "objects"):
                self.sim.canvas.objects[item] = [x1, y1, x2, y2]

    def update_visibility(self) -> None:
        """Hide or show the ant based on the terrain cell under it."""
        if not self.terrain:
            return
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        tx = int(cx // TILE_SIZE)
        ty = int(cy // TILE_SIZE)
        visible = self.terrain.get_cell(tx, ty) == TILE_TUNNEL
        state = "normal" if visible else "hidden"
        for item in (
            self.item,
            self.image_id,
            self.energy_bar_bg,
            self.energy_bar,
        ):
            try:
                self.sim.canvas.itemconfigure(item, state=state)
            except Exception:
                pass

    def update(self) -> None:
        if not self.alive:
            return
        if self.energy <= 0:
            self.die()
            return

        self.move_random()
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])
        self.frame_index = (self.frame_index + 1) % len(self.sprite_frames)
        self.sim.canvas.itemconfigure(
            self.image_id, image=self.sprite_frames[self.frame_index]
        )
        from ..constants import ENERGY_DECAY

        self.energy = max(0, self.energy - ENERGY_DECAY)
        if self.energy <= 0:
            self.die()
        self.update_visibility()


class AIBaseAnt(BaseAnt):
    """Ant that decides movement using the OpenAI API."""

    def __init__(
        self,
        sim: "AntSim",
        x: int,
        y: int,
        color: str = "black",
        model: str | None = None,
    ) -> None:
        super().__init__(sim, x, y, color)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self._future = None

    def get_ai_move(self) -> Tuple[int, int]:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return random.choice([-MOVE_STEP, 0, MOVE_STEP]), random.choice(
                [-MOVE_STEP, 0, MOVE_STEP]
            )
        food_item = getattr(self.sim, "food", None)
        food_coords = (
            self.sim.canvas.coords(food_item) if food_item is not None else [0, 0, 0, 0]
        )
        state = {
            "ant": self.sim.canvas.coords(self.item),
            "food": food_coords,
            "queen": self.sim.canvas.coords(self.sim.queen.item),
        }
        messages = [
            {
                "role": "system",
                "content": 'You control an ant in a grid. Respond with JSON like {"dx":5,"dy":0}.',
            },
            {"role": "user", "content": json.dumps(state)},
        ]
        if self._future is None:
            self._future = chat_completion(messages, self.model, 10)
            return 0, 0
        if self._future.done():
            result = self._future.result()
            self._future = None
            if result:
                try:
                    data = json.loads(result)
                    return int(data.get("dx", 0)), int(data.get("dy", 0))
                except Exception:
                    pass
        return 0, 0

    def update(self) -> None:
        if not self.alive:
            return
        if self.energy <= 0:
            self.die()
            return
        dx, dy = self.get_ai_move()
        self.attempt_move(dx, dy)
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])
        from ..constants import ENERGY_DECAY

        self.energy = max(0, self.energy - ENERGY_DECAY)
        if self.energy <= 0:
            self.die()
        self.update_visibility()
