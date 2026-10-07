"""Shared validation contracts for presets and project JSON."""

import math

DRUM_VOICES = ("kick", "snare", "closed_hat", "open_hat", "clap", "tom", "rim")

RANGES = {
    "bpm": (1, 1000, False),
    "bars": (1, 1024, True),
    "beats": (1, 32, True),
    "subdivision": (1, 64, True),
    "swing": (0, 0.49, False),
    "offset": (-128, 128, False),
    "seed": (0, 2**63 - 1, True),
    "sample_rate": (8000, 192000, True),
    "channels": (1, 2, True),
    "gain": (0, 4, False),
    "pan": (-1, 1, False),
    "transpose": (-96, 96, True),
    "humanize": (0, 0.1, False),
    "velocity_humanize": (0, 0.5, False),
    "attack": (0, 10, False),
    "decay": (0.001, 10, False),
    "sustain": (0, 1, False),
    "release": (0, 10, False),
    "cutoff": (10, 20000, False),
    "resonance": (0, 1, False),
    "saturation": (0, 10, False),
    "filter_attack": (0, 10, False),
    "filter_decay": (0.001, 10, False),
    "filter_sustain": (0, 1, False),
    "filter_release": (0, 10, False),
    "filter_amount": (-8, 8, False),
    "glide": (0, 5, False),
    "sub_mix": (0, 1, False),
    "detune": (-100, 100, False),
    "pulse_width": (0.05, 0.95, False),
    "lfo_rate": (0, 100, False),
    "lfo_depth": (0, 8, False),
    "unison_detune": (0, 100, False),
    "vibrato_rate": (0, 30, False),
    "vibrato_depth": (0, 200, False),
    "arp_rate": (0.01, 16, False),
    "voices": (1, 32, True),
    "unison": (1, 8, True),
    "pitch": (10, 20000, False),
    "pitch_envelope": (0, 24, False),
    "tone_noise": (0, 1, False),
    "variation": (0, 1, False),
    "density": (0, 1, False),
    "ghost_notes": (0, 1, False),
    "fill_every": (0, 128, True),
}

COMMON = {
    "bpm",
    "bars",
    "beats",
    "subdivision",
    "swing",
    "offset",
    "seed",
    "sample_rate",
    "channels",
    "gain",
    "pan",
    "humanize",
    "velocity_humanize",
    "variation",
    "density",
}

NOTE_COMMON = COMMON | {"transpose", "scale", "root"}
SOUND_COMMON = {
    "waveform",
    "attack",
    "decay",
    "sustain",
    "release",
    "cutoff",
    "resonance",
    "filter_attack",
    "filter_decay",
    "filter_sustain",
    "filter_release",
    "filter_amount",
    "glide",
    "sub_mix",
    "detune",
    "pulse_width",
    "saturation",
    "lfo_rate",
    "lfo_depth",
    "vibrato_rate",
    "vibrato_depth",
    "legato",
}
DRUM_ALLOWED = COMMON | {
    "pattern",
    "events",
    "drum_patterns",
    "drum_params",
    "voice",
    "pitch",
    "pitch_envelope",
    "tone_noise",
    "attack",
    "decay",
    "cutoff",
    "resonance",
    "saturation",
    "ghost_notes",
    "fill_every",
}
BASS_ALLOWED = NOTE_COMMON | SOUND_COMMON | {"pattern", "events"}
LEAD_ALLOWED = (
    NOTE_COMMON
    | SOUND_COMMON
    | {"pattern", "events", "voices", "unison", "unison_detune", "arp", "arp_rate", "mode"}
)
ALLOWED = {"drum": DRUM_ALLOWED, "bass": BASS_ALLOWED, "lead": LEAD_ALLOWED}

CHOICES = {
    "waveform": {"sine", "triangle", "saw", "pulse", "square"},
    "scale": {"none", "major", "minor", "pentatonic", "chromatic"},
    "arp": {"off", "up", "down", "random"},
    "mode": {"mono", "poly"},
    "voice": set(DRUM_VOICES),
}

DRUM_PARAM_RANGES = {
    "pitch": RANGES["pitch"],
    "pitch_envelope": RANGES["pitch_envelope"],
    "tone_noise": RANGES["tone_noise"],
    "attack": RANGES["attack"],
    "decay": RANGES["decay"],
    "cutoff": RANGES["cutoff"],
    "resonance": RANGES["resonance"],
    "saturation": RANGES["saturation"],
    "gain": (0, None, False),
    "pan": RANGES["pan"],
}


def _number(name, value, low, high, integer):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if integer and int(value) != value:
        raise ValueError(f"{name} must be an integer")
    if low is not None and value < low or high is not None and value > high:
        upper = "infinity" if high is None else high
        raise ValueError(f"{name} must be within [{low}, {upper}]")


def validate_common_values(values):
    """Validate any shared CLI-backed values present in a mapping."""
    if not isinstance(values, dict):
        raise ValueError("values must be an object")
    for name, bounds in RANGES.items():
        if name in values:
            _number(name, values[name], *bounds)
    if "channels" in values and values["channels"] not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    for name, choices in CHOICES.items():
        if name in values and values[name] not in choices:
            raise ValueError(f"invalid {name}: expected one of {sorted(choices)}")
    if "legato" in values and not isinstance(values["legato"], bool):
        raise ValueError("legato must be boolean")
    if "pattern" in values and not isinstance(values["pattern"], str):
        raise ValueError("pattern must be a string")
    if "events" in values and not isinstance(values["events"], list):
        raise ValueError("events must be an array")
    return values


def _validate_drum_maps(params):
    if "drum_patterns" in params:
        patterns = params["drum_patterns"]
        if not isinstance(patterns, dict):
            raise ValueError("drum_patterns must be an object")
        unknown = set(patterns) - set(DRUM_VOICES)
        if unknown:
            raise ValueError("unknown drum pattern voices: " + ", ".join(sorted(unknown)))
        if any(not isinstance(pattern, str) for pattern in patterns.values()):
            raise ValueError("drum patterns must be strings")
    if "drum_params" in params:
        drum_params = params["drum_params"]
        if not isinstance(drum_params, dict):
            raise ValueError("drum_params must be an object")
        unknown = set(drum_params) - set(DRUM_VOICES)
        if unknown:
            raise ValueError("unknown drum parameter voices: " + ", ".join(sorted(unknown)))
        for voice, values in drum_params.items():
            if not isinstance(values, dict):
                raise ValueError(f"drum_params.{voice} must be an object")
            unknown_keys = set(values) - set(DRUM_PARAM_RANGES)
            if unknown_keys:
                raise ValueError("unknown drum parameters: " + ", ".join(sorted(unknown_keys)))
            for name, value in values.items():
                _number(f"drum_params.{voice}.{name}", value, *DRUM_PARAM_RANGES[name])


def validate_instrument_params(instrument, params):
    """Validate persisted preset/project parameters against the public CLI contract."""
    if instrument not in ALLOWED:
        raise ValueError("instrument must be drum, bass or lead")
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    unknown = set(params) - ALLOWED[instrument]
    if unknown:
        raise ValueError(f"parameters not supported by {instrument}: " + ", ".join(sorted(unknown)))
    validate_common_values(params)
    if instrument == "drum":
        _validate_drum_maps(params)
    return params
