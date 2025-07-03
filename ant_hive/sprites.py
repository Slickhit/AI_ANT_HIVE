import tkinter as tk

from .constants import ANT_SIZE


def _load_sprites() -> list[tk.PhotoImage | None]:
    try:
        frames: list[tk.PhotoImage] = []
        for i in range(2):
            img = tk.PhotoImage(width=ANT_SIZE, height=ANT_SIZE)
            body_color = "brown"
            for x in range(ANT_SIZE):
                for y in range(ANT_SIZE):
                    if 2 <= x < ANT_SIZE - 2 and 2 <= y < ANT_SIZE - 2:
                        img.put(body_color, (x, y))
            leg_y = ANT_SIZE - 2 + (0 if i == 0 else -1)
            img.put("black", (1, leg_y))
            img.put("black", (ANT_SIZE - 2, leg_y))
            frames.append(img)
        return frames
    except Exception:
        return [None, None]


ANT_SPRITES = _load_sprites()


def create_glowing_icon(size: int = 16, inner: str = "#ffff99", outer: str = "#ff9900") -> tk.PhotoImage:
    img = tk.PhotoImage(width=size, height=size)
    cx = cy = size / 2
    ir, ig, ib = int(inner[1:3], 16), int(inner[3:5], 16), int(inner[5:7], 16)
    or_, og, ob = int(outer[1:3], 16), int(outer[3:5], 16), int(outer[5:7], 16)
    max_d = (size / 2) ** 2
    for x in range(size):
        for y in range(size):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            t = min(1.0, (dx * dx + dy * dy) / max_d)
            r = int(ir + (or_ - ir) * t)
            g = int(ig + (og - ig) * t)
            b = int(ib + (ob - ib) * t)
            img.put(f"#{r:02x}{g:02x}{b:02x}", (x, y))
    return img
