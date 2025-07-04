from ant_sim import Queen, Spider, BaseAnt, ANT_SIZE

class FakeText:
    def __init__(self):
        self.lines = []
    def insert(self, index, text):
        self.lines.append(text.strip())
    def see(self, index):
        pass
    def configure(self, **kwargs):
        pass

class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.next_id = 1
    def _create_item(self, coords):
        item_id = self.next_id
        self.next_id += 1
        self.objects[item_id] = coords[:]
        return item_id
    def create_oval(self, x1, y1, x2, y2, fill=None, **kw):
        return self._create_item([x1, y1, x2, y2])
    def create_rectangle(self, x1, y1, x2, y2, fill=None, **kw):
        return self._create_item([x1, y1, x2, y2])
    def create_text(self, *args, **kw):
        return self._create_item([0,0,0,0])
    def create_image(self, x, y, image=None, anchor="nw"):
        return self._create_item([x, y, x + ANT_SIZE, y + ANT_SIZE])
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
    def itemconfigure(self, item_id, **kw):
        pass

class FakeSimEgg:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.event_log = FakeText()
        self.ants = []
        self.eggs = []
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
    def log_event(self, msg):
        self.event_log.insert("end", msg)

class FakeSimSpider:
    def __init__(self):
        self.canvas = FakeCanvas()
        self.event_log = FakeText()
        self.ants = []
        self.predators = []
        self.is_night = True
    def get_coords(self, item):
        return self.canvas.coords(item)
    def check_collision(self, a, b):
        ax1, ay1, ax2, ay2 = self.get_coords(a)
        bx1, by1, bx2, by2 = self.get_coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1
    def log_event(self, msg):
        self.event_log.insert("end", msg)


def test_egg_hatching_logs_event():
    sim = FakeSimEgg()
    sim.queen.lay_egg(0, 0)
    egg = sim.eggs[0]
    egg.hatch_time = 1
    egg.update()
    assert any("Egg hatched" in line for line in sim.event_log.lines)


def test_spider_kill_logs_event():
    sim = FakeSimSpider()
    spider = Spider(sim, 0, 0)
    ant = BaseAnt(sim, 0, 0)
    ant.energy = 0
    sim.ants.append(ant)
    spider.attack_ants()
    assert any("Spider killed" in line for line in sim.event_log.lines)
