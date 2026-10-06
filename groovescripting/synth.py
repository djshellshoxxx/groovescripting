"""Deterministic offline procedural drum and oscillator synthesis."""

import logging
import re

import numpy as np
from scipy.signal import lfilter

from . import presets
from .music import beat_frame, frequency, note_value, parse_pattern
from . import variation as event_variation

DRUMS = ("kick", "snare", "closed_hat", "open_hat", "clap", "tom", "rim")


def envelope(n, sr, gate, o, prefix="", legato=False):
    a = max(0, float(o.get(prefix + "attack", 0.005)))
    d = max(0, float(o.get(prefix + "decay", 0.12)))
    s = float(np.clip(o.get(prefix + "sustain", 0.65), 0, 1))
    r = max(0, float(o.get(prefix + "release", 0.12)))
    t = np.arange(n) / sr
    if legato:
        a = 0
    e = np.ones(n) if a == 0 else np.minimum(t / a, 1)
    after = t >= a
    e[after] = s + (1 - s) * np.maximum(0, 1 - (t[after] - a) / max(d, 1 / sr))
    g = min(max(0, gate), n)
    if g < n:
        level = e[max(0, g - 1)]
        e[g:] = level * np.maximum(0, 1 - (t[g:] - g / sr) / max(r, 1 / sr))
    return e


def oscillator(freq, sr, waveform="saw", pulse_width=0.5):
    freq = np.asarray(freq, dtype=float)
    phase = np.cumsum(freq) / sr
    if waveform == "sine":
        return np.sin(2 * np.pi * phase)
    if waveform not in ("saw", "triangle", "pulse", "square"):
        raise ValueError("Unknown waveform")
    count = min(64, max(1, int((sr * 0.49) / max(np.max(freq), 1))))
    signal = np.zeros(len(freq))
    for k in range(1, count + 1):
        if waveform == "triangle":
            if k % 2:
                signal += ((-1) ** ((k - 1) // 2)) * np.sin(2 * np.pi * k * phase) / k**2 * 8 / np.pi**2
        elif waveform == "saw":
            signal += -2 / np.pi * np.sin(2 * np.pi * k * phase) / k
        else:
            signal += (
                4
                / np.pi
                * np.sin(np.pi * k * pulse_width)
                * np.cos(2 * np.pi * k * (phase - pulse_width / 2))
                / k
            )
    return signal


def lowpass(signal, sr, cutoff, resonance=0):
    result = np.empty_like(signal)
    state = np.zeros(2)
    q = 0.707 + float(np.clip(resonance, 0, 1)) * 9
    cuts = np.broadcast_to(np.asarray(cutoff), signal.shape)
    for start in range(0, len(signal), 64):
        end = min(start + 64, len(signal))
        f = float(np.clip(cuts[start], 10, sr * 0.45))
        w = 2 * np.pi * f / sr
        co = np.cos(w)
        alpha = np.sin(w) / (2 * q)
        den = 1 + alpha
        b = np.array([(1 - co) / 2, 1 - co, (1 - co) / 2]) / den
        a = np.array([1, -2 * co / den, (1 - alpha) / den])
        result[start:end], state = lfilter(b, a, signal[start:end], zi=state)
    return result


def _events(o, kind):
    events = o.get("events")
    if events is None:
        events = parse_pattern(
            o.get("pattern", "x...x...x...x..." if kind == "drum" else "C2 . . . C2 . G2 ."),
            kind,
            int(o.get("subdivision", 4)),
        )
    if o.get("events") is not None:
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        for e in events:
            if not isinstance(e, dict) or "beat" not in e:
                raise ValueError("Event must contain beat")
            unknown = set(e) - {"beat", "duration", "notes", "velocity", "probability", "accent"}
            if unknown:
                raise ValueError("Unknown event fields: " + ", ".join(sorted(unknown)))
            for key, default in (
                ("beat", 0),
                ("duration", 1 / int(o.get("subdivision", 4))),
                ("velocity", 1),
                ("probability", 1),
            ):
                value = float(e.get(key, default))
                if (
                    not np.isfinite(value)
                    or (key == "duration" and value <= 0)
                    or (key in ("probability", "velocity") and not 0 <= value <= 1)
                ):
                    raise ValueError("Invalid event " + key)
            if kind == "note":
                if not isinstance(e.get("notes"), list) or not e["notes"]:
                    raise ValueError("Event notes must be a nonempty list")
                for note in e["notes"]:
                    if isinstance(note, dict):
                        if (
                            set(note) != {"hz"}
                            or not np.isfinite(float(note["hz"]))
                            or float(note["hz"]) <= 0
                        ):
                            raise ValueError("Invalid frequency note")
                    else:
                        note_value(note)
                    parsed = note if isinstance(note, dict) else note_value(note)
                    if frequency(parsed) >= int(o.get("sample_rate", 44100)) / 2:
                        raise ValueError("Event frequency must be below Nyquist")
        return [dict(e) for e in events]
    pattern = str(o.get("pattern", "x...x...x...x..." if kind == "drum" else "C2 . . . C2 . G2 ."))
    tokens = (
        len(pattern)
        if kind == "drum" and re.fullmatch(r"[xX.\-]+", pattern)
        else len(re.split(r"[\s,]+", pattern.strip()))
    )
    period = tokens / int(o.get("subdivision", 4))
    total = float(o.get("beats", 4)) * float(o.get("bars", 1))
    return (
        [
            dict(e, beat=e["beat"] + base)
            for base in np.arange(0, total, period)
            for e in events
            if e["beat"] + base < total
        ]
        if period
        else []
    )


def render(instrument, options=None):
    o = dict(options or {})
    unknown = set(o) - (
        set(presets.DEFAULTS) | set(presets.SOUND_DEFAULTS) | presets.EXTRA | {"mode", "note"}
    )
    if unknown:
        raise ValueError("Unknown engine options: " + ", ".join(sorted(unknown)))
    for key, value in o.items():
        if isinstance(value, (float, int)) and not np.isfinite(value):
            raise ValueError("Nonfinite option " + key)
    for key in (
        "attack",
        "decay",
        "release",
        "filter_attack",
        "filter_decay",
        "filter_release",
        "glide",
        "gain",
        "saturation",
        "lfo_rate",
        "vibrato_rate",
        "vibrato_depth",
    ):
        if key in o and float(o[key]) < 0:
            raise ValueError(key + " must be nonnegative")
    for key in ("sustain", "filter_sustain", "resonance", "sub_mix"):
        if key in o and not 0 <= float(o[key]) <= 1:
            raise ValueError(key + " must be 0..1")
    if "pulse_width" in o and not 0.05 <= float(o["pulse_width"]) <= 0.95:
        raise ValueError("pulse_width must be .05..95")
    if "cutoff" in o and float(o["cutoff"]) <= 0:
        raise ValueError("cutoff must be positive")
    drum_params = o.get("drum_params", {})
    if not isinstance(drum_params, dict):
        raise ValueError("drum_params must be a mapping")
    allowed_drums = {
        "pitch",
        "pitch_envelope",
        "tone_noise",
        "attack",
        "decay",
        "cutoff",
        "resonance",
        "saturation",
        "gain",
        "pan",
    }
    for voice, params in drum_params.items():
        if voice not in DRUMS:
            raise ValueError("Unknown drum parameter voice " + str(voice))
        if not isinstance(params, dict):
            raise ValueError("Per-drum params must be a mapping")
        unknown = set(params) - allowed_drums
        if unknown:
            raise ValueError("Unknown drum parameters: " + ", ".join(sorted(unknown)))
        for key, value in params.items():
            try:
                number = float(value)
            except (ValueError, TypeError) as exc:
                raise ValueError("Drum parameter must be numeric: " + key) from exc
            if not np.isfinite(number):
                raise ValueError("Nonfinite drum parameter " + key)
            if key == "pan" and not -1 <= number <= 1:
                raise ValueError("Drum pan must be -1..1")
            if key in ("tone_noise", "resonance") and not 0 <= number <= 1:
                raise ValueError("Drum " + key + " must be 0..1")
            if key in ("pitch", "cutoff", "decay") and number <= 0:
                raise ValueError("Drum " + key + " must be positive")
            if key != "pan" and number < 0:
                raise ValueError("Drum " + key + " must be nonnegative")
    logging.getLogger(__name__).debug("Render %s options=%s", instrument, o)
    sr = int(o.get("sample_rate", 44100))
    bpm = float(o.get("bpm", 120))
    beats = float(o.get("beats", 4)) * float(o.get("bars", 1))
    channels = int(o.get("channels", 2))
    if sr < 1000 or bpm <= 0 or beats <= 0 or channels not in (1, 2):
        raise ValueError("Invalid render clock or channels")
    tail = float(o.get("tail", 0))
    if tail < 0:
        raise ValueError("tail must be nonnegative")
    n = beat_frame(beats, bpm, sr) + int(np.floor(tail * sr + 0.5))
    if n <= 0 or n > 10_000_000:
        raise ValueError("Render must contain 1..10,000,000 frames; split longer work into chunks")
    output = np.zeros(n)
    drum_stereo = np.zeros((n, 2))
    rng = np.random.default_rng(int(o.get("seed", 0)))
    subdivision = int(o.get("subdivision", 4))
    swing = float(o.get("swing", 0))
    offset = float(o.get("offset", 0))
    if not 0 <= swing <= 1 or subdivision <= 0:
        raise ValueError("Invalid swing or subdivision")

    def start_of(e):
        if (
            not 0 <= float(e.get("probability", 1)) <= 1
            or not 0 <= float(e.get("velocity", 1)) <= 1
            or float(e.get("duration", 1 / subdivision)) <= 0
        ):
            raise ValueError("Invalid event controls")
        humanize = float(o.get("humanize", 0))
        if humanize < 0:
            raise ValueError("humanize must be nonnegative seconds")
        beat = float(e["beat"])
        index = int(np.floor(beat * subdivision + 0.5))
        return max(
            0,
            beat_frame(beat + offset + (swing / (2 * subdivision) if index % 2 else 0), bpm, sr)
            + int(rng.uniform(-humanize, humanize) * sr),
        )

    if instrument == "drum":
        patterns = o.get("drum_patterns", {o.get("voice", "kick"): o.get("pattern", "x...x...x...x...")})
        jobs = []
        for voice, pattern in patterns.items():
            if voice not in DRUMS:
                raise ValueError("Unknown drum voice " + voice)
            events = _events(dict(o, pattern=pattern), "drum")
            events = event_variation.mutate(
                events,
                "drum",
                total_beats=beats,
                subdivision=subdivision,
                seed=int(o.get("seed", 0)) + DRUMS.index(voice) * 7919,
                variation=o.get("variation", 0),
                density=o.get("density", 1),
                ghost_notes=o.get("ghost_notes", 0),
                fill_every=o.get("fill_every", 0),
                beats_per_bar=o.get("beats", 4),
            )
            for e in events:
                jitter = float(o.get("velocity_humanize", 0))
                if not 0 <= jitter <= 1:
                    raise ValueError("velocity_humanize must be 0..1")
                e["velocity"] = float(np.clip(e.get("velocity", 1) + rng.uniform(-jitter, jitter), 0, 1))
                if rng.random() < float(e.get("probability", 1)):
                    jobs.append((start_of(e), voice, e))
        closed = sorted(start for start, voice, e in jobs if voice == "closed_hat")
        for start, voice, e in sorted(jobs, key=lambda j: j[0]):
            if not 0 <= start < n:
                continue
            p = dict(o)
            p.update(o.get("drum_params", {}).get(voice, {}))
            decay = max(
                0.001,
                float(
                    p.get(
                        "decay",
                        {
                            "kick": 0.35,
                            "snare": 0.2,
                            "closed_hat": 0.06,
                            "open_hat": 0.4,
                            "clap": 0.18,
                            "tom": 0.3,
                            "rim": 0.04,
                        }[voice],
                    )
                ),
            )
            length = min(n - start, int(sr * decay * 8))
            if voice == "open_hat":
                choke = next((c for c in closed if c > start), n)
                length = min(length, choke - start)
            t = np.arange(length) / sr
            env = np.exp(-t / decay)
            noise = rng.normal(0, 0.3, length)
            pitch = float(
                p.get("pitch", {"kick": 50, "tom": 140, "snare": 180, "rim": 1700}.get(voice, 8000))
            )
            if voice in ("kick", "tom"):
                freq = pitch * (1 + float(p.get("pitch_envelope", 3)) * np.exp(-t / 0.025))
                sound = np.sin(2 * np.pi * np.cumsum(freq) / sr) + noise * np.exp(-t / 0.004) * 0.15
            elif voice in ("closed_hat", "open_hat"):
                sound = noise - lowpass(noise, sr, np.full(length, min(6000, sr * 0.3)))
            elif voice == "rim":
                sound = np.sin(2 * np.pi * pitch * t) + 0.4 * np.sin(2 * np.pi * pitch * 1.47 * t)
            elif voice == "clap":
                burst = sum(np.exp(-np.maximum(t - d, 0) / 0.006) * (t >= d) for d in (0, 0.012, 0.024))
                sound = noise * (burst + 0.5)
            else:
                sound = noise + np.sin(2 * np.pi * pitch * t) * 0.3
            noise_mix = float(p.get("tone_noise", 0))
            if not 0 <= noise_mix <= 1:
                raise ValueError("tone_noise must be 0..1")
            sound = (1 - noise_mix) * sound + noise_mix * noise
            if "cutoff" in p:
                sound = lowpass(sound, sr, np.full(length, float(p["cutoff"])), p.get("resonance", 0))
            drive = max(0, float(p.get("saturation", 0)))
            if drive:
                sound = np.tanh(sound * (1 + drive)) / np.tanh(1 + drive)
            attack = max(0, float(p.get("attack", 0)))
            if attack:
                env *= np.minimum(t / attack, 1)
            fade = min(length, int(sr * 0.003))
            if fade:
                env[-fade:] *= np.linspace(1, 0, fade)
            hit = (
                sound
                * env
                * float(e.get("velocity", 1))
                * float(o.get("drum_params", {}).get(voice, {}).get("gain", 1))
                * (1.2 if e.get("accent") else 1)
            )
            output[start : start + length] += hit
            voice_pan = float(o.get("drum_params", {}).get(voice, {}).get("pan", 0))
            if not -1 <= voice_pan <= 1:
                raise ValueError("Drum pan must be -1..1")
            drum_stereo[start : start + length, 0] += hit * min(1, 1 - voice_pan)
            drum_stereo[start : start + length, 1] += hit * min(1, 1 + voice_pan)
    elif instrument in ("bass", "lead"):
        events = _events(o, "note")
        events = event_variation.mutate(
            events,
            "note",
            total_beats=beats,
            subdivision=subdivision,
            seed=int(o.get("seed", 0)),
            variation=o.get("variation", 0),
            density=o.get("density", 1),
        )
        jobs = []
        for e in events:
            jitter = float(o.get("velocity_humanize", 0))
            if not 0 <= jitter <= 1:
                raise ValueError("velocity_humanize must be 0..1")
            e["velocity"] = float(np.clip(e.get("velocity", 1) + rng.uniform(-jitter, jitter), 0, 1))
            if rng.random() >= float(e.get("probability", 1)):
                continue
            notes = e.get("notes") or [o.get("note", "C2" if instrument == "bass" else "C4")]
            notes = [note_value(note) if not isinstance(note, dict) else note for note in notes]
            if any(not np.isfinite(frequency(note)) or not 0 < frequency(note) < sr / 2 for note in notes):
                raise ValueError("Notes must be finite and below Nyquist")
            scale = o.get("scale", "chromatic")
            scale = "chromatic" if scale == "none" else scale
            scales = {
                "chromatic": list(range(12)),
                "major": [0, 2, 4, 5, 7, 9, 11],
                "minor": [0, 2, 3, 5, 7, 8, 10],
                "pentatonic": [0, 2, 4, 7, 9],
            }
            if scale not in scales:
                raise ValueError("Unknown scale")
            root = o.get("root", 0)
            if isinstance(root, str):
                root = note_value(root if re.search(r"\d", root) else root + "4")
            root = int(root) % 12
            if scale != "chromatic":
                allowed = [m for m in range(128) if (m - root) % 12 in scales[scale]]
                notes = [
                    min(allowed, key=lambda m: abs(m - note)) if not isinstance(note, dict) else note
                    for note in notes
                ]
            arp = o.get("arp", "off") if instrument == "lead" else "off"
            if arp != "off":
                if arp not in ("up", "down", "random"):
                    raise ValueError("Unknown arpeggio")
                notes = sorted(notes, key=frequency, reverse=arp == "down")
                rate = float(o.get("arp_rate", 0.25))
                if rate <= 0:
                    raise ValueError("arp_rate must be positive")
                for j, beat in enumerate(np.arange(0, float(e.get("duration", 1 / subdivision)), rate)):
                    copy = dict(
                        e, beat=float(e["beat"]) + beat, duration=min(rate, float(e["duration"]) - beat)
                    )
                    note = notes[int(rng.integers(len(notes)))] if arp == "random" else notes[j % len(notes)]
                    jobs.append((start_of(copy), note, copy))
            else:
                for note in notes[:1] if instrument == "bass" else notes:
                    jobs.append((start_of(e), note, e))
        jobs.sort(key=lambda j: j[0])
        active = []
        previous = None
        previous_end = -1
        mode = o.get("mode", "poly")
        if mode not in ("mono", "poly"):
            raise ValueError("mode must be mono or poly")
        voices = 1 if instrument == "bass" or mode == "mono" else int(o.get("voices", 16))
        if not 1 <= voices <= 128:
            raise ValueError("voices must be 1..128")
        scheduled = []
        for start, note, e in jobs:
            if not 0 <= start < n:
                continue
            gate = max(1, beat_frame(float(e.get("duration", 1 / subdivision)), bpm, sr))
            length = min(n - start, gate + int(max(0, float(o.get("release", 0.12))) * sr))
            active = [i for i in active if scheduled[i]["end"] > start]
            if len(active) >= voices:
                old = active.pop(0)
                scheduled[old]["end"] = start
            scheduled.append(dict(start=start, end=start + length, gate=gate, note=note, event=e))
            active.append(len(scheduled) - 1)
        for job in scheduled:
            start = job["start"]
            length = job["end"] - start
            if length <= 0:
                continue
            e = job["event"]
            target = frequency(job["note"]) * 2 ** (float(o.get("transpose", 0)) / 12)
            t = np.arange(length) / sr
            freq = np.full(length, target)
            glide = max(0, float(o.get("glide", 0)))
            legato = bool(o.get("legato", False)) and start < previous_end
            if voices == 1 and previous is not None and glide:
                frac = np.minimum(t / glide, 1)
                freq = previous * (target / previous) ** frac
            freq *= 2 ** (float(o.get("detune", 0)) / 1200)
            freq *= 2 ** (
                float(o.get("vibrato_depth", 0))
                * np.sin(2 * np.pi * float(o.get("vibrato_rate", 5)) * t)
                / 1200
            )
            if (
                not np.isfinite(freq).all()
                or np.max(freq) * 2 ** (abs(float(o.get("unison_detune", 8))) / 1200) >= sr / 2
            ):
                raise ValueError("Oscillator frequency including modulation must remain below Nyquist")
            unison = 1 if instrument == "bass" else int(o.get("unison", 1))
            if not 1 <= unison <= 16:
                raise ValueError("unison must be 1..16")
            sound = np.zeros(length)
            for cents in (
                np.linspace(-float(o.get("unison_detune", 8)), float(o.get("unison_detune", 8)), unison)
                if unison > 1
                else [0]
            ):
                sound += (
                    oscillator(
                        freq * 2 ** (cents / 1200),
                        sr,
                        o.get("waveform", "saw"),
                        float(np.clip(o.get("pulse_width", 0.5), 0.05, 0.95)),
                    )
                    / unison
                )
            sub = float(np.clip(o.get("sub_mix", 0), 0, 1))
            sound = (1 - sub) * sound + sub * oscillator(freq / 2, sr, "sine")
            fe = envelope(length, sr, job["gate"], o, "filter_")
            cutoff = float(o.get("cutoff", 3000)) * 2 ** (
                fe * float(o.get("filter_amount", 0))
                + float(o.get("lfo_depth", 0)) * np.sin(2 * np.pi * float(o.get("lfo_rate", 1)) * t)
            )
            sound = lowpass(sound, sr, cutoff, o.get("resonance", 0))
            drive = max(0, float(o.get("saturation", 0)))
            if drive:
                sound = np.tanh(sound * (1 + drive)) / np.tanh(1 + drive)
            sound *= (
                envelope(length, sr, job["gate"], o, legato=legato)
                * float(e.get("velocity", 1))
                * (1.2 if e.get("accent") else 1)
            )
            fade = min(length, int(sr * 0.003))
            if fade:
                sound[:fade] *= np.linspace(0, 1, fade)
                sound[-fade:] *= np.linspace(1, 0, fade)
            output[start : job["end"]] += sound
            previous = target
            previous_end = start + job["gate"]
    else:
        raise ValueError("instrument must be drum, bass or lead")
    if not np.isfinite(output).all() or not np.isfinite(drum_stereo).all():
        raise RuntimeError("Synthesis produced nonfinite audio")
    output = output * float(o.get("gain", 0.7))
    logging.getLogger(__name__).debug("Rendered frames=%d peak=%.6f", n, float(np.max(abs(output))))
    result = (
        drum_stereo * float(o.get("gain", 0.7))
        if instrument == "drum" and channels == 2
        else np.repeat(output[:, None], channels, axis=1)
    )
    pan = float(o.get("pan", 0))
    if not -1 <= pan <= 1:
        raise ValueError("pan must be -1..1")
    if channels == 2:
        result[:, 0] *= min(1, 1 - pan)
        result[:, 1] *= min(1, 1 + pan)
    return result
