import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import AntSim, ANT_SIZE, PREDATOR_ALERT_RANGE


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


class FakeMaster:
    def __init__(self):
        self.after_calls = []
        self.bell_called = False

    def after(self, delay, func=None):
        self.after_calls.append(delay)
        # don't call func to avoid recursion

    def bell(self):
        self.bell_called = True


class FakeFrame:
    def __init__(self):
        self.children = []

    def pack(self, *args, **kwargs):
        pass


class FakeLabel:
    def __init__(self, master=None, **kwargs):
        if master is not None and hasattr(master, "children"):
            master.children.append(self)
        self.kwargs = kwargs

    def pack(self, *args, **kwargs):
        pass

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def destroy(self):
        pass


def test_predator_alert_created(monkeypatch):
    sim = type("S", (), {})()
    sim.canvas = FakeCanvas()
    sim.master = FakeMaster()
    sim.sidebar_frame = FakeFrame()
    sim.predators = [type("P", (), {"item": sim.canvas.create_oval(PREDATOR_ALERT_RANGE - 10, 0, PREDATOR_ALERT_RANGE, ANT_SIZE)})]
    sim.queen = type("Q", (), {"item": sim.canvas.create_oval(0, 0, ANT_SIZE, ANT_SIZE)})
    sim.predator_alert_label = None
    sim._alert_job = None
    sim._alert_flash_state = False
    sim._flash_predator_alert = lambda *a, **k: None
    sim._show_predator_alert = AntSim._show_predator_alert.__get__(sim, AntSim)
    sim._hide_predator_alert = AntSim._hide_predator_alert.__get__(sim, AntSim)

    import ant_hive.sim as sim_mod
    monkeypatch.setattr(sim_mod.tk, "Label", FakeLabel)
    AntSim._update_predator_alert(sim)

    assert isinstance(sim.predator_alert_label, FakeLabel)

