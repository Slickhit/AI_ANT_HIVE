import random
import tkinter as tk
from typing import List
import time


from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    PALETTE,
    TILE_SIZE,
    PHEROMONE_DECAY,
    MONO_FONT,
    FOOD_SIZE,
)
from .terrain import Terrain, TILE_ROCK, TILE_TUNNEL
from .sprites import create_glowing_icon
from .entities.base_ant import BaseAnt
from .entities.worker import WorkerAnt
from .entities.scout import ScoutAnt
from .entities.soldier import SoldierAnt
from .entities.nurse import NurseAnt
from .entities.queen import Queen
from .entities.spider import Spider
from .entities.egg import Egg
from .entities.food import FoodDrop
from .utils import brightness_at, stipple_from_brightness


# Depth of diggable soil above the rocky layer at the bottom of the map.
DIRT_DEPTH = 5


class AntSim:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.frame = tk.Frame(master, bg=PALETTE["frame"])
        self.frame.pack(side="left", padx=5, pady=5)
        self.canvas = tk.Canvas(
            self.frame,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=PALETTE["background"],
            highlightthickness=0,
        )
        self.canvas.pack()
        self.start_time = time.time()
        self.is_night = False
        self.overlay = self.canvas.create_rectangle(
            0,
            0,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            fill="#112244",
            outline="",
            state="hidden",
        )
        self.current_day = 1
        self.status_icon = self.canvas.create_text(
            5,
            5,
            text="\u2600\ufe0f Day 1",
            anchor="nw",
            font=("Arial", 16),
        )
        self.canvas.tag_raise(self.overlay)
        self.canvas.tag_raise(self.status_icon)
        self.sidebar_frame = tk.Frame(master, bg=PALETTE["frame"])
        self.sidebar_frame.pack(side="right", fill="y")
        self.food_icon = create_glowing_icon(20)
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

        # Panel for individual ant statistics
        self.ant_panel = tk.Frame(self.sidebar_frame, bg="#f9ebcc")
        self.ant_panel.pack(side="top", fill="both", expand=True, pady=5)
        tk.Label(
            self.ant_panel,
            text="Ant Stats:",
            font=("Arial", 10, "bold"),
            bg="#f9ebcc",
            anchor="w",
        ).pack(fill="x")
        self.ant_canvas = tk.Canvas(
            self.ant_panel,
            bg="#f9ebcc",
            highlightthickness=0,
        )
        self.ant_scroll = tk.Scrollbar(
            self.ant_panel, orient="vertical", command=self.ant_canvas.yview
        )
        self.ant_canvas.configure(yscrollcommand=self.ant_scroll.set)
        self.ant_scroll.pack(side="right", fill="y")
        self.ant_canvas.pack(side="left", fill="both", expand=True)
        self.ant_list = tk.Frame(self.ant_canvas, bg="#f9ebcc")
        self.ant_window = self.ant_canvas.create_window(
            (0, 0), window=self.ant_list, anchor="nw"
        )

        self.ant_list.bind(
            "<Configure>",
            lambda e: self.ant_canvas.configure(
                scrollregion=self.ant_canvas.bbox("all")
            ),
        )

        self.ant_canvas.bind(
            "<Configure>",
            lambda e: self.ant_canvas.itemconfigure(self.ant_window, width=e.width),
        )

        # Panel for overall colony statistics
        self.colony_panel = tk.Frame(self.sidebar_frame, bg="#f9ebcc")
        self.colony_panel.pack(side="top", fill="x", pady=5)
        tk.Label(
            self.colony_panel,
            text="Colony Stats:",
            font=("Arial", 10, "bold"),
            bg="#f9ebcc",
            anchor="w",
        ).pack(fill="x")
        self.colony_stats_label = tk.Label(
            self.colony_panel,
            bg="#f9ebcc",
            anchor="w",
            justify="left",
            font=MONO_FONT,
        )
        self.colony_stats_label.pack(fill="x")
        self.spawn_button.bind("<ButtonPress-1>", self.start_place_food)
        self.canvas.bind("<Button-1>", self.place_food)
        self.placing_food = False
        self.food_drops: List[FoodDrop] = []
        self.eggs: List[Egg] = []
        self.predators: List[Spider] = []
        self.grid_width = WINDOW_WIDTH // TILE_SIZE
        self.grid_height = WINDOW_HEIGHT // TILE_SIZE
        self.pheromones: list[list[float]] = [
            [0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)
        ]
        self.pheromone_items: list[list[int | None]] = [
            [None for _ in range(self.grid_height)] for _ in range(self.grid_width)
        ]
        self.terrain = Terrain(self.grid_width, self.grid_height, self.canvas)
        for _ in range(30):
            rx = random.randint(0, self.terrain.width - 1)
            ry = random.randint(self.terrain.height // 2, self.terrain.height - 1)
            self.terrain.set_cell(rx, ry, TILE_ROCK)
        start_x = self.grid_width // 2
        start_y = self.grid_height // 2

        center_x = start_x * TILE_SIZE
        center_y = start_y * TILE_SIZE
        self.food: int | None = None
        self.queen: Queen = Queen(self, center_x, center_y)
        self.ants: List[BaseAnt] = [
            WorkerAnt(self, center_x + 15, center_y + 5, "blue"),
            WorkerAnt(self, center_x + 35, center_y + 5, "red"),
            ScoutAnt(self, center_x + 55, center_y + 5, "black"),
            SoldierAnt(self, center_x + 75, center_y + 5, "orange"),
            NurseAnt(self, center_x + 95, center_y + 5, "pink"),
        ]
        self.predators.append(Spider(self, 50, TILE_SIZE * 2))
        self.food_collected: int = 0
        self.queen_fed: int = 0
        self.ant_labels: dict[int, tk.Label] = {}
        self.update()

    def update_lighting(self) -> None:
        """Update overlay brightness and day/night icon."""
        t = time.time() - self.start_time
        brightness = brightness_at(t)

        if brightness >= 0.999:
            # Daytime without overlay
            self.canvas.itemconfigure(self.overlay, state="hidden")
            for predator in self.predators:
                predator.set_visible(False)
        else:
            self.canvas.itemconfigure(
                self.overlay,
                state="normal",
                stipple=stipple_from_brightness(brightness),
            )
            for predator in self.predators:
                predator.set_visible(True)

        cycle = t % 60.0
        self.is_night = cycle >= 30.0
        icon = "\u2600\ufe0f" if cycle < 30.0 else "\U0001f319"
        self.current_day = int(t // 60.0) + 1
        self.canvas.itemconfigure(self.status_icon, text=f"{icon} Day {self.current_day}")


    def refresh_ant_stats(self) -> None:
        active_ids = set()
        for ant in self.ants:
            active_ids.add(ant.ant_id)
            text = f"\u25a0 ID {ant.ant_id:04d} | {ant.role} | E:{int(ant.energy)} | {ant.status}"
            label = self.ant_labels.get(ant.ant_id)
            if label is None:
                label = tk.Label(
                    self.ant_list,
                    text=text,
                    anchor="w",
                    bg="#fbe0cc",
                    fg=getattr(ant, "color", "black"),
                    font=("Arial", 9),
                )
                label.pack(fill="x")
                self.ant_labels[ant.ant_id] = label
            else:
                label.configure(text=text, fg=getattr(ant, "color", "black"))

        for ant_id in list(self.ant_labels.keys()):
            if ant_id not in active_ids:
                self.ant_labels[ant_id].destroy()
                del self.ant_labels[ant_id]

    def refresh_colony_stats(self) -> None:
        stats = (
            f"Food: {self.food_collected}\n"
            f"Queen Hunger: {int(self.queen.hunger)}\n"
            f"Ants: {len(self.ants)}\n"
            f"Eggs: {len(self.eggs)}\n"
            f"Queen Thought: {self.queen.thought()}"
        )
        self.colony_stats_label.configure(text=stats)

    def start_place_food(self, _event) -> None:
        self.placing_food = True

    def place_food(self, event) -> None:
        if not self.placing_food:
            return
        self.food_drops.append(FoodDrop(self, event.x, event.y))
        self.placing_food = False

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
                    self.pheromones[x][y] = max(
                        0.0, self.pheromones[x][y] - PHEROMONE_DECAY
                    )

    def get_coords(self, item: int) -> list[float]:
        return self.canvas.coords(item)

    def check_collision(self, a: int, b: int) -> bool:
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def move_food(self) -> None:
        """Randomly reposition the main food source within canvas bounds."""
        if self.food is None:
            return
        x = random.randint(0, WINDOW_WIDTH - FOOD_SIZE)
        y = random.randint(0, WINDOW_HEIGHT - FOOD_SIZE)
        self.canvas.coords(self.food, x, y, x + FOOD_SIZE, y + FOOD_SIZE)

    def sparkle(self, x: float, y: float) -> None:
        """Display a short-lived sparkle effect at the given coordinates."""
        radius = 6
        item = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius, fill="yellow", outline=""
        )
        self.canvas.after(250, lambda i=item: self.canvas.delete(i))

    def update(self) -> None:
        self.update_lighting()
        for ant in self.ants[:]:
            ant.update()
            if ant.alive:
                ant.update_energy_bar()
        for predator in self.predators[:]:
            predator.update()
        for egg in self.eggs[:]:
            egg.update()
        self.queen.update()
        for drop in self.food_drops[:]:
            if drop.charges <= 0:
                self.food_drops.remove(drop)
        self.decay_pheromones()
        stats = (
            f"Food Collected: {self.food_collected}\n"
            f"Fed to Queen: {self.queen_fed}\n"
            f"Ants Active: {len(self.ants)}\n"
            f"Eggs: {len(self.eggs)}\n"
            f"Predators: {len(self.predators)}"
        )
        self.stats_label.configure(text=stats)
        self.refresh_ant_stats()
        self.refresh_colony_stats()
        self.master.after(100, self.update)
