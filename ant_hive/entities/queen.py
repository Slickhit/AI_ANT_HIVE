import json
import os
import random
import time
import tkinter as tk

from ..constants import (
    ANT_SIZE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PALETTE,
    MOVE_STEP,
    TILE_SIZE,
)
from ..terrain import TILE_TUNNEL
from ..ai_interface import chat_completion
from .egg import Egg, hatch_random_ant
from .worker import WorkerAnt
from .base_ant import BaseAnt


class Queen:
    """Represents the colony's queen. Uses OpenAI for spawn decisions."""

    def __init__(self, sim: "AntSim", x: int, y: int, model: str | None = None) -> None:
        self.sim = sim
        self.item: int = sim.canvas.create_oval(
            x, y, x + 40, y + 20, fill=PALETTE["neon_purple"]
        )
        self.hunger_bar_bg = sim.canvas.create_rectangle(
            x, y - 6, x + 40, y - 4, fill=PALETTE["bar_bg"]
        )
        self.hunger_bar = sim.canvas.create_rectangle(
            x, y - 6, x + 40, y - 4, fill=PALETTE["bar_green"]
        )
        self.hunger: float = 100
        self.spawn_timer: int = 300
        self.base_spawn_time: int = 300
        self.egg_lay_cooldown: int = 0
        self.ready_to_mate: bool = True
        self.mating_cooldown: int = 0
        self.model = model or os.getenv("OPENAI_QUEEN_MODEL", "gpt-4-0125-preview")
        self.mad: bool = False
        self.ant_positions: dict[int, tuple[float, float]] = {}
        self.fed: int = 0
        self.move_counter: int = 0
        self.thought_timer: int = 0
        self.current_thought: str = ""
        self.last_command: str = ""
        self.command_cooldown: int = 0
        self.glow_item = None
        self.glow_state = 0
        self.expression_item = None
        self.thinking_item = None
        self._thought_future = None
        self._spawn_future = None
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
                x + ANT_SIZE / 2, y - 15, text=":)", font=("Arial", 12)
            )
            self.thinking_item = sim.canvas.create_text(
                x + ANT_SIZE / 2,
                y - 30,
                text="Thinking...",
                font=("Arial", 10, "italic"),
                fill="white",
                state="hidden",
            )
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

    def _set_coords(
        self, item: int, x1: float, y1: float, x2: float, y2: float
    ) -> None:
        try:
            self.sim.canvas.coords(item, x1, y1, x2, y2)
        except TypeError:
            if hasattr(self.sim.canvas, "objects"):
                self.sim.canvas.objects[item] = [x1, y1, x2, y2]

    def thought(self) -> str:
        key = os.getenv("OPENAI_API_KEY")
        default = [
            "Why do they cluster there?",
            "The food... it moved?",
            "Are they listening to me?",
            "Patterns shifting around the nest.",
            "Threat scents, faint but present.",
        ]
        prompt = {
            "hunger": int(self.hunger),
            "fed": self.fed,
            "food": self.sim.food_collected,
            "ants": len(getattr(self.sim, "ants", [])),
            "eggs": len(getattr(self.sim, "eggs", [])),
            "predators": len(getattr(self.sim, "predators", [])),
        }
        if self.thought_timer > 0:
            self.thought_timer -= 1
            return self.current_thought
        if not key:
            new_thought = random.choice(default)
            self.current_thought = new_thought
            self.thought_timer = 5
            return new_thought
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a curious ant queen. "
                    "Speak in eight words or fewer about current observations."
                ),
            },
            {"role": "user", "content": json.dumps(prompt)},
        ]
        if self._thought_future is None:
            self._thought_future = chat_completion(messages, self.model, 20)
            return self.current_thought
        if self._thought_future.done():
            resp = self._thought_future.result()
            self._thought_future = None
            new_thought = resp or random.choice(default)
            new_thought = " ".join(new_thought.split()[:8])
            self.current_thought = new_thought
            self.thought_timer = 5
            return new_thought
        return self.current_thought

    def decide_spawn(self) -> bool | None:
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
            {
                "role": "system",
                "content": "Respond with yes or no if the queen should spawn a new worker.",
            },
            {"role": "user", "content": json.dumps(prompt)},
        ]
        if self._spawn_future is None:
            self._spawn_future = chat_completion(messages, self.model, 1)
            return None
        if self._spawn_future.done():
            resp = self._spawn_future.result()
            self._spawn_future = None
            return resp is None or resp.strip().lower().startswith("y")
        return None

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
        if self.egg_lay_cooldown > 0:
            return
        spawn_direct = False
        if not hasattr(self.sim, "eggs"):
            self.sim.eggs = []
            spawn_direct = True
        egg = Egg(self.sim, x, y)
        self.sim.eggs.append(egg)
        self.egg_lay_cooldown = int(self.base_spawn_time * 1.7)
        if spawn_direct:
            self.sim.eggs.remove(egg)
            # In minimal test environments without an egg list,
            # spawn the ant immediately so behavior matches the full
            # simulation where eggs eventually hatch.
            self.hatch_ant(x, y)

    def hatch_ant(self, x: int, y: int):
        """Hatch a new ant at the given position using weighted role probabilities."""
        ant = hatch_random_ant(self.sim, x, y)
        self.sim.ants.append(ant)
        return ant

    def begin_reproduction_cycle(self) -> None:
        if not self.ready_to_mate:
            return
        qx1, qy1, _, _ = self.sim.canvas.coords(self.item)
        self.lay_egg(int(qx1 + 20), int(qy1))
        self.ready_to_mate = False
        self.mating_cooldown = int(self.base_spawn_time * 1.7)

    def command_hive(
        self, message: str, role: str | None = None, radius: int | None = None
    ) -> None:
        for ant in getattr(self.sim, "ants", []):
            if role and getattr(ant, "role", ant.__class__.__name__) != role:
                continue
            if radius is not None:
                ax1, ay1, _, _ = self.sim.canvas.coords(ant.item)
                qx1, qy1, qx2, qy2 = self.sim.canvas.coords(self.item)
                cx = (qx1 + qx2) / 2
                cy = (qy1 + qy2) / 2
                if (ax1 - cx) ** 2 + (ay1 - cy) ** 2 > radius**2:
                    continue
            ant.command = message
            ant.status = message
        self.last_command = message

    def animate_glow(self) -> None:
        if self.glow_item is None:
            return
        self.glow_state = (self.glow_state + 1) % 2
        width = 1 if self.glow_state == 0 else 3
        color = "yellow" if self.glow_state == 0 else "orange"
        self.sim.canvas.itemconfigure(self.glow_item, width=width, outline=color)
        self.sim.master.after(200, self.animate_glow)

    def update_thinking_indicator(self) -> None:
        if self.thinking_item is None:
            return
        waiting = False
        if self._thought_future is not None and not self._thought_future.done():
            waiting = True
        if self._spawn_future is not None and not self._spawn_future.done():
            waiting = True
        if waiting:
            x1, y1, x2, _ = self.sim.canvas.coords(self.item)
            cx = (x1 + x2) / 2
            self.sim.canvas.coords(self.thinking_item, cx, y1 - 30)
            self.sim.canvas.itemconfigure(self.thinking_item, state="normal")
        else:
            self.sim.canvas.itemconfigure(self.thinking_item, state="hidden")

    def update_visibility(self) -> None:
        """Hide or show the queen based on the underlying terrain tile."""
        if not hasattr(self.sim, "terrain"):
            return
        x1, y1, x2, y2 = self.sim.canvas.coords(self.item)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        tx = int(cx // TILE_SIZE)
        ty = int(cy // TILE_SIZE)
        visible = self.sim.terrain.get_cell(tx, ty) == TILE_TUNNEL
        state = "normal" if visible else "hidden"
        for item in (
            self.item,
            self.hunger_bar_bg,
            self.hunger_bar,
            self.glow_item,
            self.expression_item,
            self.thinking_item,
        ):
            if item is not None:
                try:
                    self.sim.canvas.itemconfigure(item, state=state)
                except Exception:
                    pass

    def update(self) -> None:
        # Avoid blocking the Tkinter event loop with a long sleep.
        # The previous implementation paused for four seconds,
        # freezing the UI each update cycle.
        if isinstance(self.sim.canvas, tk.Canvas):
            time.sleep(0)
        self.hunger -= 0.1
        if self.egg_lay_cooldown > 0:
            self.egg_lay_cooldown -= 1
        if self.mating_cooldown > 0:
            self.mating_cooldown -= 1
        else:
            self.ready_to_mate = True
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
            expr = (
                ">:("
                if self.mad
                else (":D" if self.hunger > 80 else ":(" if self.hunger < 40 else ":|")
            )
            self.sim.canvas.coords(self.expression_item, cx, y1 - 15)
            self.sim.canvas.itemconfigure(self.expression_item, text=expr)
        if self.mad:
            self.rescue_stuck_ants()
        if self.spawn_timer <= 0 and self.hunger > 0:
            decision = self.decide_spawn()
            if decision is not None:
                if decision and self.egg_lay_cooldown <= 0:
                    x1, y1, x2, _ = self.sim.canvas.coords(self.item)
                    x = (x1 + x2) / 2
                    y = y1 - ANT_SIZE * 2
                    self.lay_egg(int(x), int(y))
                self.spawn_timer = int(self.base_spawn_time * 1.7)
        if self.command_cooldown > 0:
            self.command_cooldown -= 1
        else:
            if self.sim.food_collected < 5:
                self.command_hive("All workers: gather food.", role="WorkerAnt")
                self.command_cooldown = 50
            elif getattr(self.sim, "predators", []):
                self.command_hive("Soldiers: defend colony.", role="SoldierAnt")
                self.command_cooldown = 50
        self.update_hunger_bar()
        self.update_thinking_indicator()
        self.update_visibility()
