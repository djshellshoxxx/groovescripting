"""Versioned event trace, provenance and run fingerprints for offline arrangements.

Tracing expands a project through the same code path as rendering and asks the synth scheduler to
record its decisions instead of synthesizing audio. It never renders, plays or modifies anything.
"""

import copy
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from . import __version__, synth
from .music import beat_frame
from .projects import expand, validate

TRACE_SCHEMA_VERSION = 1
DEFAULT_MAX_EVENTS = 100_000
UNAVAILABLE = ["automation_values", "oscillator_phase", "effect_processing"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(project, overrides=None):
    """Stable run identity from normalized project data, CLI overrides and engine version."""
    payload = dict(
        project=validate(copy.deepcopy(project)),
        overrides=overrides or {},
        engine=__version__,
        trace_schema=TRACE_SCHEMA_VERSION,
    )
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()[:16]


def _event_id(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:12]


def _pattern_source(project, step, track_index, name, voice):
    """JSON Pointer of the pattern data that produced a track's events in one section."""
    override = step["section"].get("tracks", {}).get(name, {})
    base = f"/sections/{step['section_index']}/tracks/{name}" if project.get("sections") else None
    if base and "pattern" in override:
        return base + "/pattern"
    if base and voice in override.get("params", {}).get("drum_patterns", {}):
        return base + "/params/drum_patterns/" + voice
    if base and any(k in override.get("params", {}) for k in ("pattern", "events")):
        key = "events" if "events" in override["params"] else "pattern"
        return base + "/params/" + key
    track = project["tracks"][track_index]
    if "pattern" in track:
        return f"/tracks/{track_index}/pattern"
    params = track.get("params", {})
    if voice in params.get("drum_patterns", {}):
        return f"/tracks/{track_index}/params/drum_patterns/{voice}"
    for key in ("events", "pattern"):
        if key in params:
            return f"/tracks/{track_index}/params/{key}"
    return f"/tracks/{track_index}"


def _origin(project, track, key, step):
    override = step["section"].get("tracks", {}).get(track["name"], {})
    if key in override.get("params", {}) or key in override:
        return "section"
    if key in track.get("params", {}) or key in track or key in project:
        return "project"
    if "preset" in track:
        return "preset"
    return "default"


def collect(project, seed=None, max_events=DEFAULT_MAX_EVENTS):
    """Return (header, records) for a project. Records are ordered by absolute frame then identity."""
    project = validate(copy.deepcopy(project))
    overrides = {}
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        project["seed"] = seed
        overrides["seed"] = seed
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 1:
        raise ValueError("max_events must be a positive integer")
    run = fingerprint(project, overrides)
    sr = project.get("sample_rate", 44100)
    bpm = project.get("bpm", 120)
    beats = project.get("beats", 4)
    records = []
    seeds = []
    for step in expand(project):
        section_start = beat_frame(step["cursor_beats"], bpm, sr)
        for item in step["tracks"]:
            t = item["track"]
            params = item["params"]
            seeds.append(
                dict(
                    section_index=step["section_index"],
                    repetition=step["repetition"],
                    track=t["name"],
                    seed=params["seed"],
                )
            )
            if item["silent"]:
                continue
            sink = []
            synth.render(t["instrument"], params, trace=sink)
            offset_beats = float(t.get("offset", 0))
            offset_frames = beat_frame(offset_beats, bpm, sr)
            for raw in sink:
                if len(records) >= max_events:
                    raise ValueError(f"trace exceeds --max-events {max_events}; raise the limit or narrow it")
                voice = raw["voice"]
                note_part = raw.get("arp_step", raw.get("chord_index", 0))
                identity = (
                    ("src", raw["source_index"])
                    if raw["source_index"] is not None
                    else ("gen", round(raw["beat"], 9))
                )
                event_id = _event_id(
                    t["name"], step["section_index"], step["repetition"], voice, *identity, note_part
                )
                absolute = step["cursor_beats"] + offset_beats + raw["source_beat"]
                frame = None if raw["frame"] is None else section_start + offset_frames + raw["frame"]
                decisions = []
                if raw["origin"] == "variation":
                    decisions.append(dict(kind="variation_insert", detail="ghost note or fill"))
                elif not math.isclose(raw["beat"], raw["source_beat"], abs_tol=1e-12):
                    decisions.append(dict(kind="variation_shift", beats=raw["beat"] - raw["source_beat"]))
                if raw["velocity_in"] != raw["velocity"]:
                    decisions.append(
                        dict(kind="velocity_humanize", before=raw["velocity_in"], after=raw["velocity"])
                    )
                decisions.append(
                    dict(
                        kind="probability",
                        roll=raw["roll"],
                        threshold=raw["probability"],
                        result="pass" if raw["reason"] != "probability" else "fail",
                    )
                )
                if raw.get("swing_beats"):
                    decisions.append(dict(kind="swing", beats=raw["swing_beats"]))
                if raw.get("humanize_frames"):
                    decisions.append(dict(kind="humanize", frames=raw["humanize_frames"]))
                if "requested_notes" in raw and raw["requested_notes"] != raw["notes"]:
                    decisions.append(
                        dict(kind="note_resolution", requested=raw["requested_notes"], resolved=raw["notes"])
                    )
                if "voice_stolen_at_frame" in raw:
                    decisions.append(
                        dict(
                            kind="voice_limit",
                            truncated_at_frame=section_start + offset_frames + raw["voice_stolen_at_frame"],
                        )
                    )
                if raw["reason"] == "outside_render_window":
                    decisions.append(dict(kind="window", result="dropped"))
                records.append(
                    dict(
                        event_id=event_id,
                        track=t["name"],
                        instrument=t["instrument"],
                        voice=voice,
                        source=dict(
                            pointer=_pattern_source(project, step, item["index"], t["name"], voice),
                            section=step["section"].get("name", f"section-{step['section_index'] + 1}"),
                            section_index=step["section_index"],
                            repetition=step["repetition"],
                            origin=raw["origin"],
                            source_index=raw["source_index"],
                        ),
                        bar=int(absolute // beats) + 1,
                        beat=round(absolute % beats + 1, 9),
                        timing=dict(
                            requested_beat=round(absolute, 9),
                            resolved_beat=None
                            if raw.get("resolved_beat") is None
                            else round(step["cursor_beats"] + offset_beats + raw["resolved_beat"], 9),
                            frame=frame,
                            sample_rate=sr,
                        ),
                        notes=raw["notes"],
                        duration=raw["duration"],
                        velocity=round(raw["velocity"], 9),
                        probability=raw["probability"],
                        accent=raw["accent"],
                        accepted=raw["accepted"],
                        decisions=decisions,
                        resolved_parameters={
                            key: dict(value=params.get(key, 0), origin=_origin(project, t, key, step))
                            for key in ("variation", "density", "humanize", "velocity_humanize")
                            if key in params
                        },
                    )
                )
    records.sort(
        key=lambda r: (
            r["timing"]["frame"] if r["timing"]["frame"] is not None else math.inf,
            r["timing"]["requested_beat"],
            r["track"],
            r["event_id"],
        )
    )
    for record in records:
        record["trace_schema_version"] = TRACE_SCHEMA_VERSION
        record["run_fingerprint"] = run
    header = dict(
        trace_schema_version=TRACE_SCHEMA_VERSION,
        kind="header",
        tool="groovescripting",
        engine_version=__version__,
        run_fingerprint=run,
        seed=project.get("seed", 0),
        overrides=overrides,
        sample_rate=sr,
        bpm=bpm,
        beats_per_bar=beats,
        event_count=len(records),
        derived_seeds=seeds,
        unavailable=UNAVAILABLE,
    )
    return header, records


def write_jsonl(path, header, records, overwrite=False):
    """Atomically write a JSON Lines trace; no partial file remains on failure."""
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"{destination} exists; use --overwrite")
    handle, temporary = tempfile.mkstemp(prefix=".trace-", dir=destination.parent or ".")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            for item in [header, *records]:
                out.write(canonical(item) + "\n")
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def read_jsonl(path):
    lines = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0].get("kind") != "header":
        raise ValueError("trace file must start with a header record")
    if lines[0].get("trace_schema_version") != TRACE_SCHEMA_VERSION:
        raise ValueError("unsupported trace schema version")
    return lines[0], lines[1:]
