"""Standard MIDI File import/export for GrooveScripting projects."""

import argparse
import copy
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import mido

from . import __version__, diagnostics, presets
from .music import note_value
from .projects import load as load_project
from .projects import save as save_project
from .projects import validate as validate_project
from .synth import _events
from .variation import mutate

DRUM_NOTES = {
    "kick": 36,
    "snare": 38,
    "closed_hat": 42,
    "open_hat": 46,
    "clap": 39,
    "tom": 45,
    "rim": 37,
}


def _finite_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _beats_per_bar(numerator, denominator):
    value = numerator * 4 / denominator
    if not value.is_integer() or not 1 <= value <= 32:
        raise ValueError("MIDI time signature does not map to an integer quarter-note beat count")
    return int(value)


def import_file(path, instrument="lead", subdivision=4, quantize=True):
    """Import melodic note tracks from a Standard MIDI File into a version-1 project."""

    if instrument not in ("bass", "lead"):
        raise ValueError("MIDI import instrument must be bass or lead")
    if isinstance(subdivision, bool) or not isinstance(subdivision, int) or not 1 <= subdivision <= 64:
        raise ValueError("subdivision must be an integer within [1, 64]")

    source = mido.MidiFile(path)
    ticks_per_beat = source.ticks_per_beat
    tempos = []
    signatures = []
    tracks = []
    percussion_notes = 0
    max_end = 0.0

    for track_index, track in enumerate(source.tracks):
        absolute = 0
        name = getattr(track, "name", "") or f"MIDI Track {track_index + 1}"
        active = defaultdict(deque)
        notes = []
        track_end = 0
        for message in track:
            absolute += message.time
            track_end = absolute
            if message.is_meta:
                if message.type == "set_tempo":
                    tempos.append(message.tempo)
                elif message.type == "time_signature":
                    signatures.append((message.numerator, message.denominator))
                elif message.type == "track_name" and message.name:
                    name = message.name
                continue
            if message.type not in ("note_on", "note_off"):
                continue
            is_on = message.type == "note_on" and message.velocity > 0
            if message.channel == 9:
                if is_on:
                    percussion_notes += 1
                continue
            key = (message.channel, message.note)
            if is_on:
                active[key].append((absolute, message.velocity))
            elif active[key]:
                start, velocity = active[key].popleft()
                notes.append((start, max(start + 1, absolute), message.note, velocity))

        for (channel, note), queue in active.items():
            del channel
            while queue:
                start, velocity = queue.popleft()
                notes.append((start, max(start + 1, track_end), note, velocity))

        if not notes:
            continue

        step = 1 / subdivision

        def q(value):
            if not quantize:
                return value
            return round(value * subdivision) / subdivision

        grouped = defaultdict(list)
        for start_tick, end_tick, note, velocity in notes:
            start = q(start_tick / ticks_per_beat)
            duration = q((end_tick - start_tick) / ticks_per_beat)
            if quantize:
                duration = max(step, duration)
            else:
                duration = max(1 / ticks_per_beat, duration)
            key = (start, duration, velocity)
            grouped[key].append(note)
            max_end = max(max_end, start + duration)

        events = []
        for (start, duration, velocity), chord in sorted(grouped.items()):
            events.append(
                {
                    "beat": float(start),
                    "duration": float(duration),
                    "notes": sorted(chord),
                    "velocity": float(velocity / 127),
                    "probability": 1,
                }
            )
        tracks.append(
            {
                "name": name,
                "instrument": instrument,
                "params": {"events": events},
            }
        )

    unique_tempos = sorted(set(tempos))
    if len(unique_tempos) > 1:
        raise ValueError("MIDI contains multiple tempo values; project version 1 supports one tempo")
    tempo = unique_tempos[0] if unique_tempos else 500000
    bpm = float(mido.tempo2bpm(tempo))

    unique_signatures = []
    for signature in signatures:
        if signature not in unique_signatures:
            unique_signatures.append(signature)
    if len(unique_signatures) > 1:
        raise ValueError("MIDI contains multiple time signatures; project version 1 supports one")
    beats = _beats_per_bar(*unique_signatures[0]) if unique_signatures else 4

    if not tracks:
        if percussion_notes:
            raise ValueError("percussion-only MIDI import is not supported yet")
        raise ValueError("MIDI file contains no melodic note events")

    project = {
        "version": 1,
        "bpm": bpm,
        "beats": beats,
        "bars": max(1, int(math.ceil(max_end / beats))),
        "subdivision": subdivision,
        "tracks": tracks,
    }
    validate_project(project)
    return project


def _resolved_track(original, overrides, project, sequence, index, bars):
    track = copy.deepcopy(original)
    if "params" not in track:
        track["params"] = {}
    if "params" in overrides:
        track["params"].update(overrides["params"])
    track.update({key: value for key, value in overrides.items() if key != "params"})
    params = dict(track.get("params", {}))
    if "preset" in track:
        params = presets.resolve(track["instrument"], track["preset"], params)
    params.update(
        bpm=project.get("bpm", 120),
        bars=bars,
        beats=project.get("beats", 4),
        subdivision=project.get("subdivision", 4),
        seed=project.get("seed", 0) + sequence * 1009 + index * 9176,
    )
    if "pattern" in track:
        params["pattern"] = track["pattern"]
    return track, params


def _note_events(params, total_beats):
    events = _events(params, "note")
    return mutate(
        events,
        "note",
        total_beats=total_beats,
        subdivision=params.get("subdivision", 4),
        seed=params.get("seed", 0),
        variation=params.get("variation", 0),
        density=params.get("density", 1),
    )


def _drum_events(params, total_beats):
    patterns = params.get(
        "drum_patterns",
        {params.get("voice", "kick"): params.get("pattern", "x...x...x...x...")},
    )
    result = []
    for voice, pattern in patterns.items():
        if voice not in DRUM_NOTES:
            raise ValueError("unknown drum voice for MIDI export: " + str(voice))
        events = _events(dict(params, pattern=pattern), "drum")
        events = mutate(
            events,
            "drum",
            total_beats=total_beats,
            subdivision=params.get("subdivision", 4),
            seed=params.get("seed", 0) + list(DRUM_NOTES).index(voice) * 7919,
            variation=params.get("variation", 0),
            density=params.get("density", 1),
            ghost_notes=params.get("ghost_notes", 0),
            fill_every=params.get("fill_every", 0),
            beats_per_bar=params.get("beats", 4),
        )
        result.extend((voice, event) for event in events)
    return result


def _midi_note(value, transpose=0):
    parsed = note_value(value)
    if isinstance(parsed, dict):
        raise ValueError("arbitrary Hz notes cannot be exported to MIDI without pitch bend")
    note = int(round(float(parsed) + float(transpose)))
    if not 0 <= note <= 127:
        raise ValueError("transposed MIDI note is outside 0..127")
    return note


def export_file(project, path, overwrite=False, ticks_per_beat=480):
    """Export a validated project to a type-1 Standard MIDI File."""

    validate_project(project)
    if isinstance(ticks_per_beat, bool) or not isinstance(ticks_per_beat, int) or ticks_per_beat < 24:
        raise ValueError("ticks_per_beat must be an integer >= 24")
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(str(destination))

    bpm = _finite_number("bpm", project.get("bpm", 120))
    beats_per_bar = int(project.get("beats", 4))
    midi_file = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    meta = mido.MidiTrack()
    midi_file.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=beats_per_bar, denominator=4, time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))

    messages = {track["name"]: [] for track in project["tracks"]}
    sections = project.get("sections") or [{"bars": project.get("bars", 1)}]
    cursor = 0.0
    sequence = 0

    for section in sections:
        for _ in range(section.get("repeat", 1)):
            bars = section.get("bars", project.get("bars", 1))
            total_beats = bars * beats_per_bar
            selected = []
            for original in project["tracks"]:
                overrides = section.get("tracks", {}).get(original["name"], {})
                selected.append(_resolved_track(original, overrides, project, sequence, len(selected), bars))
            solo = any(track.get("solo", False) and not track.get("mute", False) for track, _ in selected)

            for track_index, (track, params) in enumerate(selected):
                if track.get("mute", False) or (solo and not track.get("solo", False)):
                    continue
                offset = float(track.get("offset", 0))
                trim = track.get("trim")
                channel = track_index % 15
                if channel >= 9:
                    channel += 1

                if track["instrument"] == "drum":
                    for voice, event in _drum_events(params, total_beats):
                        if float(event.get("probability", 1)) == 0:
                            continue
                        start = float(event["beat"])
                        duration = float(event.get("duration", 1 / params.get("subdivision", 4)))
                        if trim is not None:
                            if start >= trim:
                                continue
                            duration = min(duration, max(0, float(trim) - start))
                        start += offset
                        end = start + duration
                        if end <= 0 or start >= total_beats:
                            continue
                        start = max(0.0, start)
                        end = min(total_beats, max(start, end))
                        velocity = max(1, min(127, int(round(float(event.get("velocity", 1)) * 127))))
                        note = DRUM_NOTES[voice]
                        start_tick = int(round((cursor + start) * ticks_per_beat))
                        end_tick = max(start_tick + 1, int(round((cursor + end) * ticks_per_beat)))
                        messages[track["name"]].append(
                            (start_tick, 1, mido.Message("note_on", note=note, velocity=velocity, channel=9))
                        )
                        messages[track["name"]].append(
                            (end_tick, 0, mido.Message("note_off", note=note, velocity=0, channel=9))
                        )
                else:
                    transpose = float(params.get("transpose", 0))
                    for event in _note_events(params, total_beats):
                        if float(event.get("probability", 1)) == 0:
                            continue
                        start = float(event["beat"])
                        duration = float(event.get("duration", 1 / params.get("subdivision", 4)))
                        if trim is not None:
                            if start >= trim:
                                continue
                            duration = min(duration, max(0, float(trim) - start))
                        start += offset
                        end = start + duration
                        if end <= 0 or start >= total_beats:
                            continue
                        start = max(0.0, start)
                        end = min(total_beats, max(start, end))
                        velocity = max(1, min(127, int(round(float(event.get("velocity", 1)) * 127))))
                        for source_note in event.get("notes", []):
                            note = _midi_note(source_note, transpose)
                            start_tick = int(round((cursor + start) * ticks_per_beat))
                            end_tick = max(start_tick + 1, int(round((cursor + end) * ticks_per_beat)))
                            messages[track["name"]].append(
                                (
                                    start_tick,
                                    1,
                                    mido.Message("note_on", note=note, velocity=velocity, channel=channel),
                                )
                            )
                            messages[track["name"]].append(
                                (
                                    end_tick,
                                    0,
                                    mido.Message("note_off", note=note, velocity=0, channel=channel),
                                )
                            )
            cursor += total_beats
            sequence += 1

    for track in project["tracks"]:
        midi_track = mido.MidiTrack()
        midi_file.tracks.append(midi_track)
        midi_track.append(mido.MetaMessage("track_name", name=track["name"], time=0))
        last_tick = 0
        for tick, order, message in sorted(messages[track["name"]], key=lambda item: (item[0], item[1])):
            del order
            message.time = max(0, tick - last_tick)
            midi_track.append(message)
            last_tick = tick
        midi_track.append(mido.MetaMessage("end_of_track", time=0))

    midi_file.save(destination)
    return destination


def parser():
    p = argparse.ArgumentParser(prog="groovmidi", description="GrooveScripting MIDI file interchange")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--log-file", metavar="PATH", help="append troubleshooting logs to a UTF-8 file")
    p.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info")
    p.add_argument("--log-format", choices=["text", "json"], default="text")
    sub = p.add_subparsers(dest="action", required=True)

    imp = sub.add_parser("import", help="convert MIDI to a GrooveScripting project")
    imp.add_argument("input")
    imp.add_argument("--output", "-o", required=True)
    imp.add_argument("--instrument", choices=["bass", "lead"], default="lead")
    imp.add_argument("--subdivision", type=int, default=4)
    imp.add_argument("--no-quantize", action="store_true")
    imp.add_argument("--overwrite", action="store_true")

    exp = sub.add_parser("export", help="convert a GrooveScripting project to MIDI")
    exp.add_argument("input")
    exp.add_argument("--output", "-o", required=True)
    exp.add_argument("--overwrite", action="store_true")
    return p


def cli(argv=None):
    args = parser().parse_args(argv)
    logger = handler = None
    try:
        if not args.log_file and (args.log_level != "info" or args.log_format != "text"):
            raise ValueError("--log-level and --log-format require --log-file")
        logger, handler = diagnostics.configure(args.log_file, args.log_level, args.log_format)
        logger.info("Starting groovmidi %s", args.action)
        if args.action == "import":
            project = import_file(
                args.input,
                instrument=args.instrument,
                subdivision=args.subdivision,
                quantize=not args.no_quantize,
            )
            save_project(args.output, project, overwrite=args.overwrite)
        else:
            project = load_project(args.input)
            export_file(project, args.output, overwrite=args.overwrite)
        logger.info("Completed groovmidi %s", args.action)
        return 0
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        if logger:
            logger.exception("Invalid input: %s", error)
        print(f"groovmidi: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ImportError) as error:
        if logger:
            logger.exception("Operation failed: %s", error)
        print(f"groovmidi: {error}", file=sys.stderr)
        return 1
    finally:
        if logger and handler:
            diagnostics.close(logger, handler)


def main():
    return cli()


if __name__ == "__main__":
    raise SystemExit(main())
