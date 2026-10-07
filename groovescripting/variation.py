"""Deterministic event mutation for musical variation."""

import copy
import math

import numpy as np


def _unit(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be within [0, 1]")
    return value


def _fill_every(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("fill_every must be an integer within [0, 128]")
    if int(value) != value or not 0 <= value <= 128:
        raise ValueError("fill_every must be an integer within [0, 128]")
    return int(value)


def mutate(
    events,
    kind,
    *,
    total_beats,
    subdivision,
    seed,
    variation=0,
    density=1,
    ghost_notes=0,
    fill_every=0,
    beats_per_bar=4,
):
    """Return a seeded mutated copy of expanded events.

    kind is "drum" or "note". Tonal mutation deliberately leaves pitch data untouched.
    """

    variation = _unit("variation", variation)
    density = _unit("density", density)
    ghost_notes = _unit("ghost_notes", ghost_notes)
    fill_every = _fill_every(fill_every)
    if kind not in ("drum", "note"):
        raise ValueError("kind must be drum or note")
    if kind != "drum" and (ghost_notes or fill_every):
        raise ValueError("ghost_notes and fill_every are drum-only controls")
    if (
        isinstance(subdivision, bool)
        or int(subdivision) != subdivision
        or subdivision <= 0
        or not math.isfinite(float(subdivision))
    ):
        raise ValueError("subdivision must be a positive integer")
    if (
        not isinstance(total_beats, (int, float))
        or isinstance(total_beats, bool)
        or not math.isfinite(total_beats)
        or total_beats < 0
    ):
        raise ValueError("total_beats must be finite and nonnegative")
    if (
        not isinstance(beats_per_bar, (int, float))
        or isinstance(beats_per_bar, bool)
        or not math.isfinite(beats_per_bar)
        or beats_per_bar <= 0
    ):
        raise ValueError("beats_per_bar must be positive")

    rng = np.random.default_rng(int(seed))
    source = copy.deepcopy(list(events))
    if variation == 0 and density == 1 and ghost_notes == 0 and fill_every == 0:
        return source

    step = 1 / int(subdivision)
    out = []
    for event in source:
        if rng.random() > density:
            continue
        item = copy.deepcopy(event)
        if variation:
            velocity = float(item.get("velocity", 1))
            velocity += rng.uniform(-0.25 * variation, 0.25 * variation)
            item["velocity"] = float(np.clip(velocity, 0, 1))
            jitter = rng.uniform(-0.25 * step * variation, 0.25 * step * variation)
            upper = max(0.0, float(total_beats) - np.finfo(float).eps)
            item["beat"] = float(np.clip(float(item["beat"]) + jitter, 0, upper))
        out.append(item)

    if kind == "drum" and total_beats > 0:
        occupied = {
            int(round(float(event["beat"]) * subdivision))
            for event in out
            if 0 <= float(event["beat"]) < total_beats
        }
        slots = int(math.ceil(float(total_beats) * subdivision))
        for index in range(slots):
            beat = index * step
            if beat >= total_beats or index in occupied:
                continue
            add = rng.random() < ghost_notes
            if not add and fill_every:
                bar_index = int(beat // beats_per_bar)
                in_final_beat = beat >= (bar_index + 1) * beats_per_bar - 1
                target_bar = (bar_index + 1) % fill_every == 0
                fill_probability = variation if variation else 0.35
                add = target_bar and in_final_beat and rng.random() < fill_probability
            if add:
                out.append(
                    {
                        "beat": float(beat),
                        "duration": float(step),
                        "notes": [],
                        "velocity": float(rng.uniform(0.15, 0.45)),
                        "probability": 1,
                    }
                )
                occupied.add(index)

    out.sort(key=lambda event: float(event["beat"]))
    return out
