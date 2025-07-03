import json
import os
import random
import tkinter as tk

from ..constants import ANT_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT, PALETTE, MOVE_STEP
from ..ai_interface import chat_completion, openai
from .egg import Egg
from .worker import WorkerAnt
from .base_ant import BaseAnt


class Queen:
    """Represents the colony's queen. Uses OpenAI for spawn decisions."""

    def __init__(self, sim: "AntSim", x: int, y: int, model: str | None = None) -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(x, y, x + 40, y + 20, fill=PALETTE["neon_purple"])
        self.hunger_bar_bg = sim.canvas.create_rectangle(x, y - 6, x + 40, y - 4, fill=PALETTE["bar_bg"])
        self.hunger_bar = sim.canvas.create_rectangle(x, y - 6, x + 40, y - 4, fill=PALETTE["bar_green"])
        self.hunger: float = 100
        self.spawn_timer: int = 300
        self.model = model or os.getenv("OPENAI_QUEEN_MODEL", "gpt-4-0125-preview")
        self.mad: bool = False
        self.ant_positions: dict[int, tuple[float, float]] = {}
        self.fed: int = 0
        self.move_counter: int = 0
        self.thought_timer: int = 0
        self.current_thought: str = ""
        self.glow_item = None
        self.glow_state = 0
        self.expression_item = None
        if isinstance(sim.canvas, tk.Canvas):
            self.glow_item = sim.canvas.create_oval(x - 5, y - 10, x + ANT_SIZE + 5, y + ANT_SIZE + 10, outline="yellow", width=2)
            sim.canvas.tag_lower(self.glow_item, self.item)
            self.expression_item = sim.canvas.create_text(x + ANT_SIZE / 2, y - 15, text=":)", font=("Arial", 12))
            self.animate_glow()

    def feed(self, amount: float = 10) -> None:
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
        if self.thought_timer > 0:
            self.thought_timer -= 1
            return self.current_thought
        if not key:
            new_thought = random.choice(default)
        else:
            messages = [
                {"role": "system", "content": "You are a snarky ant queen. Reply with a single short thought about your state."},
                {"role": "user", "content": json.dumps(prompt)},
            ]
            resp = chat_completion(messages, self.model, 20)
            new_thought = resp or random.choice(default)
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
            worker_count = counts.get("WorkerAnt", 0)
            return self.sim.food_collected > worker_count and self.hunger > 30
        prompt = {
            "hunger": self.hunger,
            "ants": len(self.sim.ants),
            "food": self.sim.food_collected,
            "population": counts,
        }
        messages = [
            {"role": "system", "content": "Respond with yes or no if the queen should spawn a new worker."},
            {"role": "user", "content": json.dumps(prompt)},
        ]
        resp = chat_completion(messages, self.model, 1)
        return resp is None or resp.strip().lower().startswith("y")

    def rescue_stuck_ants(self) -> None:
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
        spawn_direct = False
        if not hasattr(self.sim, "eggs"):
            self.sim.eggs = []
            spawn_direct = True
        egg = Egg(self.sim, x, y)
        self.sim.eggs.append(egg)
        if spawn_direct:
            self.sim.eggs.remove(egg)
            self.sim.ants.append(WorkerAnt(self.sim, x, y, "blue"))

    def animate_glow(self) -> None:
        if self.glow_item is None:
            return
        self.glow_state = (self.glow_state + 1) % 2
        width = 1 if self.glow_state == 0 else 3
        color = "yellow" if self.glow_state == 0 else "orange"
        self.sim.canvas.itemconfigure(self.glow_item, width=width, outline=color)
        self.sim.master.after(200, self.animate_glow)

    def update(self) -> None:
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
        if self.expression_item is not None:
            x1, y1, x2, _ = self.sim.canvas.coords(self.item)
            cx = (x1 + x2) / 2
            expr = ">:(" if self.mad else (":D" if self.hunger > 80 else ":(" if self.hunger < 40 else ":|")
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
