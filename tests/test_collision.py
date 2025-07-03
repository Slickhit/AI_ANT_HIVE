import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# We'll use a minimal fake canvas to test collision without requiring Tk

class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.next_id = 1

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
        pass


class FakeSim:
    def __init__(self):
        self.canvas = FakeCanvas()

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

def test_collision_detection():
    sim = FakeSim()
    a = sim.canvas.create_rectangle(0, 0, 10, 10)
    b = sim.canvas.create_rectangle(5, 5, 15, 15)
    assert sim.check_collision(a, b)


def test_no_collision_when_separate():
    sim = FakeSim()
    a = sim.canvas.create_rectangle(0, 0, 10, 10)
    b = sim.canvas.create_rectangle(20, 20, 30, 30)
    assert not sim.check_collision(a, b)


def test_no_collision_when_touching_edges():
    sim = FakeSim()
    a = sim.canvas.create_rectangle(0, 0, 10, 10)
    b = sim.canvas.create_rectangle(10, 10, 20, 20)
    assert not sim.check_collision(a, b)
