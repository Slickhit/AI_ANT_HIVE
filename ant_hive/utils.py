import time


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def brightness_at(t: float) -> float:
    """Return lighting brightness for the day\-night cycle.

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
