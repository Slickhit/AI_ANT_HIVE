import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import random

from ant_sim import ScoutAnt, BaseAnt, MOVE_STEP, ANT_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT


class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.next_id = 1

    def _create_item(self, coords):
        item_id = self.next_id
        self.next_id += 1
        self.objects[item_id] = coords[:]
        return item_id

    def create_oval(self, x1, y1, x2, y2, fill=None):
        return self._create_item([x1, y1, x2, y2])

    def create_rectangle(self, x1, y1, x2, y2, fill=None):
        return self._create_item([x1, y1, x2, y2])

    def create_text(self, *args, **kwargs):
        return self._create_item([0, 0, 0, 0])

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


def test_scout_records_positions(monkeypatch):
    sim = FakeSim()
    scout = ScoutAnt(sim, 0, 0)
    assert (0.0, 0.0) in scout.visited

    # choose first available unexplored move
    monkeypatch.setattr(random, "choice", lambda opts: opts[0])
    scout.update()

    coords = sim.canvas.coords(scout.item)
    assert (coords[0], coords[1]) in scout.visited
    assert len(scout.visited) >= 2


def test_scout_prioritizes_unexplored(monkeypatch):
    sim = FakeSim()
    scout = ScoutAnt(sim, 0, 0)

    recorded = {}

    def fake_choice(options):
        recorded['options'] = options
        return options[0]

    monkeypatch.setattr(random, "choice", fake_choice)

    # prevent fallback to move_random
    called = {"move_random": False}

    def fake_move_random(self):
        called["move_random"] = True

    monkeypatch.setattr(BaseAnt, "move_random", fake_move_random)

    scout.update()

    # ensure move_random was not used
    assert not called["move_random"]
    assert recorded["options"]
    # options should be list of tuples (dx, dy, x, y)
    assert isinstance(recorded["options"][0], tuple)
    coords = sim.canvas.coords(scout.item)
    assert (coords[0], coords[1]) in scout.visited
