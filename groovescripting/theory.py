"""Music theory helpers: scales, modes, chord symbols, Euclidean rhythms and progressions.

Pure functions with no audio or file IO. Chord symbols in note patterns use ``ROOT[quality]@octave``
(for example ``Cm7@3``) so they never collide with plain note names such as ``Bb4``.
"""

import argparse
import re
import sys

from . import __version__

SCALES = {
    "chromatic": list(range(12)),
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}

CHORDS = {
    "": [0, 4, 7],
    "m": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "5": [0, 7],
    "6": [0, 4, 7, 9],
    "m6": [0, 3, 7, 9],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "m7": [0, 3, 7, 10],
    "m7b5": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "9": [0, 4, 7, 10, 14],
    "maj9": [0, 4, 7, 11, 14],
    "m9": [0, 3, 7, 10, 14],
    "add9": [0, 4, 7, 14],
}

_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_ROMAN = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}
_CHORD_RE = re.compile(r"([A-Ga-g][#b]?)([^@]*)@(-?\d+)(?:/(\d+))?")


def pitch_class(name):
    """Pitch class 0..11 for a note name like ``C``, ``F#`` or ``Bb``."""
    match = re.fullmatch(r"([A-Ga-g])([#b]?)", str(name))
    if not match:
        raise ValueError(f"Invalid note name: {name}")
    letter, accidental = match.groups()
    return (_LETTERS[letter.upper()] + {"": 0, "#": 1, "b": -1}[accidental]) % 12


def note_name(midi):
    midi = int(midi)
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def scale_pitch_classes(root, scale):
    if scale not in SCALES:
        raise ValueError(f"Unknown scale: {scale}")
    base = root if isinstance(root, int) else pitch_class(root)
    return [(base + step) % 12 for step in SCALES[scale]]


def scale_notes(root, scale, octave=4):
    """Ascending note names for one octave of a scale, including the octave note."""
    base = (octave + 1) * 12 + (root if isinstance(root, int) else pitch_class(root))
    return [note_name(base + step) for step in SCALES[scale] + [12]]


def chord_midi(symbol, octave=3, inversion=0):
    """MIDI numbers for a chord like ``Cm7``; ``inversion`` rotates lowest notes up an octave."""
    match = re.fullmatch(r"([A-Ga-g][#b]?)(.*)", symbol)
    if not match or match.group(2) not in CHORDS:
        raise ValueError(f"Unknown chord: {symbol}")
    root = (octave + 1) * 12 + pitch_class(match.group(1))
    notes = [root + step for step in CHORDS[match.group(2)]]
    for _ in range(inversion % len(notes)):
        notes.append(notes.pop(0) + 12)
    if not all(0 <= n <= 127 for n in notes):
        raise ValueError("Chord outside MIDI range")
    return notes


def expand_chord_token(token):
    """Expand ``Cm7@3`` or ``Cm7@3/1`` (inversion) to ``C3+Eb3...``; other tokens return None."""
    match = _CHORD_RE.fullmatch(token.rstrip("!"))
    if not match:
        return None
    root, quality, octave, inversion = match.groups()
    notes = chord_midi(root + quality, int(octave), int(inversion or 0))
    return "+".join(note_name(n) for n in notes) + ("!" if token.endswith("!") else "")


def euclid(pulses, steps, rotation=0):
    """Bjorklund-style Euclidean rhythm as a list of booleans."""
    if steps < 1 or not 0 <= pulses <= steps:
        raise ValueError("Euclidean rhythm needs 0 <= pulses <= steps and steps >= 1")
    pattern = [(i * pulses) % steps < pulses for i in range(steps)]
    rotation %= steps
    return pattern[-rotation:] + pattern[:-rotation] if rotation else pattern


def euclid_string(pulses, steps, rotation=0):
    return "".join("x" if hit else "." for hit in euclid(pulses, steps, rotation))


def expand_euclid(pattern):
    """Expand ``euclid(5,8[,rot])`` to a drum string; other patterns return None."""
    match = re.fullmatch(r"\s*euclid\(\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(-?\d+)\s*)?\)\s*", str(pattern))
    return euclid_string(int(match[1]), int(match[2]), int(match[3] or 0)) if match else None


def progression(key, numerals, scale="major", octave=3):
    """Chord pattern for roman numerals (``i iv V``): lowercase = minor, uppercase = major."""
    tonic = pitch_class(key)
    out = []
    for numeral in numerals:
        match = re.fullmatch(r"([b#]?)([ivIV]+)(7|maj7|dim|sus4|sus2)?", numeral)
        if not match or match.group(2).upper() not in _ROMAN:
            raise ValueError(f"Invalid roman numeral: {numeral}")
        accidental, roman, extra = match.groups()
        degree = _ROMAN[roman.upper()]
        root = (tonic + degree + {"": 0, "#": 1, "b": -1}[accidental]) % 12
        quality = ("m" if roman.islower() else "") + (extra or "")
        quality = {"mdim": "dim", "m7": "m7", "7": "7"}.get(quality, quality)
        out.append(f"{_NAMES[root]}{quality}@{octave}")
    return out


def parser():
    p = argparse.ArgumentParser(prog="groovtheory", description="GrooveScripting music theory helper")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scale", help="list scale notes")
    s.add_argument("root")
    s.add_argument("scale", choices=sorted(SCALES))
    s.add_argument("--octave", type=int, default=4)
    c = sub.add_parser("chord", help="expand chord symbols to note patterns")
    c.add_argument("symbols", nargs="+")
    c.add_argument("--octave", type=int, default=3)
    e = sub.add_parser("euclid", help="Euclidean rhythm drum string")
    e.add_argument("pulses", type=int)
    e.add_argument("steps", type=int)
    e.add_argument("--rotate", type=int, default=0)
    g = sub.add_parser("progression", help="chord pattern from roman numerals")
    g.add_argument("key")
    g.add_argument("numerals", nargs="+")
    g.add_argument("--octave", type=int, default=3)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "scale":
            print(" ".join(scale_notes(args.root, args.scale, args.octave)))
        elif args.command == "chord":
            print(" ".join("+".join(note_name(n) for n in chord_midi(s, args.octave)) for s in args.symbols))
        elif args.command == "euclid":
            print(euclid_string(args.pulses, args.steps, args.rotate))
        else:
            chords = progression(args.key, args.numerals, octave=args.octave)
            print(" ".join(expand_chord_token(c) for c in chords))
    except ValueError as error:
        print(f"groovtheory: {error}", file=sys.stderr)
        return 2
    return 0


cli = main


if __name__ == "__main__":
    raise SystemExit(main())
