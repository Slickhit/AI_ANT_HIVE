from __future__ import annotations

import json
import os
import random
import tkinter as tk
from typing import List, Tuple

import openai

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
ANT_SIZE = 10
FOOD_SIZE = 8
MOVE_STEP = 5

# Energy constants
ENERGY_MAX = 100
MOVE_ENERGY_COST = 1
DIG_ENERGY_COST = 2
REST_ENERGY_GAIN = 5


class BaseAnt:
    """Base class for all ants."""

    def __init__(self, sim: "AntSim", x: int, y: int, color: str = "black") -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(
            x, y, x + ANT_SIZE, y + ANT_SIZE, fill=color
        )
        self.carrying_food: bool = False
        self.last_pos: Tuple[float, float] = (float(x), float(y))
        self.energy: int = ENERGY_MAX

    def move_random(self) -> None:
        dx = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        dy = random.choice([-MOVE_STEP, 0, MOVE_STEP])
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
        new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))
        self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)
        self.consume_energy(MOVE_ENERGY_COST)

    def move_towards(self, target: int) -> None:
        x1, y1, _, _ = self.sim.canvas.coords(self.item)
        tx1, ty1, _, _ = self.sim.canvas.coords(target)
        dx = MOVE_STEP if x1 < tx1 else -MOVE_STEP if x1 > tx1 else 0
        dy = MOVE_STEP if y1 < ty1 else -MOVE_STEP if y1 > ty1 else 0
        new_x1 = max(0, min(WINDOW_WIDTH - ANT_SIZE, x1 + dx))
        new_y1 = max(0, min(WINDOW_HEIGHT - ANT_SIZE, y1 + dy))
        self.sim.canvas.move(self.item, new_x1 - x1, new_y1 - y1)
        self.consume_energy(MOVE_ENERGY_COST)

    def consume_energy(self, amount: int) -> None:
        self.energy = max(0, self.energy - amount)

    def rest(self) -> None:
        self.energy = min(ENERGY_MAX, self.energy + REST_ENERGY_GAIN)

    def dig(self) -> None:
        self.consume_energy(DIG_ENERGY_COST)

    def update(self) -> None:
        if self.energy <= 0:
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
        self.sim.canvas.move(self.item, dx, dy)
        self.consume_energy(MOVE_ENERGY_COST)
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
        self.last_pos = (coords[0], coords[1])
        self.visited.add(self.last_pos)


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

    def feed(self, amount: float = 10) -> None:
        """Increase the queen's hunger level when fed."""
        self.hunger = min(100, self.hunger + amount)

    def decide_spawn(self) -> bool:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return True
        openai.api_key = key
        prompt = {
            "hunger": self.hunger,
            "ants": len(self.sim.ants),
            "food": self.sim.food_collected,
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

    def update(self) -> None:
        """Handle hunger and periodically spawn new worker ants."""
        self.hunger -= 0.1
        self.spawn_timer -= 1

        if self.hunger < 50:
            self.sim.canvas.itemconfigure(self.item, fill="red")
            self.mad = True
        else:
            self.sim.canvas.itemconfigure(self.item, fill="purple")
            self.mad = False

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
        self.canvas.pack()

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
        ]

        # Stats
        self.food_collected: int = 0
        self.queen_fed: int = 0
        self.stats_text: int = self.canvas.create_text(
            5, 5, anchor="nw", fill="blue", font=("Arial", 10)
        )

        # Kick off loop
        self.update()

    def move_food(self) -> None:
        self.canvas.move(self.food, random.randint(-50, 50), random.randint(20, 40))

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

    def update(self) -> None:
        for ant in self.ants:
            ant.update()

        self.queen.update()

        self.canvas.itemconfigure(self.stats_text, text=self.get_stats())
        self.master.after(100, self.update)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("AI Ant Hive")
    app = AntSim(root)
    root.mainloop()
