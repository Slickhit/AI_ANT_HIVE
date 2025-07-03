import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import Queen, WorkerAnt, ANT_SIZE, FOOD_SIZE


class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.next_id = 1
        self.configured = {}

    def _create_item(self, coords):
        item_id = self.next_id
        self.next_id += 1
        self.objects[item_id] = coords[:]
        return item_id

    def create_rectangle(self, x1, y1, x2, y2, fill=None):
        return self._create_item([x1, y1, x2, y2])

    def create_oval(self, x1, y1, x2, y2, fill=None):
        return self._create_item([x1, y1, x2, y2])

    def create_text(self, *args, **kwargs):
        return self._create_item([0, 0, 0, 0])

    def move(self, item_id, dx, dy):
        x1, y1, x2, y2 = self.objects[item_id]
        self.objects[item_id] = [x1 + dx, y1 + dy, x2 + dx, y2 + dy]

    def coords(self, item_id):
        return self.objects[item_id]

    def itemconfigure(self, item_id, **kwargs):
        self.configured[item_id] = kwargs


class FakeSim:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.food = self.canvas.create_rectangle(0, 0, FOOD_SIZE, FOOD_SIZE, fill="green")
        self.ants = []
        self.food_collected = 0
        self.queen_fed = 0
        self.queen = Queen(self, 0, 0)

    def move_food(self):
        pass

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def test_queen_creation():
    sim = FakeSim()
    assert sim.queen.hunger == 100
    assert sim.queen.spawn_timer == 300


def test_worker_feeds_queen():
    sim = FakeSim()
    worker = WorkerAnt(sim, 0, 0)
    worker.carrying_food = True
    sim.queen.hunger = 50
    worker.update()
    assert sim.queen.hunger == 60
    assert sim.queen_fed == 1
    assert not worker.carrying_food


def test_queen_spawns_new_worker():
    sim = FakeSim()
    sim.queen.spawn_timer = 0
    initial_count = len(sim.ants)
    sim.queen.update()
    assert len(sim.ants) == initial_count + 1
    assert sim.queen.spawn_timer == 300
    assert sim.queen.hunger < 100
