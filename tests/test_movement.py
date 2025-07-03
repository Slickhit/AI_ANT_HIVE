import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import random

import pytest

from ant_sim import BaseAnt, MOVE_STEP


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
        assert (x1, y1) == (MOVE_STEP, -MOVE_STEP)
        assert (x2, y2) == (MOVE_STEP + 10, -MOVE_STEP + 10)
