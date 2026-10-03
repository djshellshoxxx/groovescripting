"""Validated audio buffers, encoding, resampling and aligned mixing."""

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def buffer(data):
    x = np.asarray(data, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not np.isfinite(x).all():
        raise ValueError("audio must be finite mono or stereo samples")
    return x


def rate(sr):
    if isinstance(sr, bool) or int(sr) != sr or not 8000 <= sr <= 384000:
        raise ValueError("sample_rate must be an integer from 8000 to 384000")
    return int(sr)


def read(path):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    return buffer(x), rate(sr)


def write(path, data, sr, overwrite=False, format="wav", subtype="PCM_16"):
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {p}")
    fmt = format.upper()
    if fmt not in ("WAV", "FLAC") or not sf.check_format(fmt, subtype):
        raise ValueError("unsupported output format/subtype")
    sf.write(str(p), buffer(data), rate(sr), format=fmt, subtype=subtype)


def info(path):
    x, sr = read(path)
    meta = sf.info(path)
    return dict(
        path=str(path),
        sample_rate=sr,
        frames=len(x),
        channels=x.shape[1],
        duration=len(x) / sr,
        peak=np.max(np.abs(x), axis=0).tolist() if len(x) else [0.0] * x.shape[1],
        rms=np.sqrt(np.mean(x * x, axis=0)).tolist() if len(x) else [0.0] * x.shape[1],
        clipping=int(np.count_nonzero(np.abs(x) >= 1)),
        format=meta.format,
        subtype=meta.subtype,
    )


def resample(data, source_rate, target_rate):
    x = buffer(data)
    source_rate = rate(source_rate)
    target_rate = rate(target_rate)
    if source_rate == target_rate or not len(x):
        return x.copy()
    g = gcd(source_rate, target_rate)
    return resample_poly(x, target_rate // g, source_rate // g, axis=0)


def mix(tracks, sample_rate, channels, normalize=False, limit=False):
    sr = rate(sample_rate)
    if channels not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    active = [t for t in tracks if not t.get("mute", False)]
    if any(t.get("solo", False) for t in active):
        active = [t for t in active if t.get("solo", False)]
    prepared = []
    for t in active:
        if "data" in t:
            x = buffer(t["data"])
            source = t.get("sample_rate", sr)
        else:
            x, source = read(t["path"])
        x = resample(x, source, sr)
        trim = t.get("trim_seconds")
        if trim is not None:
            if not np.isfinite(trim) or trim < 0:
                raise ValueError("trim_seconds must be finite and nonnegative")
            x = x[: round(trim * sr)]
        pan = float(t.get("pan", 0))
        gain = float(t.get("gain", 1))
        offset_seconds = float(t.get("offset_seconds", 0))
        if not np.isfinite([pan, gain, offset_seconds]).all() or not -1 <= pan <= 1:
            raise ValueError("gain/offset must be finite; pan must be within [-1,1]")
        if channels == 1:
            x = x.mean(axis=1, keepdims=True)
        elif x.shape[1] == 1:
            angle = (pan + 1) * np.pi / 4
            x = x * np.array([np.cos(angle), np.sin(angle)])
        else:
            x = x * np.array([min(1.0, 1 - pan), min(1.0, 1 + pan)])
        offset = round(offset_seconds * sr)
        if offset < 0:
            x = x[-offset:]
            offset = 0
        prepared.append((offset, x * gain))
    n = max((offset + len(x) for offset, x in prepared), default=0)
    out = np.zeros((n, channels))
    for offset, x in prepared:
        out[offset : offset + len(x)] += x
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if normalize and peak:
        out /= peak
    if limit:
        out = np.clip(out, -1, 1)
    return out, dict(
        frames=n,
        active_tracks=len(active),
        peak_before=peak,
        peak_after=float(np.max(np.abs(out))) if out.size else 0.0,
    )
