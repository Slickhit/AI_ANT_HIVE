import tkinter as tk

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
        self.images: dict[str, tk.PhotoImage | None] = {}
        for key, data in self.texture_data.items():
            try:
                self.images[key] = tk.PhotoImage(data=data)
            except Exception:
                self.images[key] = None
        self.grid: list[list[str]] = [
            [TILE_SAND for _ in range(height)] for _ in range(width)
        ]
        self.rects: list[list[int]] = [[0] * height for _ in range(width)]
        self.shades: list[list[int]] = [[0] * height for _ in range(width)]
        self._render()

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
                    rect = self.canvas.create_rectangle(
                        x * TILE_SIZE,
                        y * TILE_SIZE,
                        (x + 1) * TILE_SIZE,
                        (y + 1) * TILE_SIZE,
                        fill=self.colors[state],
                    )
                self.rects[x][y] = rect
                self._update_shading(x, y)

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
                self.rects[x][y] = self.canvas.create_rectangle(
                    x * TILE_SIZE,
                    y * TILE_SIZE,
                    (x + 1) * TILE_SIZE,
                    (y + 1) * TILE_SIZE,
                    fill=self.colors[state],
                )
            self._update_shading(x, y)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._update_shading(nx, ny)
