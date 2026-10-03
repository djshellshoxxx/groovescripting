"""Pattern parser and drift-free musical sample clock."""

import math
import re
from decimal import ROUND_HALF_UP, Decimal


def beat_frame(beat, bpm=120, sample_rate=44100):
    return int(
        (Decimal(str(beat)) * Decimal(60) * Decimal(sample_rate) / Decimal(str(bpm))).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def note_value(value):
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number) or not 0 <= number <= 127:
            raise ValueError("MIDI note must be finite 0..127")
        return number
    value = str(value)
    if value.lower().endswith("hz"):
        hz = float(value[:-2])
        if not math.isfinite(hz) or hz <= 0:
            raise ValueError("Frequency must be positive")
        return {"hz": hz}
    match = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", value)
    if not match:
        number = float(value)
        if not 0 <= number <= 127:
            raise ValueError("MIDI note must be 0..127")
        return number
    letter, accidental, octave = match.groups()
    midi = (
        (int(octave) + 1) * 12
        + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter.upper()]
        + {"": 0, "#": 1, "b": -1}[accidental]
    )
    if not 0 <= midi <= 127:
        raise ValueError("Note outside MIDI range")
    return midi


def frequency(note):
    return float(note["hz"]) if isinstance(note, dict) else 440 * 2 ** ((float(note) - 69) / 12)


def parse_pattern(pattern, kind="note", subdivision=4):
    if subdivision <= 0:
        raise ValueError("subdivision must be positive")
    pattern = str(pattern).strip()
    tokens = (
        list(pattern)
        if kind == "drum" and re.fullmatch(r"[xX.\-]+", pattern)
        else re.split(r"[\s,]+", pattern)
        if pattern
        else []
    )
    events = []
    for index, token in enumerate(tokens):
        fields = token.split(":")
        if len(fields) > 4:
            raise ValueError("Pattern token has too many fields")
        if fields[0] == "~":
            if kind == "drum" or not events:
                raise ValueError("Tie requires a previous note")
            events[-1]["duration"] += 1 / subdivision
            continue
        if kind == "drum" and fields[0] not in ("x", "X", ".", "-", "_"):
            raise ValueError("Invalid drum token")
        if fields[0] in (".", "-", "_"):
            continue
        duration = float(fields[1]) if len(fields) > 1 and fields[1] else 1 / subdivision
        velocity = float(fields[2]) if len(fields) > 2 and fields[2] else 1
        probability = float(fields[3]) if len(fields) > 3 and fields[3] else 1
        if (
            not all(math.isfinite(v) for v in (duration, velocity, probability))
            or duration <= 0
            or not 0 <= velocity <= 1
            or not 0 <= probability <= 1
        ):
            raise ValueError("Invalid event duration, velocity or probability")
        accent = fields[0] == "X" or fields[0].endswith("!")
        notes = [] if kind == "drum" else [note_value(n) for n in fields[0].rstrip("!").split("+")]
        events.append(
            dict(
                beat=index / subdivision,
                duration=duration,
                notes=notes,
                velocity=velocity,
                probability=probability,
                accent=accent,
            )
        )
    return events
