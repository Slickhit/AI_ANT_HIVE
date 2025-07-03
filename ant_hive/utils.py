import time


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def brightness_at(t: float) -> float:
    cycle = t % 60.0
    phase = 30.0
    trans = 3.0
    if cycle < phase:
        if cycle < trans:
            return lerp(0.5, 1.0, cycle / trans)
        if cycle > phase - trans:
            return lerp(1.0, 0.5, (cycle - (phase - trans)) / trans)
        return 1.0
    cycle -= phase
    if cycle < trans:
        return lerp(1.0, 0.5, cycle / trans)
    if cycle > phase - trans:
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
