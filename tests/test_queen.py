import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from unittest.mock import MagicMock, patch

from ant_sim import Queen, WorkerAnt, AIBaseAnt, FOOD_SIZE, ANT_SIZE

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

    def sparkle(self, x, y):
        pass

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def test_queen_feed_increases_hunger():
    sim = FakeSim()
    sim.queen.hunger = 40
    sim.queen.feed(30)
    assert sim.queen.hunger == 70
    sim.queen.feed(50)
    assert sim.queen.hunger == 100


def test_worker_ant_feeding_queen():
    sim = FakeSim()
    worker = WorkerAnt(sim, 0, 0)
    sim.ants.append(worker)
    worker.carrying_food = True
    sim.queen.hunger = 40
    worker.update()
    assert sim.queen_fed == 1
    assert not worker.carrying_food
    assert sim.queen.hunger > 40

def test_queen_creation():
    sim = FakeSim()
    assert sim.queen.hunger == 100
    assert sim.queen.spawn_timer == 300

def test_worker_feeds_queen():
    sim = FakeSim()
    worker = WorkerAnt(sim, 0, 0)
    worker.carrying_food = True
    sim.ants.append(worker)
    sim.queen.hunger = 50
    worker.update()
    assert sim.queen.hunger == 60
    assert sim.queen.fed == 1
    assert not worker.carrying_food

def test_queen_spawns_new_worker():
    FakeSim()
    # This placeholder test simply ensures construction succeeds

@patch("ant_sim.openai.ChatCompletion.create")
def test_ai_base_ant_moves_with_openai(mock_create):
    os.environ["OPENAI_API_KEY"] = "test"
    mock_create.return_value = MagicMock(choices=[MagicMock(message={"content": json.dumps({"dx": 5, "dy": -5})})])
    sim = FakeSim()
    ant = AIBaseAnt(sim, 0, 0)
    ant.update()
    coords = sim.canvas.coords(ant.item)
    assert coords[0] == 5 and coords[1] == 0
    mock_create.assert_called_once()

@patch("ant_sim.openai.ChatCompletion.create")
def test_queen_uses_openai_for_spawn(mock_create):
    os.environ["OPENAI_API_KEY"] = "test"
    mock_create.return_value = MagicMock(choices=[MagicMock(message={"content": "yes"})])
    sim = FakeSim()

    sim = FakeSim()
    sim.queen.spawn_timer = 0
    sim.queen.update()
    assert len(sim.ants) == 1
    mock_create.assert_called_once()
