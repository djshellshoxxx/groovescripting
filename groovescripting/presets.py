"""Versioned, validated presets shared by instruments and projects."""

import json
from pathlib import Path

from .validation import ALLOWED, validate_instrument_params

DEFAULTS = dict(
    bpm=120,
    bars=1,
    beats=4,
    subdivision=4,
    swing=0.0,
    offset=0.0,
    seed=0,
    sample_rate=44100,
    channels=2,
    gain=0.7,
    pan=0.0,
    transpose=0,
    scale="none",
    root="C4",
    humanize=0.0,
    velocity_humanize=0.0,
)
SOUND_DEFAULTS = dict(
    waveform="saw",
    attack=0.005,
    decay=0.12,
    sustain=0.65,
    release=0.12,
    cutoff=3000.0,
    resonance=0.0,
    filter_attack=0.005,
    filter_decay=0.12,
    filter_sustain=0.65,
    filter_release=0.12,
    filter_amount=0.0,
    glide=0.0,
    legato=False,
    sub_mix=0.0,
    detune=0.0,
    pulse_width=0.5,
    saturation=0.0,
    lfo_rate=0.0,
    lfo_depth=0.0,
    voices=8,
    unison=1,
    unison_detune=12.0,
    vibrato_rate=5.0,
    vibrato_depth=0.0,
    arp="off",
    arp_rate=0.25,
)
BUILTINS = {
    "drum": {
        "electronic": dict(
            drum_patterns={
                "kick": "x...x...x...x...",
                "snare": "....x.......x...",
                "closed_hat": "x.x.x.x.x.x.x.x.",
            }
        ),
        "dance": dict(
            drum_patterns={
                "kick": "X...X...X...X...",
                "clap": "....x.......x...",
                "open_hat": "..x...x...x...x.",
            },
            saturation=0.3,
        ),
        "breakbeat": dict(
            drum_patterns={
                "kick": "X.....x...x.....",
                "snare": "....X.......X...",
                "closed_hat": "x.xXx.x.x.xXx.x.",
            },
            swing=0.15,
        ),
        "experimental": dict(
            drum_patterns={"tom": "X..x....x..X....", "rim": "..x..x...x..x...", "clap": ".......x.......x"},
            seed=12,
            pitch=240,
        ),
    },
    "bass": {
        "sub": dict(waveform="sine", cutoff=500.0, sub_mix=0.25, pattern="C2 . C2 . G1 . C2 ."),
        "plucked": dict(
            waveform="triangle", decay=0.08, sustain=0.15, cutoff=1600.0, pattern="C2 . Eb2 G2 . Bb1 C2 ."
        ),
        "acid": dict(
            waveform="saw",
            resonance=0.65,
            filter_amount=2.0,
            sustain=0.3,
            glide=0.06,
            legato=True,
            pattern="C2:0.5:1 ~ G2! . Bb1 . C2 .",
        ),
        "aggressive": dict(
            waveform="pulse",
            pulse_width=0.3,
            saturation=2.0,
            sub_mix=0.35,
            cutoff=1500.0,
            pattern="C2 C2 . Eb2 G1 . Bb1 C2",
        ),
    },
    "lead": {
        "pluck": dict(
            waveform="triangle", decay=0.08, sustain=0.1, release=0.1, pattern="C4 . E4 . G4 . B4 ."
        ),
        "sustained": dict(
            waveform="saw",
            attack=0.06,
            sustain=0.75,
            release=0.3,
            unison=3,
            vibrato_depth=8.0,
            pattern="C4:1 . . . E4:1 . . .",
        ),
        "soft_chord": dict(
            waveform="sine", attack=0.04, release=0.3, pattern="C4+E4+G4:1 . . . F4+A4+C5:1 . . ."
        ),
        "experimental": dict(
            waveform="pulse",
            pulse_width=0.2,
            resonance=0.5,
            lfo_rate=3.0,
            lfo_depth=1.5,
            arp="random",
            seed=31,
            pattern="C4+Eb4+G4+Bb4:1 . . .",
        ),
    },
}
EXTRA = {
    "pattern",
    "events",
    "drum_patterns",
    "drum_params",
    "voice",
    "pitch",
    "pitch_envelope",
    "tone_noise",
    "tail",
    "mode",
}


def names(instrument):
    return sorted(BUILTINS[instrument])


def load(instrument, value):
    if value in BUILTINS[instrument]:
        params = BUILTINS[instrument][value]
        validate_instrument_params(instrument, params)
        return {"version": 1, "instrument": instrument, "name": value, "params": params}
    data = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("instrument") != instrument:
        raise ValueError("Preset requires version 1 and matching instrument")
    if not isinstance(data.get("params"), dict):
        raise ValueError("Preset params must be an object")
    validate_instrument_params(instrument, data["params"])
    return data


def resolve(instrument, preset=None, params=None):
    result = {key: value for key, value in DEFAULTS.items() if key in ALLOWED[instrument]}
    if instrument != "drum":
        result.update({key: value for key, value in SOUND_DEFAULTS.items() if key in ALLOWED[instrument]})
    if preset:
        result.update(load(instrument, preset)["params"])
    result.update(params or {})
    return result


def save(path, instrument, params, overwrite=False):
    validate_instrument_params(instrument, params)
    path = Path(path)
    data = {"version": 1, "instrument": instrument, "name": path.stem, "params": params}
    with path.open("w" if overwrite else "x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
