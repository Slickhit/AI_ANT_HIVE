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

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
SIDEBAR_WIDTH = 150
ANT_SIZE = 10
FOOD_SIZE = 8
MOVE_STEP = 5
PHEROMONE_DECAY = 0.01
SCOUT_PHEROMONE_AMOUNT = 1.0


# Terrain constants
TILE_SIZE = 20
TILE_SAND = "sand"
TILE_TUNNEL = "tunnel"
TILE_ROCK = "rock"
TILE_COLLAPSED = "collapsed"

class Terrain:
    """Simple 2D grid representing the underground."""

    colors = {
        TILE_SAND: "#c2b280",
        TILE_TUNNEL: "#806517",
        TILE_ROCK: "#7f7f7f",
        TILE_COLLAPSED: "black",
    }

    def __init__(self, width: int, height: int, canvas: tk.Canvas) -> None:
        self.width = width
        self.height = height
        self.canvas = canvas
        self.grid: list[list[str]] = [
            [TILE_SAND for _ in range(height)] for _ in range(width)
        ]
        self.rects: list[list[int]] = [[0] * height for _ in range(width)]
        self._render()

    def _render(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                state = self.grid[x][y]
                rect = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill=self.colors[state],
                )
                self.rects[x][y] = rect

    def get_cell(self, x: int, y: int) -> str:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return TILE_ROCK
        return self.grid[x][y]

    def set_cell(self, x: int, y: int, state: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x][y] = state
            self.canvas.itemconfigure(self.rects[x][y], fill=self.colors[state])

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
        self.item = sim.canvas.create_rectangle(
            x,
            y,
            x + FOOD_SIZE,
            y + FOOD_SIZE,
            fill="orange",
        )

    def take_charge(self) -> bool:
        if self.charges <= 0:
            return False
        self.charges -= 1
        if self.charges <= 0:
            self.sim.canvas.delete(self.item)
        return True

class BaseAnt:
    """Base class for all ants."""

    def __init__(
        self, sim: "AntSim", x: int, y: int, color: str = "black", energy: int = 100
    ) -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(
            x, y, x + ANT_SIZE, y + ANT_SIZE, fill=color
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
        self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)

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


    def update(self) -> None:
        if self.energy <= 0:
            self.status = "Tired"
            self.energy = max(0, self.energy - 0.1)
            self.rest()
            return

        self.move_random()
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])


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
        if not self.carrying_food:
            # Check for food drops first
            for drop in getattr(self.sim, "food_drops", []):
                if self.sim.check_collision(self.item, drop.item):
                    if drop.take_charge():
                        self.energy = min(ENERGY_MAX, self.energy + 20)
                        self.carrying_food = True
                    if drop.charges <= 0:
                        self.sim.food_drops.remove(drop)
                    break
            if self.carrying_food:
                pass
            else:
                # Follow pheromones if present, otherwise head toward food
                x1, y1, _, _ = self.sim.canvas.coords(self.item)
                best_dir = None
                best_value = -1.0
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
            else:
                self.move_towards(self.sim.food)
            if self.sim.check_collision(self.item, self.sim.food):
                self.carrying_food = True
                self.sim.food_collected += 1
                self.sim.move_food()
        else:
            self.move_towards(self.sim.queen.item)
            if self.sim.check_collision(self.item, self.sim.queen.item):
                self.sim.queen.feed()
                self.sim.queen.fed += 1
                self.sim.queen_fed += 1
                self.carrying_food = False
        coords = self.sim.canvas.coords(self.item)
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
        coords = self.sim.canvas.coords(self.item)
        self.last_pos = (coords[0], coords[1])


class Queen:
    """Represents the colony's queen. Uses OpenAI for spawn decisions."""

    def __init__(self, sim: "AntSim", x: int, y: int, model: str | None = None) -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(x, y, x + 40, y + 20, fill="purple")
        self.hunger: float = 100
        self.spawn_timer: int = 300
        self.model = model or os.getenv("OPENAI_QUEEN_MODEL", "gpt-4-0125-preview")
        self.mad: bool = False
        self.ant_positions: dict[int, tuple[float, float]] = {}
        self.fed: int = 0
        self.move_counter: int = 0

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
        }
        if not key:
            return random.choice(default)
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
            return resp.choices[0].message["content"].strip()
        except Exception:
            return random.choice(default)

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
            self.sim.canvas.itemconfigure(self.item, fill="red")
            self.mad = True
        else:
            self.sim.canvas.itemconfigure(self.item, fill="purple")
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
                self.sim.ants.append(WorkerAnt(self.sim, int(x), int(y), "blue"))
            self.spawn_timer = 300


class AntSim:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.canvas = tk.Canvas(
            master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg="white"
        )
        self.canvas.pack(side="left")
        self.sidebar = tk.Text(master, width=30)
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.configure(state="disabled")
        self.spawn_button = tk.Button(master, text="Food Drop")
        self.spawn_button.pack(side="top")
        self.spawn_button.bind("<ButtonPress-1>", self.start_place_food)
        self.canvas.bind("<Button-1>", self.place_food)
        self.placing_food = False

        self.food_drops: List[FoodDrop] = []
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
        self.stats_text: int = self.canvas.create_text(
            5, 5, anchor="nw", fill="blue", font=("Arial", 10)
        )

        self.update_sidebar()

        # Kick off loop
        self.update()

    def move_food(self) -> None:
        self.canvas.move(self.food, random.randint(-50, 50), random.randint(20, 40))

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

    def deposit_pheromone(self, x: float, y: float, amount: float) -> None:
        gx = int(x) // TILE_SIZE
        gy = int(y) // TILE_SIZE
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            self.pheromones[gx][gy] += amount

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
            f"Ants Active: {len(self.ants)}"
        )

    def update_sidebar(self) -> None:
        lines = [
            f"ID {ant.ant_id} | {ant.role} | E:{int(ant.energy)} | {ant.status}"
            for ant in self.ants
        ]
        metrics = (
            f"Food: {self.food_collected}\n"
            f"Queen Hunger: {int(self.queen.hunger)}\n"
            f"Ants: {len(self.ants)}"
        )
        self.sidebar.configure(state="normal")
        self.sidebar.delete("1.0", tk.END)
        self.sidebar.insert(tk.END, "Ant Stats:\n")
        for line in lines:
            self.sidebar.insert(tk.END, line + "\n")
        self.sidebar.insert(tk.END, "\nColony Stats:\n" + metrics)
        all_entities = [self.queen] + self.ants
        sel = all_entities[self.selected_index]
        if sel is self.queen:
            thought = self.queen.thought()
            self.sidebar.insert(tk.END, f"\nQueen Thought: {thought}")
        else:
            self.sidebar.insert(tk.END, f"\nSelected: {sel.role}")
        self.sidebar.configure(state="disabled")
        self.master.after(1000, self.update_sidebar)

    def update(self) -> None:
        for ant in self.ants:
            ant.update()

        self.queen.update()
        for drop in self.food_drops[:]:
            if drop.charges <= 0:
                self.food_drops.remove(drop)
        self.decay_pheromones()

        self.canvas.itemconfigure(self.stats_text, text=self.get_stats())
        self.master.after(100, self.update)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("AI Ant Hive")
    app = AntSim(root)
    root.mainloop()
