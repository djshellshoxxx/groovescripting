"""Sample-accurate post-synthesis automation for project tracks."""

import math

import numpy as np

RANGES = {
    "gain": (0, 4),
    "pan": (-1, 1),
    "cutoff": (10, 20000),
    "saturation": (0, 10),
}
CURVES = {"linear", "step"}


def validate(lanes):
    if lanes is None:
        return []
    if not isinstance(lanes, list):
        raise ValueError("automation must be a list")
    seen = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("automation lane must be an object")
        unknown = set(lane) - {"param", "curve", "points"}
        if unknown:
            raise ValueError("unknown automation lane keys: " + ", ".join(sorted(unknown)))
        param = lane.get("param")
        if param not in RANGES:
            raise ValueError("unsupported automation param: " + str(param))
        if param in seen:
            raise ValueError("duplicate automation param: " + param)
        seen.add(param)
        curve = lane.get("curve", "linear")
        if curve not in CURVES:
            raise ValueError("automation curve must be linear or step")
        points = lane.get("points")
        if not isinstance(points, list) or not points:
            raise ValueError("automation lane requires points")
        previous = None
        lo, hi = RANGES[param]
        for point in points:
            if not isinstance(point, dict) or set(point) != {"beat", "value"}:
                raise ValueError("automation points require beat and value")
            beat = point["beat"]
            value = point["value"]
            if (
                isinstance(beat, bool)
                or not isinstance(beat, (int, float))
                or not math.isfinite(beat)
                or beat < 0
            ):
                raise ValueError("automation beat must be finite and nonnegative")
            if previous is not None and beat <= previous:
                raise ValueError("automation point beats must be strictly increasing")
            previous = beat
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not lo <= value <= hi
            ):
                raise ValueError(f"automation {param} value must be within [{lo}, {hi}]")
    return lanes


def values(lane, beat_positions):
    validate([lane])
    points = lane["points"]
    beats = np.asarray(beat_positions, dtype=float)
    xp = np.asarray([p["beat"] for p in points], dtype=float)
    fp = np.asarray([p["value"] for p in points], dtype=float)
    if lane.get("curve", "linear") == "linear":
        return np.interp(beats, xp, fp, left=fp[0], right=fp[-1])
    indices = np.searchsorted(xp, beats, side="right") - 1
    indices = np.clip(indices, 0, len(fp) - 1)
    return fp[indices]


def apply(data, sample_rate, bpm, lanes, start_beat=0):
    """Apply validated automation to a mono/stereo float buffer."""

    validate(lanes)
    x = np.asarray(data, dtype=float).copy()
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not np.isfinite(x).all():
        raise ValueError("automation requires finite mono or stereo audio")
    if not lanes or not len(x):
        return x
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, (int, float))
        or not math.isfinite(sample_rate)
        or sample_rate <= 0
        or isinstance(bpm, bool)
        or not isinstance(bpm, (int, float))
        or not math.isfinite(bpm)
        or bpm <= 0
        or not isinstance(start_beat, (int, float))
        or isinstance(start_beat, bool)
        or not math.isfinite(start_beat)
    ):
        raise ValueError("invalid automation clock")

    beat_positions = float(start_beat) + np.arange(len(x)) * float(bpm) / (60 * float(sample_rate))
    for lane in lanes:
        curve = values(lane, beat_positions)
        param = lane["param"]
        if param == "gain":
            x *= curve[:, None]
        elif param == "pan" and x.shape[1] == 2:
            left = np.minimum(1.0, 1.0 - curve)
            right = np.minimum(1.0, 1.0 + curve)
            x[:, 0] *= left
            x[:, 1] *= right
        elif param == "cutoff":
            from .synth import lowpass

            for channel in range(x.shape[1]):
                x[:, channel] = lowpass(x[:, channel], int(sample_rate), curve)
        elif param == "saturation":
            active = curve > 0
            if np.any(active):
                drive = 1 + curve[active]
                x[active] = np.tanh(x[active] * drive[:, None]) / np.tanh(drive)[:, None]
        if not np.isfinite(x).all():
            raise ValueError("automation produced nonfinite samples")
    return x
