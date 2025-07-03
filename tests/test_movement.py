import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import random

from ant_sim import (
    BaseAnt,
    MOVE_STEP,
    ANT_SIZE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    Terrain,
    TILE_SIZE,
    TILE_TUNNEL,
    TILE_SAND,
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


class FakeSimWithTerrain(FakeSim):
    def __init__(self):
        super().__init__()
        self.terrain = Terrain(3, 3, self.canvas)


class DummyTarget:
    def __init__(self, sim, x1, y1, x2, y2):
        self.item = sim.canvas.create_rectangle(x1, y1, x2, y2)
        self.sim = sim


class TestBaseAntMovement:
    def test_move_towards_positive_direction(self):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)
        target = DummyTarget(sim, 20, 0, 30, 10)
        ant.move_towards(target.item)
        x1, y1, x2, y2 = sim.canvas.coords(ant.item)
        assert (x1, y1) == (MOVE_STEP, 0)
        assert (x2, y2) == (MOVE_STEP + 10, 10)

    def test_move_towards_negative_direction(self):
        sim = FakeSim()
        ant = BaseAnt(sim, 20, 20)
        target = DummyTarget(sim, 0, 20, 10, 30)
        ant.move_towards(target.item)
        x1, y1, x2, y2 = sim.canvas.coords(ant.item)
        assert (x1, y1) == (20 - MOVE_STEP, 20)
        assert (x2, y2) == (20 - MOVE_STEP + 10, 30)

    def test_move_random(self, monkeypatch):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)

        choices = [MOVE_STEP, -MOVE_STEP]

        def fake_choice(options):
            return choices.pop(0)

        monkeypatch.setattr(random, "choice", fake_choice)
        ant.move_random()
        x1, y1, x2, y2 = sim.canvas.coords(ant.item)
        assert (x1, y1) == (MOVE_STEP, 0)
        assert (x2, y2) == (MOVE_STEP + 10, 10)

    def test_move_random_stays_within_bounds(self, monkeypatch):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)

        # Force movement that would go outside the canvas
        monkeypatch.setattr(random, "choice", lambda options: -MOVE_STEP)
        ant.move_random()
        x1, y1, x2, y2 = sim.canvas.coords(ant.item)
        assert x1 == 0 and y1 == 0
        assert x2 == ANT_SIZE and y2 == ANT_SIZE

    def test_move_towards_stays_within_bounds(self):
        sim = FakeSim()
        # place ant in bottom-right corner
        start_x = WINDOW_WIDTH - ANT_SIZE
        start_y = WINDOW_HEIGHT - ANT_SIZE
        ant = BaseAnt(sim, start_x, start_y)
        # target outside canvas to the bottom-right
        target = DummyTarget(sim, WINDOW_WIDTH + 20, WINDOW_HEIGHT + 20,
                             WINDOW_WIDTH + 30, WINDOW_HEIGHT + 30)
        ant.move_towards(target.item)
        x1, y1, x2, y2 = sim.canvas.coords(ant.item)
        assert x1 == start_x and y1 == start_y
        assert x2 == start_x + ANT_SIZE and y2 == start_y + ANT_SIZE

    def test_digging_costs_more_energy(self):
        sim = FakeSimWithTerrain()
        ant = BaseAnt(sim, 0, 0, energy=10)
        ant.attempt_move(TILE_SIZE, 0)
        assert ant.energy == 8
        assert sim.terrain.get_cell(1, 0) == TILE_TUNNEL

    def test_tunnel_movement_costs_one_energy(self):
        sim = FakeSimWithTerrain()
        sim.terrain.set_cell(1, 0, TILE_TUNNEL)
        ant = BaseAnt(sim, 0, 0, energy=10)
        ant.attempt_move(TILE_SIZE, 0)
        assert ant.energy == 9
