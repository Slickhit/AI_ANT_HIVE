import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ant_sim import Terrain, TILE_SAND
from ant_hive.utils import blend_color


class FakeCanvas:
    def __init__(self):
        self.objects = {}
        self.fills = {}
        self.next_id = 1

    def _create_item(self, coords, fill=None):
        item_id = self.next_id
        self.next_id += 1
        self.objects[item_id] = coords[:]
        if fill is not None:
            self.fills[item_id] = fill
        return item_id

    def create_rectangle(self, x1, y1, x2, y2, fill=None, **kwargs):
        return self._create_item([x1, y1, x2, y2], fill)

    def create_image(self, x, y, image=None, anchor="nw"):
        return self._create_item([x, y, x, y])

    def delete(self, item_id):
        self.objects.pop(item_id, None)
        self.fills.pop(item_id, None)


def test_deeper_rows_are_darker():
    canvas = FakeCanvas()
    terrain = Terrain(1, 3, canvas)
    top_fill = canvas.fills[terrain.rects[0][0]]
    bottom_fill = canvas.fills[terrain.rects[0][2]]
    assert top_fill != bottom_fill
    expected = blend_color(canvas, "black", Terrain.colors[TILE_SAND], 0.5)
    assert bottom_fill == expected
