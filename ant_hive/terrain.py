import tkinter as tk

from .utils import blend_color

TILE_SIZE = 20
TILE_SAND = "sand"
TILE_TUNNEL = "tunnel"
TILE_ROCK = "rock"
TILE_COLLAPSED = "collapsed"

SAND_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAARklEQVR4nO3QMRHAMBADwctjEPRg",
    "MgSjEAenyJiArfLVqdninjneZZs9Sdz8SmKSqCRm+wdTGEAlMeiGCbwbdsOD3w3v8Q8txS8qFa7u",
    "XQAAAABJRU5ErkJggg==",
)
TUNNEL_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAARklEQVR4nO3QMRHAMBADwctjEIsg",
    "NA/DFAenyJiArfLVqdninjneZZs9Sdz8SmKSqCRm+wdTGEAlMeiGCbwbdsOD3w3v8Q8OIi4y+xWE",
    "tQAAAABJRU5ErkJggg==",
)
ROCK_TEXTURE = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAQklEQVR4nO3QsRHAQAwCwbNqoHO1",
    "SQ/+4McNWIQiI9ngnu5+bfNNEpNfSUwSlcRsXzCFAVQSg22YwLfhNvzxt+EcPz04LrP+YyCNAAAA",
    "AElFTkSuQmCC",
)

class Terrain:
    """Simple 2D grid representing the underground."""

    colors = {
        TILE_SAND: "#c2b280",
        TILE_TUNNEL: "#806517",
        TILE_ROCK: "#7f7f7f",
        TILE_COLLAPSED: "black",
    }

    texture_data = {
        TILE_SAND: SAND_TEXTURE,
        TILE_TUNNEL: TUNNEL_TEXTURE,
        TILE_ROCK: ROCK_TEXTURE,
    }

    def __init__(self, width: int, height: int, canvas: tk.Canvas) -> None:
        self.width = width
        self.height = height
        self.canvas = canvas
        # Define zones used for future colony organization if the map
        # is large enough for city planning logic.
        if width >= 80 and height >= 60:
            self.zones = {
                "center": (20, 20, 40, 40),
                "food_storage": (10, 45, 30, 55),
                "nursery": (50, 45, 70, 55),
            }
        else:
            self.zones = {}
        self.images: dict[str, tk.PhotoImage | None] = {}
        for key, data in self.texture_data.items():
            try:
                self.images[key] = tk.PhotoImage(data=data)
            except Exception:
                self.images[key] = None
        self.grid: list[list[str]] = [
            [TILE_SAND for _ in range(height)] for _ in range(width)
        ]
        if width >= 10 and height >= 10:
            for x in range(width):
                for y in range(height):
                    if x < 5 or x > width - 5 or y > height - 5:
                        self.grid[x][y] = TILE_ROCK
        self.rects: list[list[int]] = [[0] * height for _ in range(width)]
        self.shades: list[list[int]] = [[0] * height for _ in range(width)]
        self.explored: list[list[bool]] = [
            [True for _ in range(height)] for _ in range(width)
        ]
        self.fog: list[list[int]] = [[0] * height for _ in range(width)]
        self._render()

    def _depth_color(self, color: str, y: int) -> str:
        """Return a darker shade of ``color`` based on vertical index ``y``."""
        if self.height <= 1:
            return color
        alpha = (y / (self.height - 1)) * 0.5
        return blend_color(self.canvas, "black", color, alpha)

    def _render(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                state = self.grid[x][y]
                if hasattr(self.canvas, "create_image") and self.images.get(state):
                    rect = self.canvas.create_image(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        anchor="nw",
                        image=self.images[state],
                    )
                else:
                    color = self.colors[state]
                    if state in (TILE_SAND, TILE_TUNNEL):
                        color = self._depth_color(color, y)
                    rect = self.canvas.create_rectangle(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        (x + 1) * TILE_SIZE,
                        (y + 1) * TILE_SIZE,
                        fill=color,
                    )
                self.rects[x][y] = rect
                self._update_shading(x, y)
                self._update_fog(x, y)

    def _update_shading(self, x: int, y: int) -> None:
        if self.shades[x][y]:
            if hasattr(self.canvas, "delete"):
                self.canvas.delete(self.shades[x][y])
            self.shades[x][y] = 0
        state = self.grid[x][y]
        if state != TILE_TUNNEL:
            return
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if self.get_cell(nx, ny) != TILE_TUNNEL:
                self.shades[x][y] = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill="#000000",
                    stipple="gray50",
                    outline="",
                )
                break

    def _update_fog(self, x: int, y: int) -> None:
        if self.fog[x][y]:
            if hasattr(self.canvas, "delete"):
                self.canvas.delete(self.fog[x][y])
            self.fog[x][y] = 0
        if not self.explored[x][y]:
            self.fog[x][y] = self.canvas.create_rectangle(
                x * TILE_SIZE,
                y * TILE_SIZE,
                (x + 1) * TILE_SIZE,
                (y + 1) * TILE_SIZE,
                fill="#000000",
                stipple="gray75",
                outline="",
            )

    def set_explored(self, x: int, y: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            if not self.explored[x][y]:
                self.explored[x][y] = True
                if self.fog[x][y]:
                    if hasattr(self.canvas, "delete"):
                        self.canvas.delete(self.fog[x][y])
                    self.fog[x][y] = 0

    def initialize_explored(self, cx: int, cy: int, radius: int = 3) -> None:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                self.set_explored(cx + dx, cy + dy)

    def expand(self, new_width: int, new_height: int) -> None:
        if new_width <= self.width and new_height <= self.height:
            return
        for x in range(self.width, new_width):
            self.grid.append([TILE_SAND for _ in range(self.height)])
            self.rects.append([0] * self.height)
            self.shades.append([0] * self.height)
            self.explored.append([True] * self.height)
            self.fog.append([0] * self.height)
        for x in range(new_width):
            self.grid[x].extend([TILE_SAND] * (new_height - len(self.grid[x])))
            self.rects[x].extend([0] * (new_height - len(self.rects[x])))
            self.shades[x].extend([0] * (new_height - len(self.shades[x])))
            self.explored[x].extend([True] * (new_height - len(self.explored[x])))
            self.fog[x].extend([0] * (new_height - len(self.fog[x])))
        old_width, old_height = self.width, self.height
        self.width, self.height = new_width, new_height
        for x in range(old_width, new_width):
            for y in range(new_height):
                state = self.grid[x][y]
                if hasattr(self.canvas, "create_image") and self.images.get(state):
                    rect = self.canvas.create_image(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        anchor="nw",
                        image=self.images[state],
                    )
                else:
                    rect = self.canvas.create_rectangle(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        (x + 1) * TILE_SIZE,
                        (y + 1) * TILE_SIZE,
                        fill=self.colors[state],
                    )
                self.rects[x][y] = rect
                self._update_shading(x, y)
                self._update_fog(x, y)
        for x in range(0, old_width):
            for y in range(old_height, new_height):
                state = self.grid[x][y]
                if hasattr(self.canvas, "create_image") and self.images.get(state):
                    rect = self.canvas.create_image(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        anchor="nw",
                        image=self.images[state],
                    )
                else:
                    rect = self.canvas.create_rectangle(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        (x + 1) * TILE_SIZE,
                        (y + 1) * TILE_SIZE,
                        fill=self.colors[state],
                    )
                self.rects[x][y] = rect
                self._update_shading(x, y)
                self._update_fog(x, y)

    def get_cell(self, x: int, y: int) -> str:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return TILE_ROCK
        return self.grid[x][y]

    def set_cell(self, x: int, y: int, state: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x][y] = state
            if hasattr(self.canvas, "delete"):
                self.canvas.delete(self.rects[x][y])
                if self.shades[x][y]:
                    self.canvas.delete(self.shades[x][y])
            if hasattr(self.canvas, "create_image") and self.images.get(state):
                self.rects[x][y] = self.canvas.create_image(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    anchor="nw",
                    image=self.images[state],
                )
            else:
                color = self.colors[state]
                if state in (TILE_SAND, TILE_TUNNEL):
                    color = self._depth_color(color, y)
                self.rects[x][y] = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill=color,
                )
            self._update_shading(x, y)
            self._update_fog(x, y)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._update_shading(nx, ny)
                    self._update_fog(nx, ny)
