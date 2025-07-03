from __future__ import annotations

import json
import os
import random
import tkinter as tk
from typing import List, Tuple

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    class _DummyChat:
        @staticmethod
        def create(*_args, **_kwargs):
            raise ModuleNotFoundError("openai is required for this feature")

    class _DummyOpenAI:
        api_key = ""
        ChatCompletion = _DummyChat

    openai = _DummyOpenAI()

# Constants
PALETTE = {
    "background": "#f4ecd8",
    "sidebar": "#eee1c6",
    "frame": "#d2b48c",
    "bar_bg": "#5a462e",
    "bar_green": "#4caf50",
    "bar_yellow": "#c4b000",
    "bar_red": "#8b0000",
    "neon_purple": "#d400ff",
}

MONO_FONT = ("JetBrains Mono", 10)
HEADER_FONT = ("JetBrains Mono", 10, "bold underline")

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# Window constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
SIDEBAR_WIDTH = 150
ANT_SIZE = 10
FOOD_SIZE = 8
MOVE_STEP = 5
PHEROMONE_DECAY = 0.01
SCOUT_PHEROMONE_AMOUNT = 1.0

# Animated sprite frames for ants. We avoid external binaries by generating
# simple images programmatically. When Tk isn't available (e.g. during tests)
# creation will fail and we fall back to `None` frames.
def _load_sprites() -> list[tk.PhotoImage | None]:
    try:
        frames: list[tk.PhotoImage] = []
        for i in range(2):
            img = tk.PhotoImage(width=ANT_SIZE, height=ANT_SIZE)
            body_color = "brown"
            for x in range(ANT_SIZE):
                for y in range(ANT_SIZE):
                    if 2 <= x < ANT_SIZE - 2 and 2 <= y < ANT_SIZE - 2:
                        img.put(body_color, (x, y))
            leg_y = ANT_SIZE - 2 + (0 if i == 0 else -1)
            img.put("black", (1, leg_y))
            img.put("black", (ANT_SIZE - 2, leg_y))
            frames.append(img)
        return frames
    except Exception:
        # During headless testing Tk may not be initialized.
        return [None, None]

ANT_SPRITES = _load_sprites()


# Utility to create a small glowing orb sprite
def create_glowing_icon(size: int = 16, inner: str = "#ffff99", outer: str = "#ff9900") -> tk.PhotoImage:
    """Return a circular gradient image used for food drops."""
    img = tk.PhotoImage(width=size, height=size)
    cx = cy = size / 2
    ir, ig, ib = int(inner[1:3], 16), int(inner[3:5], 16), int(inner[5:7], 16)
    or_, og, ob = int(outer[1:3], 16), int(outer[3:5], 16), int(outer[5:7], 16)
    max_d = (size / 2) ** 2
    for x in range(size):
        for y in range(size):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            t = min(1.0, (dx * dx + dy * dy) / max_d)
            r = int(ir + (or_ - ir) * t)
            g = int(ig + (og - ig) * t)
            b = int(ib + (ob - ib) * t)
            img.put(f"#{r:02x}{g:02x}{b:02x}", (x, y))
    return img


# Terrain constants
TILE_SIZE = 20
TILE_SAND = "sand"
TILE_TUNNEL = "tunnel"
TILE_ROCK = "rock"
TILE_COLLAPSED = "collapsed"

# Small base64 encoded textures to avoid binary files in the repository
SAND_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAARklEQVR4nO3QMRHAMBADwctjEPRg"
    "MgSjEAenyJiArfLVqdninjneZZs9Sdz8SmKSqCRm+wdTGEAlMeiGCbwbdsOD3w3v8Q8txS8qFa7u"
    "XQAAAABJRU5ErkJggg=="
)
TUNNEL_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAARklEQVR4nO3QMRHAMBADwctjEIsg"
    "NA/DFAenyJiArfLVqdninjneZZs9Sdz8SmKSqCRm+wdTGEAlMeiGCbwbdsOD3w3v8Q8OIi4y+xWE"
    "tQAAAABJRU5ErkJggg=="
)
ROCK_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAQklEQVR4nO3QsRHAQAwCwbNqoHO1"
    "SQ/+4McNWIQiI9ngnu5+bfNNEpNfSUwSlcRsXzCFAVQSg22YwLfhNvzxt+EcPz04LrP+YyCNAAAA"
    "AElFTkSuQmCC"
)

class Terrain:
    """Simple 2D grid representing the underground."""

    colors = {
        TILE_SAND: "#c2b280",
        TILE_TUNNEL: "#806517",
        TILE_ROCK: "#7f7f7f",
        TILE_COLLAPSED: "black",
    }

    texture_data = {
        TILE_SAND: SAND_TEXTURE,
        TILE_TUNNEL: TUNNEL_TEXTURE,
        TILE_ROCK: ROCK_TEXTURE,
    }

    def __init__(self, width: int, height: int, canvas: tk.Canvas) -> None:
        self.width = width
        self.height = height
        self.canvas = canvas
        self.images: dict[str, tk.PhotoImage | None] = {}
        for key, data in self.texture_data.items():
            try:
                self.images[key] = tk.PhotoImage(data=data)
            except Exception:
                # When running headless tests there may be no Tk instance
                self.images[key] = None
        self.grid: list[list[str]] = [
            [TILE_SAND for _ in range(height)] for _ in range(width)
        ]
        self.rects: list[list[int]] = [[0] * height for _ in range(width)]
        self.shades: list[list[int]] = [[0] * height for _ in range(width)]
        self._render()

    def _render(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                state = self.grid[x][y]
                if hasattr(self.canvas, "create_image") and self.images.get(state):
                    rect = self.canvas.create_image(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        anchor="nw",
                        image=self.images[state],
                    )
                else:
                    rect = self.canvas.create_rectangle(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        (x + 1) * TILE_SIZE,
                        (y + 1) * TILE_SIZE,
                        fill=self.colors[state],
                    )
                self.rects[x][y] = rect
                self._update_shading(x, y)

    def _update_shading(self, x: int, y: int) -> None:
        """Add a semi-transparent overlay on tunnel edges."""
        if self.shades[x][y]:
            if hasattr(self.canvas, "delete"):
                self.canvas.delete(self.shades[x][y])
            self.shades[x][y] = 0

        state = self.grid[x][y]
        if state != TILE_TUNNEL:
            return

        # Determine if any neighbour is non-tunnel
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if self.get_cell(nx, ny) != TILE_TUNNEL:
                # Tkinter does not support 8 digit hex colors for transparency.
                # Use a stipple pattern with a solid black fill to create a
                # semi-transparent overlay instead.
                self.shades[x][y] = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill="#000000",
                    stipple="gray50",
                    outline="",
                )
                break

    def get_cell(self, x: int, y: int) -> str:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return TILE_ROCK
        return self.grid[x][y]

    def set_cell(self, x: int, y: int, state: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x][y] = state
            if hasattr(self.canvas, "delete"):
                self.canvas.delete(self.rects[x][y])
                if self.shades[x][y]:
                    self.canvas.delete(self.shades[x][y])
            if hasattr(self.canvas, "create_image") and self.images.get(state):
                self.rects[x][y] = self.canvas.create_image(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    anchor="nw",
                    image=self.images[state],
                )
            else:
                self.rects[x][y] = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill=self.colors[state],
                )
            self._update_shading(x, y)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._update_shading(nx, ny)

# Energy constants
ENERGY_MAX = 100
MOVE_ENERGY_COST = 1
DIG_ENERGY_COST = 2
REST_ENERGY_GAIN = 5


class FoodDrop:
    """Limited food source that disappears after its charges are used."""

    def __init__(self, sim: "AntSim", x: int, y: int, charges: int = 5) -> None:
        self.sim = sim
        self.charges = charges
        # Rectangle used for collision detection
        self.item = sim.canvas.create_rectangle(
            x,
            y,
            x + FOOD_SIZE,
            y + FOOD_SIZE,
            outline="",
            fill="",
        )

        self.icon = None
        self.flash_icon = None
        self.image_item = None
        self.tooltip = None

        if hasattr(sim.canvas, "create_image"):
            self.icon = create_glowing_icon(FOOD_SIZE)
            self.flash_icon = create_glowing_icon(FOOD_SIZE, inner="#ffffff", outer="#ffcc00")
            self.image_item = sim.canvas.create_image(x, y, image=self.icon, anchor="nw")
            self.tooltip = sim.canvas.create_text(
                x + FOOD_SIZE / 2,
                y - 10,
                text=f"{self.charges} left",
                state="hidden",
                fill="black",
                font=("Arial", 8),
            )
            sim.canvas.tag_bind(self.image_item, "<Enter>", self._show_tooltip)
            sim.canvas.tag_bind(self.image_item, "<Leave>", self._hide_tooltip)
            sim.canvas.tag_bind(self.image_item, "<Button-1>", self._on_click)

    def _show_tooltip(self, _event=None) -> None:
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, state="normal")

    def _hide_tooltip(self, _event=None) -> None:
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, state="hidden")

    def _flash(self) -> None:
        if self.image_item and self.flash_icon:
            self.sim.canvas.itemconfigure(self.image_item, image=self.flash_icon)
            if hasattr(self.sim, "master") and hasattr(self.sim.master, "after"):
                self.sim.master.after(
                    100, lambda: self.sim.canvas.itemconfigure(self.image_item, image=self.icon)
                )

    def _on_click(self, _event=None) -> None:
        self.take_charge()

    def take_charge(self) -> bool:
        if self.charges <= 0:
            return False
        self.charges -= 1
        self._flash()
        if self.tooltip is not None:
            self.sim.canvas.itemconfigure(self.tooltip, text=f"{self.charges} left")
        if self.charges <= 0:
            self.sim.canvas.delete(self.item)
            if self.image_item:
                self.sim.canvas.delete(self.image_item)
            if self.tooltip:
                self.sim.canvas.delete(self.tooltip)
        return True


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
            self.sim.ants.append(WorkerAnt(self.sim, int(x1), int(y1), "blue"))


class BaseAnt:
    """Base class for all ants."""

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
        self.status: str = "Active"
        self.role: str = self.__class__.__name__
        self.ant_id: int = self.item
        self.terrain: Terrain | None = getattr(sim, "terrain", None)



    def attempt_move(self, dx: int, dy: int) -> None:
        if self.energy <= 0:
            return
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
        new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))

        # Base movement cost
        cost = MOVE_ENERGY_COST
        if self.terrain:
            tile_x = int((new_x1 + ANT_SIZE / 2) // TILE_SIZE)
            tile_y = int((new_y1 + ANT_SIZE / 2) // TILE_SIZE)
            tile = self.terrain.get_cell(tile_x, tile_y)
            if tile in (TILE_ROCK, TILE_COLLAPSED):
                return
            if tile == TILE_SAND:
                self.terrain.set_cell(tile_x, tile_y, TILE_TUNNEL)
                cost += 1  # digging through sand costs extra
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

    def energy_color(self) -> str:
        if self.energy > 60:
            return PALETTE["bar_green"]
        if self.energy > 30:
            return PALETTE["bar_yellow"]
        return PALETTE["bar_red"]

    def update_energy_bar(self) -> None:
        x1, y1, x2, _ = self.sim.canvas.coords(self.item)
        self._set_coords(self.energy_bar_bg, x1, y1 - 4, x2, y1 - 2)
        width = (self.energy / ENERGY_MAX) * (x2 - x1)
        self._set_coords(self.energy_bar, x1, y1 - 4, x1 + width, y1 - 2)
        self.sim.canvas.itemconfigure(self.energy_bar, fill=self.energy_color())

    def _set_coords(self, item: int, x1: float, y1: float, x2: float, y2: float) -> None:
        try:
            self.sim.canvas.coords(item, x1, y1, x2, y2)
        except TypeError:
            if hasattr(self.sim.canvas, "objects"):
                self.sim.canvas.objects[item] = [x1, y1, x2, y2]


    def update(self) -> None:
        if self.energy <= 0:
            self.status = "Tired"
            self.energy = max(0, self.energy - 0.1)
            self.rest()
            return

        self.move_random()
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])
        self.frame_index = (self.frame_index + 1) % len(self.sprite_frames)
        self.sim.canvas.itemconfigure(self.image_id, image=self.sprite_frames[self.frame_index])


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

    def get_ai_move(self) -> Tuple[int, int]:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return random.choice([-MOVE_STEP, 0, MOVE_STEP]), random.choice(
                [-MOVE_STEP, 0, MOVE_STEP]
            )
        openai.api_key = key

        state = {
            "ant": self.sim.canvas.coords(self.item),
            "food": self.sim.canvas.coords(self.sim.food),
            "queen": self.sim.canvas.coords(self.sim.queen.item),
        }
        messages = [
            {
                "role": "system",
                "content": 'You control an ant in a grid. Respond with JSON like {"dx":5,"dy":0}.',
            },
            {"role": "user", "content": json.dumps(state)},
        ]

        try:
            resp = openai.ChatCompletion.create(
                model=self.model, messages=messages, max_tokens=10
            )
            data = json.loads(resp.choices[0].message["content"])
            return int(data.get("dx", 0)), int(data.get("dy", 0))
        except Exception:
            return 0, 0

    def update(self) -> None:
        if self.energy <= 0:
            self.rest()
            coords = self.sim.canvas.coords(self.item)
            self.last_pos = (coords[0], coords[1])
            return
        dx, dy = self.get_ai_move()
        self.attempt_move(dx, dy)
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])



class WorkerAnt(BaseAnt):
    """Ant focused on collecting food and feeding the queen."""

    def update(self) -> None:
        if self.energy <= 0:
            self.rest()
            coords = self.sim.canvas.coords(self.item)
            self.last_pos = (coords[0], coords[1])
            return
        start = self.sim.canvas.coords(self.item)
        # Initialize to avoid UnboundLocalError when carrying food
        best_dir = None
        best_value = -1.0
        if not self.carrying_food:
            # Check for food drops first
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
            if self.carrying_food:
                pass
            else:
                # Follow pheromones if present, otherwise head toward food
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


class ScoutAnt(BaseAnt):
    """Ant that explores randomly, remembering visited positions."""

    def __init__(self, sim: "AntSim", x: int, y: int, color: str = "black") -> None:
        super().__init__(sim, x, y, color)
        self.visited: set[tuple[float, float]] = {(float(x), float(y))}

    def update(self) -> None:
        x1, y1, _, _ = self.sim.canvas.coords(self.item)

        # Consider moves that lead to unexplored positions
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


class SoldierAnt(BaseAnt):
    """Simple soldier ant that patrols around the queen."""

    def update(self) -> None:
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


class Queen:
    """Represents the colony's queen. Uses OpenAI for spawn decisions."""

    def __init__(self, sim: "AntSim", x: int, y: int, model: str | None = None) -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(
            x, y, x + 40, y + 20, fill=PALETTE["neon_purple"]
        )
        self.hunger_bar_bg = sim.canvas.create_rectangle(
            x,
            y - 6,
            x + 40,
            y - 4,
            fill=PALETTE["bar_bg"],
        )
        self.hunger_bar = sim.canvas.create_rectangle(
            x,
            y - 6,
            x + 40,
            y - 4,
            fill=PALETTE["bar_green"],
        )
        self.hunger: float = 100
        self.spawn_timer: int = 300
        self.model = model or os.getenv("OPENAI_QUEEN_MODEL", "gpt-4-0125-preview")
        self.mad: bool = False
        self.ant_positions: dict[int, tuple[float, float]] = {}
        self.fed: int = 0
        self.move_counter: int = 0
        self.thought_timer: int = 0
        self.current_thought: str = ""

        # Animation assets (only if using a real Tk canvas)
        self.glow_item: int | None = None
        self.glow_state: int = 0
        self.expression_item: int | None = None

        if isinstance(sim.canvas, tk.Canvas):
            self.glow_item = sim.canvas.create_oval(
                x - 5,
                y - 10,
                x + ANT_SIZE + 5,
                y + ANT_SIZE + 10,
                outline="yellow",
                width=2,
            )
            sim.canvas.tag_lower(self.glow_item, self.item)
            self.expression_item = sim.canvas.create_text(
                x + ANT_SIZE / 2,
                y - 15,
                text=":)",
                font=("Arial", 12),
            )
            self.animate_glow()

    def feed(self, amount: float = 10) -> None:
        """Increase the queen's hunger level when fed."""
        self.hunger = min(100, self.hunger + amount)

    def hunger_color(self) -> str:
        if self.hunger > 60:
            return PALETTE["bar_green"]
        if self.hunger > 30:
            return PALETTE["bar_yellow"]
        return PALETTE["bar_red"]

    def update_hunger_bar(self) -> None:
        x1, y1, x2, _ = self.sim.canvas.coords(self.item)
        self._set_coords(self.hunger_bar_bg, x1, y1 - 6, x2, y1 - 4)
        width = (self.hunger / 100) * (x2 - x1)
        self._set_coords(self.hunger_bar, x1, y1 - 6, x1 + width, y1 - 4)
        self.sim.canvas.itemconfigure(self.hunger_bar, fill=self.hunger_color())

    def _set_coords(self, item: int, x1: float, y1: float, x2: float, y2: float) -> None:
        try:
            self.sim.canvas.coords(item, x1, y1, x2, y2)
        except TypeError:
            if hasattr(self.sim.canvas, "objects"):
                self.sim.canvas.objects[item] = [x1, y1, x2, y2]

    def thought(self) -> str:
        """Return the queen's current thought or mood."""
        key = os.getenv("OPENAI_API_KEY")
        default = [
            "I demand more food.",
            "Where are my loyal workers?",
            "This colony better prosper.",
            "Another day of ruling...",
            "Perhaps a nap soon.",
        ]
        prompt = {
            "hunger": int(self.hunger),
            "fed": self.fed,
            "food": self.sim.food_collected,
            "ants": len(getattr(self.sim, "ants", [])),
            "eggs": len(getattr(self.sim, "eggs", [])),
        }

        if not hasattr(self, "thought_timer"):
            self.thought_timer = 0
            self.current_thought = random.choice(default)

        if self.thought_timer > 0:
            self.thought_timer -= 1
            return self.current_thought

        if not key:
            if self.hunger < 30:
                new_thought = "I'm starving... bring food!"
            elif prompt["eggs"] > 0:
                new_thought = f"Waiting on {prompt['eggs']} eggs."
            elif prompt["ants"] < 5:
                new_thought = "We need more workers."
            else:
                new_thought = random.choice(default)
        else:
            openai.api_key = key
            try:
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a snarky ant queen. Reply with a single short thought about your state.",
                        },
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    max_tokens=20,
                )
                new_thought = resp.choices[0].message["content"].strip()
            except Exception:
                if self.hunger < 30:
                    new_thought = "I'm starving... bring food!"
                else:
                    new_thought = random.choice(default)

        self.current_thought = new_thought
        self.thought_timer = 5
        return new_thought

    def decide_spawn(self) -> bool:
        key = os.getenv("OPENAI_API_KEY")
        counts: dict[str, int] = {}
        for ant in self.sim.ants:
            role = getattr(ant, "role", ant.__class__.__name__)
            counts[role] = counts.get(role, 0) + 1
        if not key:
            # Simple heuristic when offline: spawn if food reserves exceed number
            # of workers and queen is reasonably fed.
            worker_count = counts.get("WorkerAnt", 0)
            return self.sim.food_collected > worker_count and self.hunger > 30
        openai.api_key = key
        prompt = {
            "hunger": self.hunger,
            "ants": len(self.sim.ants),
            "food": self.sim.food_collected,
            "population": counts,
        }
        try:
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Respond with yes or no if the queen should spawn a new worker.",
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
                max_tokens=1,
            )
            answer = resp.choices[0].message["content"].strip().lower()
            return answer.startswith("y")
        except Exception:
            return True

    def rescue_stuck_ants(self) -> None:
        """Move ants that haven't changed position."""
        for ant in self.sim.ants:
            coords = self.sim.canvas.coords(ant.item)
            last = self.ant_positions.get(ant.item)
            if last is not None and coords[:2] == list(last):
                self.sim.canvas.move(
                    ant.item,
                    random.choice([-MOVE_STEP, MOVE_STEP]),
                    random.choice([-MOVE_STEP, MOVE_STEP]),
                )
                coords = self.sim.canvas.coords(ant.item)
            self.ant_positions[ant.item] = (coords[0], coords[1])

    def lay_egg(self, x: int, y: int) -> None:
        """Spawn an egg near the given coordinates."""
        spawn_direct = False
        if not hasattr(self.sim, "eggs"):
            self.sim.eggs = []
            spawn_direct = True
        egg = Egg(self.sim, x, y)
        self.sim.eggs.append(egg)
        if spawn_direct:
            # tests or simplified sims expect immediate ants
            self.sim.eggs.remove(egg)
            self.sim.ants.append(WorkerAnt(self.sim, x, y, "blue"))

    def animate_glow(self) -> None:
        """Pulse the glow outline to give the queen some life."""
        if self.glow_item is None:
            return
        self.glow_state = (self.glow_state + 1) % 2
        width = 1 if self.glow_state == 0 else 3
        color = "yellow" if self.glow_state == 0 else "orange"
        self.sim.canvas.itemconfigure(self.glow_item, width=width, outline=color)
        self.sim.master.after(200, self.animate_glow)


    def update(self) -> None:
        """Handle hunger and periodically spawn new worker ants."""
        self.hunger -= 0.1
        self.spawn_timer -= 1
        self.move_counter += 1
        if self.move_counter % 20 == 0:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            x1, y1, _, _ = self.sim.canvas.coords(self.item)
            new_x1 = max(0, min(WINDOW_WIDTH - 40, x1 + dx))
            new_y1 = max(0, min(WINDOW_HEIGHT - 20, y1 + dy))
            self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)

        if self.hunger < 50:
            self.sim.canvas.itemconfigure(self.item, fill=PALETTE["bar_red"])
            self.mad = True
        else:
            self.sim.canvas.itemconfigure(self.item, fill=PALETTE["neon_purple"])
            self.mad = False

        # Update expression graphic
        if self.mad:
            expr = ">:("
        elif self.hunger > 80:
            expr = ":D"
        elif self.hunger < 40:
            expr = ":("
        else:
            expr = ":|"
        if self.expression_item is not None:
            x1, y1, x2, _ = self.sim.canvas.coords(self.item)
            cx = (x1 + x2) / 2
            self.sim.canvas.coords(self.expression_item, cx, y1 - 15)
            self.sim.canvas.itemconfigure(self.expression_item, text=expr)

        if self.mad:
            self.rescue_stuck_ants()

        if self.spawn_timer <= 0 and self.hunger > 0:
            if self.decide_spawn():
                x1, y1, x2, _ = self.sim.canvas.coords(self.item)
                x = (x1 + x2) / 2
                y = y1 - ANT_SIZE * 2
                self.lay_egg(int(x), int(y))
            self.spawn_timer = 300

        self.update_hunger_bar()


class AntSim:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.frame = tk.Frame(master, bg=PALETTE["frame"])
        self.frame.pack(side="left", padx=5, pady=5)
        self.title_label = tk.Label(
            self.frame,
            text="Ant Hive Simulation v0.1",
            bg=PALETTE["frame"],
            font=HEADER_FONT,
        )
        self.title_label.pack(fill="x")
        self.canvas = tk.Canvas(
            self.frame,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=PALETTE["background"],
            highlightthickness=0,
        )
        self.canvas.pack()
        self.sidebar_frame = tk.Frame(master, bg=PALETTE["frame"])
        self.sidebar_frame.pack(side="right", fill="y")

        self.food_icon = create_glowing_icon(20)
        # Icon used when rendering ant stats in the sidebar
        self.ant_icon = create_glowing_icon(ANT_SIZE)

        self.spawn_button = tk.Button(
            self.sidebar_frame,
            image=self.food_icon,
            text="Food Drop",
            compound="top",
            borderwidth=0,
        )
        self.spawn_button.pack(side="top")

        self.stats_label = tk.Label(
            self.sidebar_frame, bg=PALETTE["frame"], font=("Arial", 10)
        )
        self.stats_label.pack(side="top")

        self.ant_panel = tk.Text(
            self.sidebar_frame,
            width=30,
            height=10,
            bg=PALETTE["sidebar"],
            font=MONO_FONT,
        )
        self.ant_panel.pack(side="top", fill="both", expand=True)
        self.ant_panel.tag_configure("header", font=HEADER_FONT)
        self.ant_panel.tag_configure("normal", font=MONO_FONT)
        self.ant_panel.configure(state="disabled")

        self.colony_panel = tk.Text(
            self.sidebar_frame,
            width=30,
            height=6,
            bg=PALETTE["sidebar"],
            font=MONO_FONT,
        )
        self.colony_panel.pack(side="top", fill="both", expand=True)
        self.colony_panel.tag_configure("header", font=HEADER_FONT)
        self.colony_panel.tag_configure("normal", font=MONO_FONT)
        self.colony_panel.configure(state="disabled")
        self.spawn_button.bind("<ButtonPress-1>", self.start_place_food)
        self.canvas.bind("<Button-1>", self.place_food)
        self.placing_food = False

        self.food_drops: List[FoodDrop] = []
        self.eggs: List[Egg] = []
        self.selected_index = 0
        self.selection_highlight: int | None = None
        self.selection_tooltip: int | None = None
        self.master.bind("<Tab>", self.cycle_selection)

        # Pheromone grid
        self.grid_width = WINDOW_WIDTH // TILE_SIZE
        self.grid_height = WINDOW_HEIGHT // TILE_SIZE
        self.pheromones: list[list[float]] = [
            [0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)
        ]
        # Canvas items for visualizing pheromones
        self.pheromone_items: list[list[int | None]] = [
            [None for _ in range(self.grid_height)] for _ in range(self.grid_width)
        ]

        # Terrain
        self.terrain = Terrain(self.grid_width, self.grid_height, self.canvas)
        for _ in range(30):
            rx = random.randint(0, self.terrain.width - 1)
            ry = random.randint(self.terrain.height // 2, self.terrain.height - 1)
            self.terrain.set_cell(rx, ry, TILE_ROCK)


        # Entities
        self.food: int = self.canvas.create_rectangle(
            180, 20, 180 + FOOD_SIZE, 20 + FOOD_SIZE, fill="green"
        )
        self.queen: Queen = Queen(self, 180, 570)

        # Ants
        self.ants: List[BaseAnt] = [
            WorkerAnt(self, 195, 295, "blue"),
            WorkerAnt(self, 215, 295, "red"),
            ScoutAnt(self, 235, 295, "black"),
            SoldierAnt(self, 255, 295, "orange"),
            NurseAnt(self, 275, 295, "pink"),
        ]

        # Stats
        self.food_collected: int = 0
        self.queen_fed: int = 0

        self.update_sidebar()

        # Kick off loop
        self.update()

    def move_food(self) -> None:
        self.canvas.move(self.food, random.randint(-50, 50), random.randint(20, 40))

    def sparkle(self, x: float, y: float) -> None:
        flash = self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="yellow", outline="")
        self.canvas.after(200, lambda: self.canvas.delete(flash))

    def start_place_food(self, _event) -> None:
        self.placing_food = True

    def place_food(self, event) -> None:
        if not self.placing_food:
            return
        self.food_drops.append(FoodDrop(self, event.x, event.y))
        self.placing_food = False

    def cycle_selection(self, _event) -> None:
        all_entities = [self.queen] + self.ants
        self.selected_index = (self.selected_index + 1) % len(all_entities)
        sel = all_entities[self.selected_index]

        if self.selection_highlight:
            self.canvas.delete(self.selection_highlight)
            self.selection_highlight = None
        if self.selection_tooltip:
            self.canvas.delete(self.selection_tooltip)
            self.selection_tooltip = None

        if sel is self.queen:
            thought = self.queen.thought()
            self.master.title(f"Queen: {thought}")
        else:
            self.master.title(f"Selected: {sel.role}")

        x1, y1, x2, y2 = self.canvas.coords(sel.item)
        self.selection_highlight = self.canvas.create_rectangle(
            x1 - 2,
            y1 - 2,
            x2 + 2,
            y2 + 2,
            outline="cyan",
            width=2,
        )
        cx = (x1 + x2) / 2
        label = "Queen" if sel is self.queen else sel.role
        self.selection_tooltip = self.canvas.create_text(
            cx,
            y1 - 10,
            text=label,
            fill="cyan",
            font=("Arial", 10),
        )
        self.master.after(1000, self.clear_selection_marks)

    def clear_selection_marks(self) -> None:
        if self.selection_highlight:
            self.canvas.delete(self.selection_highlight)
            self.selection_highlight = None
        if self.selection_tooltip:
            self.canvas.delete(self.selection_tooltip)
            self.selection_tooltip = None

    def _update_pheromone_visual(self, gx: int, gy: int) -> None:
        """Render a rectangle representing pheromone strength."""
        val = self.pheromones[gx][gy]
        item = self.pheromone_items[gx][gy]
        if val <= 0:
            if item:
                if hasattr(self.canvas, "delete"):
                    self.canvas.delete(item)
                self.pheromone_items[gx][gy] = None
            return
        intensity = max(0, min(255, int(255 * min(1.0, val))))
        color = f"#0000{intensity:02x}"
        if item:
            if hasattr(self.canvas, "itemconfigure"):
                self.canvas.itemconfigure(item, fill=color)
        else:
            x1 = gx * TILE_SIZE + TILE_SIZE / 4
            y1 = gy * TILE_SIZE + TILE_SIZE / 4
            x2 = x1 + TILE_SIZE / 2
            y2 = y1 + TILE_SIZE / 2
            if hasattr(self.canvas, "create_rectangle"):
                item = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline="",
                )
                self.pheromone_items[gx][gy] = item
                if hasattr(self.canvas, "tag_lower"):
                    self.canvas.tag_lower(item)

    def deposit_pheromone(self, x: float, y: float, amount: float) -> None:
        gx = int(x) // TILE_SIZE
        gy = int(y) // TILE_SIZE
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            self.pheromones[gx][gy] += amount
            self._update_pheromone_visual(gx, gy)

    def get_pheromone(self, x: float, y: float) -> float:
        gx = int(x) // TILE_SIZE
        gy = int(y) // TILE_SIZE
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            return self.pheromones[gx][gy]
        return 0.0

    def decay_pheromones(self) -> None:
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if self.pheromones[x][y] > 0:
                    self.pheromones[x][y] = max(0.0, self.pheromones[x][y] - PHEROMONE_DECAY)
                    self._update_pheromone_visual(x, y)

    def get_coords(self, item: int) -> List[float]:
        return self.canvas.coords(item)

    def check_collision(self, a: int, b: int) -> bool:
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def get_stats(self) -> str:
        return (
            f"Food Collected: {self.food_collected}\n"
            f"Fed to Queen: {self.queen_fed}\n"
            f"Ants Active: {len(self.ants)}\n"
            f"Eggs: {len(self.eggs)}"
        )

    def update_sidebar(self) -> None:
        lines = [
            f"ID {ant.ant_id} | {ant.role} | E:{int(ant.energy)} | {ant.status}"
            for ant in self.ants
        ]
        metrics = (
            f"Food: {self.food_collected}\n"
            f"Queen Hunger: {int(self.queen.hunger)}\n"
            f"Ants: {len(self.ants)}\n"
            f"Eggs: {len(self.eggs)}"
        )
        self.ant_panel.configure(state="normal")
        self.ant_panel.delete("1.0", tk.END)
        self.ant_panel.insert(tk.END, "Ant Stats:\n", "header")
        for line in lines:
            self.ant_panel.image_create(tk.END, image=self.ant_icon)
            self.ant_panel.insert(tk.END, " " + line + "\n", "normal")
        self.ant_panel.configure(state="disabled")

        self.colony_panel.configure(state="normal")
        self.colony_panel.delete("1.0", tk.END)
        self.colony_panel.insert(tk.END, "Colony Stats:\n", "header")
        self.colony_panel.insert(tk.END, metrics, "normal")
        all_entities = [self.queen] + self.ants
        sel = all_entities[self.selected_index]
        if sel is self.queen:
            thought = self.queen.thought()
            self.colony_panel.insert(tk.END, f"\nQueen Thought: {thought}", "normal")
        else:
            self.colony_panel.insert(tk.END, f"\nSelected: {sel.role}", "normal")
        self.colony_panel.configure(state="disabled")
        self.master.after(1000, self.update_sidebar)

    def update(self) -> None:
        for ant in self.ants:
            ant.update()
            ant.update_energy_bar()

        for egg in self.eggs[:]:
            egg.update()

        self.queen.update()
        for drop in self.food_drops[:]:
            if drop.charges <= 0:
                self.food_drops.remove(drop)
        self.decay_pheromones()

        self.stats_label.configure(text=self.get_stats())
        self.master.after(100, self.update)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Ant Hive Simulation v0.1")
    app = AntSim(root)
    root.mainloop()
