def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def brightness_at(t: float) -> float:
    """Return lighting brightness for the day-night cycle.

    The cycle lasts 60 seconds with 30 seconds of day and 30 seconds of night.
    A short transition of two seconds is applied at the edges using linear
    interpolation so the lighting changes smoothly.
    """

    cycle = t % 60.0
    phase = 30.0
    trans = 2.0

    if cycle < phase:
        # Day time
        if cycle < trans:
            # Night \-> day transition
            return lerp(0.5, 1.0, cycle / trans)
        if cycle > phase - trans:
            # Day \-> night transition
            return lerp(1.0, 0.5, (cycle - (phase - trans)) / trans)
        return 1.0

    cycle -= phase
    # Night time
    if cycle < trans:
        # Day \-> night transition
        return lerp(1.0, 0.5, cycle / trans)
    if cycle > phase - trans:
        # Night \-> day transition
        return lerp(0.5, 1.0, (cycle - (phase - trans)) / trans)
    return 0.5


def stipple_from_brightness(val: float) -> str:
    alpha = (1.0 - val) / 0.5
    if alpha > 0.75:
        return "gray75"
    if alpha > 0.5:
        return "gray50"
    if alpha > 0.25:
        return "gray25"
    return "gray12"


def blend_color(canvas, fg: str, bg: str, alpha: float) -> str:
    """Blend ``fg`` over ``bg`` with transparency ``alpha``.

    Parameters
    ----------
    canvas: tk.Canvas
        Canvas used to resolve color names to RGB values.
    fg: str
        Foreground color string.
    bg: str
        Background color string.
    alpha: float
        Weight for ``fg`` in the range ``0.0`` to ``1.0``.

    Returns
    -------
    str
        Hex color string representing the blended color.
    """
    def _to_rgb(c: str) -> tuple[int, int, int]:
        if hasattr(canvas, "winfo_rgb"):
            try:
                r, g, b = canvas.winfo_rgb(c)
                return r // 256, g // 256, b // 256
            except Exception:
                pass
        if c.startswith("#") and len(c) == 7:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        basic = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 128, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "orange": (255, 165, 0),
            "pink": (255, 192, 203),
            "brown": (165, 42, 42),
            "purple": (128, 0, 128),
        }
        return basic.get(c.lower(), (0, 0, 0))

    fr, fg_, fb = _to_rgb(fg)
    br, bg_, bb = _to_rgb(bg)
    r = int(fr * alpha + br * (1.0 - alpha))
    g = int(fg_ * alpha + bg_ * (1.0 - alpha))
    b = int(fb * alpha + bb * (1.0 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"
