"""Versioned JSON arrangements and deterministic aligned stems."""

import copy
import json
from pathlib import Path

import numpy as np

from . import automation
from .audio import buffer, mix, rate
from .music import beat_frame
from .validation import validate_common_values, validate_instrument_params


def validate(project):
    if not isinstance(project, dict) or project.get("version") != 1:
        raise ValueError("project version must be 1")
    unknown = set(project) - {
        "version",
        "bpm",
        "beats",
        "bars",
        "subdivision",
        "swing",
        "sample_rate",
        "channels",
        "seed",
        "tracks",
        "sections",
        "humanize",
        "velocity_humanize",
    }
    if unknown:
        raise ValueError("unknown project keys: " + ", ".join(sorted(unknown)))
    validate_common_values(project)
    rate(project.get("sample_rate", 44100))
    for k, default in [("bpm", 120), ("beats", 4), ("bars", 1), ("subdivision", 4)]:
        v = project.get(k, default)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0:
            raise ValueError(f"{k} must be positive")
        if k != "bpm" and int(v) != v:
            raise ValueError(f"{k} must be integer")
    if project.get("channels", 2) not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    seed = project.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    tracks = project.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("project requires tracks")
    names = set()
    for t in tracks:
        if not isinstance(t, dict):
            raise ValueError("track must be an object")
        unknown = set(t) - {
            "name",
            "instrument",
            "preset",
            "params",
            "pattern",
            "gain",
            "pan",
            "mute",
            "solo",
            "offset",
            "trim",
            "automation",
        }
        if unknown:
            raise ValueError("unknown track keys: " + ", ".join(sorted(unknown)))
        for k in ("mute", "solo"):
            if not isinstance(t.get(k, False), bool):
                raise ValueError(f"{k} must be boolean")
        name = t.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("track names must be unique nonempty strings")
        names.add(name)
        if t.get("instrument") not in ("drum", "bass", "lead"):
            raise ValueError("unknown instrument")
        if not isinstance(t.get("params", {}), dict):
            raise ValueError("params must be an object")
        validate_instrument_params(t["instrument"], t.get("params", {}))
        automation.validate(t.get("automation", []))
        for k, default in [("gain", 1), ("pan", 0), ("offset", 0), ("trim", None)]:
            value = t.get(k, default)
            if value is not None and (not isinstance(value, (int, float)) or not np.isfinite(value)):
                raise ValueError(f"{k} must be finite")
        if not -1 <= t.get("pan", 0) <= 1 or (t.get("trim") is not None and t["trim"] < 0):
            raise ValueError("invalid pan or trim")
    sections = project.get("sections", [])
    if not isinstance(sections, list):
        raise ValueError("sections must be a list")
    for s in sections:
        if not isinstance(s, dict):
            raise ValueError("section must be an object")
        unknown = set(s) - {"name", "bars", "repeat", "tracks", "variation"}
        if unknown:
            raise ValueError("unknown section keys: " + ", ".join(sorted(unknown)))
        for k in ("bars", "repeat"):
            v = s.get(k, project.get("bars", 1) if k == "bars" else 1)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise ValueError(f"section {k} must be a positive integer")
        overrides = s.get("tracks", {})
        if not isinstance(overrides, dict) or set(overrides) - names:
            raise ValueError("section tracks must reference existing track names")
        for name, v in overrides.items():
            if not isinstance(v, dict):
                raise ValueError("track override must be an object")
            if set(v) - {
                "preset",
                "params",
                "pattern",
                "gain",
                "pan",
                "mute",
                "solo",
                "offset",
                "trim",
                "automation",
            }:
                raise ValueError("unknown or immutable track override keys")
            original = next(t for t in tracks if t["name"] == name)
            merged = dict(original, **{k: value for k, value in v.items() if k != "params"})
            if not isinstance(v.get("params", {}), dict):
                raise ValueError("override params must be an object")
            merged["params"] = dict(original.get("params", {}), **v.get("params", {}))
            validate(dict(project, tracks=[merged], sections=[]))
        if not isinstance(s.get("variation", 0), int) or s.get("variation", 0) < 0:
            raise ValueError("variation must be nonnegative integer")
    return project


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save(path, project, overwrite=False):
    validate(project)
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(str(p))
    p.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


def render_project(project, render_fn, tail="cut", automation_fn=None):
    validate(project)
    automation_fn = automation.apply if automation_fn is None else automation_fn
    if tail not in ("cut", "full", "wrap"):
        raise ValueError("tail must be cut, full or wrap")
    sr = rate(project.get("sample_rate", 44100))
    channels = project.get("channels", 2)
    bpm = project.get("bpm", 120)
    beats = project.get("beats", 4)
    sections = project.get("sections") or [dict(bars=project.get("bars", 1))]
    chunks = []
    stem_chunks = {t["name"]: [] for t in project["tracks"]}
    sequence = 0
    section_count = sum(s.get("repeat", 1) for s in sections)
    cursor_beats = 0
    for section in sections:
        for repetition in range(section.get("repeat", 1)):
            bars = section.get("bars", project.get("bars", 1))
            selected = []
            for original in project["tracks"]:
                t = copy.deepcopy(original)
                overrides = section.get("tracks", {}).get(t["name"], {})
                t["params"].update(overrides.get("params", {})) if "params" in t else t.update(
                    params=copy.deepcopy(overrides.get("params", {}))
                )
                t.update({k: v for k, v in overrides.items() if k != "params"})
                selected.append(t)
            check = dict(project, tracks=selected, sections=[])
            validate(check)
            solo = any(t.get("solo", False) and not t.get("mute", False) for t in selected)
            rendered = {}
            target = beat_frame(cursor_beats + bars * beats, bpm, sr) - beat_frame(cursor_beats, bpm, sr)
            for index, t in enumerate(selected):
                if t.get("mute", False) or (solo and not t.get("solo", False)):
                    rendered[t["name"]] = np.zeros((0, channels))
                    continue
                params = dict(t.get("params", {}))
                if "preset" in t:
                    from .presets import resolve

                    params = resolve(t["instrument"], t["preset"], params)
                params.update(
                    bpm=bpm,
                    bars=bars,
                    beats=beats,
                    subdivision=project.get("subdivision", 4),
                    swing=project.get("swing", 0),
                    humanize=project.get("humanize", params.get("humanize", 0)),
                    velocity_humanize=project.get("velocity_humanize", params.get("velocity_humanize", 0)),
                    sample_rate=sr,
                    channels=channels,
                    seed=project.get("seed", 0)
                    + sequence * 1009
                    + index * 9176
                    + section.get("variation", 0),
                )
                if "pattern" in t:
                    params["pattern"] = t["pattern"]
                if tail in ("full", "wrap"):
                    params["tail"] = max(
                        float(params.get("release", 0.12)),
                        float(params.get("decay", 0.4)) * 8 if t["instrument"] == "drum" else 0,
                    )
                else:
                    params["tail"] = 0
                result = render_fn(t["instrument"], params)
                data, source = result if isinstance(result, tuple) else (result, sr)
                data = buffer(data)
                lanes = t.get("automation", [])
                if lanes:
                    data, _ = mix([dict(data=data, sample_rate=source)], sr, channels)
                    source = sr
                    data = automation_fn(data, sr, bpm, lanes, cursor_beats + float(t.get("offset", 0)))
                track = dict(
                    data=data,
                    sample_rate=source,
                    gain=t.get("gain", 1),
                    pan=t.get("pan", 0),
                    offset_seconds=beat_frame(t.get("offset", 0), bpm, sr) / sr,
                )
                if t.get("trim") is not None:
                    track["trim_seconds"] = beat_frame(t["trim"], bpm, sr) / sr
                stem, _ = mix([track], sr, channels)
                if tail == "wrap":
                    folded = np.zeros((target, channels))
                    for start in range(0, len(stem), target):
                        part = stem[start : start + target]
                        folded[: len(part)] += part
                    stem = folded
                rendered[t["name"]] = (
                    stem if tail == "full" and sequence == section_count - 1 else stem[:target]
                )
            if tail == "full" and sequence == section_count - 1:
                target = max([target] + [len(stem) for stem in rendered.values()])
            chunk = np.zeros((target, channels))
            for name in stem_chunks:
                stem = rendered[name]
                padded = np.zeros_like(chunk)
                padded[: len(stem)] = stem
                stem_chunks[name].append(padded)
                chunk += padded
            chunks.append(chunk)
            sequence += 1
            cursor_beats += bars * beats
    return np.concatenate(chunks), sr, {name: np.concatenate(values) for name, values in stem_chunks.items()}


validate_project = validate
