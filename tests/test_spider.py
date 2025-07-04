import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import Spider, BaseAnt, ANT_SIZE


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

    def coords(self, item_id, *args):
        if args:
            self.objects[item_id] = list(args)
        return self.objects[item_id]

    def itemconfigure(self, item_id, **kwargs):
        pass


class FakeSim:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.ants = []
        self.predators = []
        self.is_night = True

    def get_coords(self, item):
        return self.canvas.coords(item)

    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def test_spider_brain_moves_towards_ant():
    sim = FakeSim()
    spider = Spider(sim, 0, 0)
    ant = BaseAnt(sim, 50, 0)
    sim.ants.append(ant)
    spider.brain_move()
    coords = sim.canvas.coords(spider.item)
    assert coords[0] > 0


def test_spider_hunger_increases_after_three_ants():
    sim = FakeSim()
    spider = Spider(sim, 0, 0)
    ants = [BaseAnt(sim, 0, 0) for _ in range(3)]
    for ant in ants:
        ant.energy = 0
        sim.ants.append(ant)
    spider.attack_ants()
    assert spider.hunger == 1


def test_spider_update_skips_during_day():
    sim = FakeSim()
    sim.is_night = False
    spider = Spider(sim, 0, 0)
    ant = BaseAnt(sim, 0, 0)
    sim.ants.append(ant)
    start_coords = sim.canvas.coords(spider.item)
    spider.update()
    assert sim.canvas.coords(spider.item) == start_coords
    assert ant.energy == 100


def test_spider_lays_eggs_on_death():
    sim = FakeSim()
    spider = Spider(sim, 0, 0)
    sim.predators.append(spider)
    spider.vitality = 0
    spider.update()
    assert spider.has_laid_eggs
    assert len(sim.predators) == 3


def test_spider_growth_increases_speed():
    sim = FakeSim()
    spider = Spider(sim, 0, 0)
    start_speed = spider.speed
    start_consumption = spider.food_consumption
    spider.sleep_cycle()
    assert spider.size > 1.0
    assert spider.speed > start_speed
    assert spider.food_consumption > start_consumption
