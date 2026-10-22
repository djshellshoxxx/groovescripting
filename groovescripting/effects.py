"""Ordered offline effects with explicit tail policies."""

import numpy as np
from scipy.signal import lfilter

from .audio import buffer, rate


def _number(effect, key, default, lo=None, hi=None):
    v = float(effect.get(key, default))
    if not np.isfinite(v) or (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValueError(f"invalid effect {key}: {v}")
    return v


def validate(effects):
    """Validate effect preset syntax without audio buffers or sample-rate assumptions."""
    limits = {
        "gain": {"db": (0, -120, 60)},
        "fade": {"in_seconds": (0, 0, None), "out_seconds": (0, 0, None)},
        "lowpass": {"hz": (1000, 1, None), "resonance": (0, 0, 1)},
        "saturation": {"drive": (1, 0.001, 100)},
        "highpass": {"hz": (80, 1, None), "resonance": (0, 0, 1)},
        "normalize": {"peak_db": (-1, -60, 0)},
        "limiter": {"ceiling_db": (-1, -60, 0)},
        "chorus": {"rate_hz": (0.8, 0.01, 10), "depth_ms": (3, 0, 20), "mix": (0.4, 0, 1)},
        "delay": {
            "seconds": (0.25, 0.001, 30),
            "mix": (0.3, 0, 1),
            "feedback": (0.4, 0, 0.999),
            "repeats": (8, 1, 64),
        },
        "reverb": {"seconds": (1, 0.001, 30), "mix": (0.3, 0, 1), "decay": (0.5, 0, 0.999)},
    }
    if not isinstance(effects, list):
        raise ValueError("effects must be an array of objects")
    for e in effects:
        if not isinstance(e, dict):
            raise ValueError("each effect must be an object")
        kind = e.get("type", e.get("name"))
        if kind not in limits:
            raise ValueError(f"unknown effect: {kind}")
        unknown = set(e) - ({"type", "name"} | set(limits[kind]))
        if unknown:
            raise ValueError("Unknown effect properties: " + ", ".join(sorted(unknown)))
        for key, bounds in limits[kind].items():
            value = _number(e, key, *bounds)
            if key == "repeats" and value != int(value):
                raise ValueError("repeats must be an integer")
    return effects


def apply(data, sr, effects, tail="cut"):
    validate(effects)
    x = buffer(data).copy()
    sr = rate(sr)
    original = len(x)
    if tail not in ("cut", "full", "wrap"):
        raise ValueError("tail must be cut, full or wrap")
    if not isinstance(effects, list):
        raise ValueError("effects must be an array of objects")
    properties = {
        "gain": {"db"},
        "fade": {"in_seconds", "out_seconds"},
        "lowpass": {"hz", "resonance"},
        "saturation": {"drive"},
        "highpass": {"hz", "resonance"},
        "normalize": {"peak_db"},
        "limiter": {"ceiling_db"},
        "chorus": {"rate_hz", "depth_ms", "mix"},
        "delay": {"seconds", "mix", "feedback", "repeats"},
        "reverb": {"seconds", "mix", "decay"},
    }
    for e in effects:
        if not isinstance(e, dict):
            raise ValueError("each effect must be an object")
        kind = e.get("type", e.get("name"))
        unknown = set(e) - ({"type", "name"} | properties.get(kind, set()))
        if unknown:
            raise ValueError("Unknown effect properties: " + ", ".join(sorted(unknown)))
        if kind == "gain":
            x *= 10 ** (_number(e, "db", 0, -120, 60) / 20)
        elif kind == "fade":
            fi = min(len(x), round(_number(e, "in_seconds", 0, 0) * sr))
            fo = min(len(x), round(_number(e, "out_seconds", 0, 0) * sr))
            if fi:
                x[:fi] *= np.linspace(0, 1, fi)[:, None]
            if fo:
                x[-fo:] *= np.linspace(1, 0, fo)[:, None]
        elif kind in ("lowpass", "highpass"):
            hz = _number(e, "hz", 1000 if kind == "lowpass" else 80, 1, sr / 2 - 1)
            q = 0.5 + 9.5 * _number(e, "resonance", 0, 0, 1)
            w = 2 * np.pi * hz / sr
            c = np.cos(w)
            a = np.sin(w) / (2 * q)
            if kind == "lowpass":
                b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]) / (1 + a)
            else:
                b = np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2]) / (1 + a)
            aa = [1, -2 * c / (1 + a), (1 - a) / (1 + a)]
            x = lfilter(b, aa, x, axis=0)
        elif kind == "saturation":
            d = _number(e, "drive", 1, 0.001, 100)
            x = np.tanh(x * d) / np.tanh(d)
        elif kind == "normalize":
            peak = float(np.max(np.abs(x))) if len(x) else 0.0
            if peak > 0:
                x *= 10 ** (_number(e, "peak_db", -1, -60, 0) / 20) / peak
        elif kind == "limiter":
            ceiling = 10 ** (_number(e, "ceiling_db", -1, -60, 0) / 20)
            x = ceiling * np.tanh(x / ceiling)
        elif kind == "chorus":
            depth = _number(e, "depth_ms", 3, 0, 20) * sr / 1000
            lfo = np.sin(2 * np.pi * _number(e, "rate_hz", 0.8, 0.01, 10) * np.arange(len(x)) / sr)
            wet = _number(e, "mix", 0.4, 0, 1)
            position = np.arange(len(x)) - depth * (1 + lfo) - 1
            # A causal delay has zero history before the first input sample.
            grid = np.arange(-1, len(x))
            delayed = np.column_stack([
                np.interp(position, grid, np.concatenate(([0.0], channel)), left=0, right=0)
                for channel in x.T
            ])
            x = x * (1 - wet) + delayed * wet
        elif kind in ("delay", "reverb"):
            seconds = _number(e, "seconds", 0.25 if kind == "delay" else 1, 0.001, 30)
            wet = _number(e, "mix", 0.3, 0, 1)
            if kind == "delay":
                feedback = _number(e, "feedback", 0.4, 0, 0.999)
                repeats_value = _number(e, "repeats", 8, 1, 64)
                if repeats_value != int(repeats_value):
                    raise ValueError("repeats must be an integer")
                step = max(1, round(seconds * sr))
                repeats = int(repeats_value)
                taps = [(step * k, feedback ** (k - 1)) for k in range(1, repeats + 1)]
            else:
                decay = _number(e, "decay", 0.5, 0, 0.999)
                taps = [(max(1, round(seconds * sr * k / 12)), decay ** (k - 1) / 6) for k in range(1, 13)]
            y = np.zeros((len(x) + max(t[0] for t in taps), x.shape[1]))
            y[: len(x)] = x * (1 - wet)
            for offset, amplitude in taps:
                y[offset : offset + len(x)] += x * wet * amplitude
            x = y
        else:
            raise ValueError(f"unknown effect: {kind}")
        if not np.isfinite(x).all():
            raise ValueError("effect produced nonfinite samples")
    if tail == "cut":
        return x[:original]
    if tail == "wrap":
        y = np.zeros((original, x.shape[1]))
        if original:
            for start in range(0, len(x), original):
                y[: min(original, len(x) - start)] += x[start : start + original]
        return y
    return x
