import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import (
    BaseAnt,
    MOVE_ENERGY_COST,
    DIG_ENERGY_COST,
    REST_ENERGY_GAIN,
    ENERGY_MAX,
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


class TestEnergy:
    def test_move_consumes_energy(self, monkeypatch):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)
        start = ant.energy
        monkeypatch.setattr(random, "choice", lambda options: 0)
        ant.move_random()
        assert ant.energy == start - MOVE_ENERGY_COST

    def test_dig_consumes_energy(self):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)
        start = ant.energy
        ant.dig()
        assert ant.energy == start - DIG_ENERGY_COST

    def test_rest_recovers_energy(self):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)
        ant.energy = 0
        ant.rest()
        assert ant.energy == REST_ENERGY_GAIN

    def test_update_rests_when_energy_empty(self, monkeypatch):
        sim = FakeSim()
        ant = BaseAnt(sim, 0, 0)
        ant.energy = 1
        monkeypatch.setattr(random, "choice", lambda options: 0)
        ant.update()
        pos = sim.canvas.coords(ant.item)
        assert ant.energy == 0
        ant.update()
        assert sim.canvas.coords(ant.item) == pos
        assert ant.energy == REST_ENERGY_GAIN
