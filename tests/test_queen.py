import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import Queen, WorkerAnt


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
        self.food = self.canvas.create_rectangle(0, 0, 8, 8, fill="green")
        self.queen_fed = 0
        self.food_collected = 0
        self.ants = []
        # Place queen at origin for easier collision
        self.queen = Queen(self, 0, 0)

    def move_food(self):
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
