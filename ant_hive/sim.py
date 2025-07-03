import random
import tkinter as tk
from typing import List

from .constants import WINDOW_WIDTH, WINDOW_HEIGHT, PALETTE, TILE_SIZE, PHEROMONE_DECAY
from .terrain import Terrain, TILE_ROCK
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


class AntSim:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.frame = tk.Frame(master, bg=PALETTE["frame"])
        self.frame.pack(side="left", padx=5, pady=5)
        self.canvas = tk.Canvas(self.frame, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg=PALETTE["background"], highlightthickness=0)
        self.canvas.pack()
        self.start_time = time.time()
        self.overlay = self.canvas.create_rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill="#112244", outline="", state="hidden")
        self.status_icon = self.canvas.create_text(5, 5, text="\u2600\ufe0f", anchor="nw", font=("Arial", 16))
        self.canvas.tag_raise(self.overlay)
        self.canvas.tag_raise(self.status_icon)
        self.sidebar_frame = tk.Frame(master, bg=PALETTE["frame"])
        self.sidebar_frame.pack(side="right", fill="y")
        self.food_icon = create_glowing_icon(20)
        self.spawn_button = tk.Button(self.sidebar_frame, image=self.food_icon, text="Food Drop", compound="top", borderwidth=0)
        self.spawn_button.pack(side="top")
        self.stats_label = tk.Label(self.sidebar_frame, bg=PALETTE["frame"], font=("Arial", 10))
        self.stats_label.pack(side="top")
        self.spawn_button.bind("<ButtonPress-1>", self.start_place_food)
        self.canvas.bind("<Button-1>", self.place_food)
        self.placing_food = False
        self.food_drops: List[FoodDrop] = []
        self.eggs: List[Egg] = []
        self.predators: List[Spider] = []
        self.grid_width = WINDOW_WIDTH // TILE_SIZE
        self.grid_height = WINDOW_HEIGHT // TILE_SIZE
        self.pheromones: list[list[float]] = [[0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)]
        self.pheromone_items: list[list[int | None]] = [[None for _ in range(self.grid_height)] for _ in range(self.grid_width)]
        self.terrain = Terrain(self.grid_width, self.grid_height, self.canvas)
        for _ in range(30):
            rx = random.randint(0, self.terrain.width - 1)
            ry = random.randint(self.terrain.height // 2, self.terrain.height - 1)
            self.terrain.set_cell(rx, ry, TILE_ROCK)
        self.food: int = self.canvas.create_rectangle(180, 20, 180 + 8, 20 + 8, fill="green")
        self.queen: Queen = Queen(self, 180, 570)
        self.ants: List[BaseAnt] = [
            WorkerAnt(self, 195, 295, "blue"),
            WorkerAnt(self, 215, 295, "red"),
            ScoutAnt(self, 235, 295, "black"),
            SoldierAnt(self, 255, 295, "orange"),
            NurseAnt(self, 275, 295, "pink"),
        ]
        self.predators.append(Spider(self, 50, 50))
        self.food_collected: int = 0
        self.queen_fed: int = 0
        self.update()

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
                    self.pheromones[x][y] = max(0.0, self.pheromones[x][y] - PHEROMONE_DECAY)

    def get_coords(self, item: int) -> list[float]:
        return self.canvas.coords(item)

    def check_collision(self, a: int, b: int) -> bool:
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def update(self) -> None:
        for ant in self.ants:
            ant.update()
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
        self.stats_label.configure(text=f"Food Collected: {self.food_collected}")
        self.master.after(100, self.update)
