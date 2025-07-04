import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import (
    WorkerAnt,
    TILE_SIZE,
    PHEROMONE_DECAY,
    SCOUT_PHEROMONE_AMOUNT,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    ANT_SIZE,
)

class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.next_id = 1

    def _create_item(self, coords):
        item_id = self.next_id
        self.next_id += 1
        self.objects[item_id] = coords[:]
        return item_id

    def create_oval(self, x1, y1, x2, y2, fill=None, **kwargs):
        return self._create_item([x1, y1, x2, y2])

    def create_rectangle(self, x1, y1, x2, y2, fill=None, **kwargs):
        return self._create_item([x1, y1, x2, y2])

    def create_text(self, *args, **kwargs):
        return self._create_item([0, 0, 0, 0])

    def create_image(self, x, y, image=None, anchor="nw"):
        return self._create_item([x, y, x + ANT_SIZE, y + ANT_SIZE])

    def create_line(self, x1, y1, x2, y2, **kwargs):
        return self._create_item([x1, y1, x2, y2])

    def delete(self, item_id):
        self.objects.pop(item_id, None)

    def after(self, delay, func=None):
        if func:
            func()

    def move(self, item_id, dx, dy):
        x1, y1, x2, y2 = self.objects[item_id]
        self.objects[item_id] = [x1 + dx, y1 + dy, x2 + dx, y2 + dy]

    def coords(self, item_id):
        return self.objects[item_id]

    def itemconfigure(self, item_id, **kwargs):
        pass

class FakeSim:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.food = self.canvas.create_rectangle(0, 0, ANT_SIZE, ANT_SIZE, fill="green")
        self.queen = type("Q", (), {"item": self.canvas.create_oval(0,0,ANT_SIZE,ANT_SIZE)})
        self.ants = []
        self.food_collected = 0
        self.queen_fed = 0
        self.grid_width = WINDOW_WIDTH // TILE_SIZE
        self.grid_height = WINDOW_HEIGHT // TILE_SIZE
        self.pheromones = {
            "food": [[0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)],
            "danger": [[0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)],
            "scout": [[0.0 for _ in range(self.grid_height)] for _ in range(self.grid_width)],
        }

    def deposit_pheromone(self, x, y, amount, ptype="scout", prev=None):
        grid = self.pheromones[ptype]
        gx = int(x) // TILE_SIZE
        gy = int(y) // TILE_SIZE
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            grid[gx][gy] += amount

    def get_pheromone(self, x, y, ptype="scout"):
        grid = self.pheromones[ptype]
        gx = int(x) // TILE_SIZE
        gy = int(y) // TILE_SIZE
        if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
            return grid[gx][gy]
        return 0.0

    def decay_pheromones(self):
        for grid in self.pheromones.values():
            for x in range(self.grid_width):
                for y in range(self.grid_height):
                    if grid[x][y] > 0:
                        grid[x][y] = max(0.0, grid[x][y] - PHEROMONE_DECAY)

    def move_food(self):
        pass

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def test_pheromone_decay():
    sim = FakeSim()
    sim.deposit_pheromone(0, 0, SCOUT_PHEROMONE_AMOUNT)
    sim.decay_pheromones()
    assert sim.pheromones["scout"][0][0] == SCOUT_PHEROMONE_AMOUNT - PHEROMONE_DECAY


def test_worker_follows_pheromone():
    sim = FakeSim()
    # deposit pheromone to the right of starting tile
    sim.deposit_pheromone(TILE_SIZE, 0, 1.0, "food")
    worker = WorkerAnt(sim, 0, 0)
    sim.ants.append(worker)
    worker.update()
    x1, y1, x2, y2 = sim.canvas.coords(worker.item)
    assert x1 > 0  # moved towards pheromone


def test_multiple_pheromone_types_independent():
    sim = FakeSim()
    sim.deposit_pheromone(0, 0, 2.0, "scout")
    sim.deposit_pheromone(0, 0, 1.0, "food")
    sim.decay_pheromones()
    assert sim.pheromones["scout"][0][0] == 2.0 - PHEROMONE_DECAY
    assert sim.pheromones["food"][0][0] == 1.0 - PHEROMONE_DECAY
