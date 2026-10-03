"""Generate a searchable static command reference from the actual argument parsers."""

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from groovescripting import presets  # noqa: E402
from groovescripting.cli import TOOLS, parser  # noqa: E402

DESCRIPTIONS = {
    "input": "Input audio file (or project/preset JSON for groovinfo).",
    "inputs": "Input audio files, in track order.",
    "project": "Version 1 JSON project path.",
    "output": "Output file. Defaults to TOOL.wav.",
    "format": "Export container; inferred from output extension when omitted.",
    "subtype": "Export sample representation. FLOAT requires WAV.",
    "sample_rate": "Render rate in Hz; helpers preserve input/project rate unless overridden.",
    "channels": "Channel count; helpers preserve input/project layout unless overridden.",
    "bpm": "Tempo in beats per minute.",
    "bars": "Render length in whole bars.",
    "beats": "Beats per bar.",
    "subdivision": "Pattern steps per beat.",
    "swing": "Delay alternating steps by a fraction of a step.",
    "offset": "Shift events in beats.",
    "seed": "Random seed for reproducible synthesis.",
    "gain": "Linear output amplitude multiplier.",
    "pan": "Stereo balance: -1 left, 0 center, 1 right.",
    "pattern": "Space-separated note tokens or compact drum hit/rest pattern.",
    "events": "JSON file containing explicit beat-timed events.",
    "transpose": "Pitch shift in semitones.",
    "humanize": "Random timing variation in seconds.",
    "velocity_humanize": "Random velocity variation.",
    "scale": "Quantize notes to selected scale.",
    "root": "Scale root as a note name.",
    "preset": "Built-in preset name or version 1 JSON preset file.",
    "save_preset": "Write current preset; replacement requires --overwrite.",
    "list_presets": "List built-in presets without rendering.",
    "inspect_preset": "Print resolved preset settings without rendering.",
    "attack": "Amplitude envelope attack in seconds.",
    "decay": "Envelope decay in seconds; drums use a per-voice default.",
    "sustain": "Envelope sustain level.",
    "release": "Envelope release in seconds.",
    "cutoff": "Lowpass cutoff frequency in Hz.",
    "resonance": "Filter resonance amount.",
    "saturation": "Nonlinear saturation drive.",
    "voice": "Default drum voice.",
    "pitch": "Drum base pitch in Hz.",
    "pitch_envelope": "Drum pitch sweep amount.",
    "tone_noise": "Drum tonal/noise blend.",
    "drum_pattern": "Repeat for multiple drum voices: VOICE=PATTERN.",
    "drum_param": "Repeat per-voice override: VOICE.KEY=VALUE; use underscores in KEY.",
    "waveform": "Oscillator waveform.",
    "filter_attack": "Filter envelope attack in seconds.",
    "filter_decay": "Filter envelope decay in seconds.",
    "filter_sustain": "Filter envelope sustain level.",
    "filter_release": "Filter envelope release in seconds.",
    "filter_amount": "Filter envelope modulation in octaves.",
    "glide": "Pitch glide in seconds.",
    "legato": "Enable/disable legato note transitions.",
    "sub_mix": "Sub-oscillator amplitude blend.",
    "detune": "Pitch detuning in cents.",
    "pulse_width": "Pulse oscillator duty cycle.",
    "lfo_rate": "Filter LFO rate in Hz.",
    "lfo_depth": "Filter LFO depth in octaves.",
    "voices": "Maximum synth voice count.",
    "unison": "Oscillators per note.",
    "unison_detune": "Unison spread in cents.",
    "vibrato_rate": "Pitch vibrato rate in Hz.",
    "vibrato_depth": "Pitch vibrato depth in cents.",
    "arp": "Chord arpeggiation direction.",
    "arp_rate": "Arpeggio step length in beats.",
    "play": "Play the rendered result after export.",
    "play_only": "Render and play without exporting an audio file.",
    "device": "Playback device index or name.",
    "volume": "Application playback volume.",
    "mute": "Mute application playback.",
    "system_volume": "Explicitly request OS master volume change.",
    "system_unmute": "Explicitly request OS master unmute.",
    "tail": "cut truncates to loop; full retains release; wrap folds tails into loop.",
    "effect": "Repeat JSON effect objects to build an ordered effects chain.",
    "normalize": "Scale peak to 0.95 (mix uses 1.0).",
    "limit": "Clamp amplitude to ±0.98 (mix uses ±1.0).",
    "stems": "Directory for individual track WAV files.",
    "track_gain": "Repeat in input order; omitted tracks use gain 1.",
    "track_pan": "Repeat in input order; omitted tracks use center pan.",
    "track_offset": "Repeat offsets in seconds in input order.",
    "trim": "Repeat durations in seconds in input order.",
    "track_mute": "Repeat 1-based input track indexes to mute.",
    "track_solo": "Repeat 1-based input track indexes to solo.",
    "json": "Print machine-readable status or inspection output.",
    "overwrite": "Allow replacement of existing output/preset/stem files.",
    "log_file": "Append opt-in troubleshooting logs to a UTF-8 file.",
    "log_level": "Log detail; requires --log-file.",
    "log_format": "Readable lines or JSON records; requires --log-file.",
    "devices": "List available playback devices.",
    "diagnose": "Report playback backend availability.",
    "test_tone": "Play an internally generated test tone.",
    "repeat": "Playback repetition count.",
    "version": "Print package version and exit.",
    "help": "Print command usage and exit.",
}


def bounds(action):
    if not callable(action.type) or not getattr(action.type, "__closure__", None):
        return ""
    values = dict(zip(action.type.__code__.co_freevars, [c.cell_contents for c in action.type.__closure__]))
    return (
        f"{'integer' if values.get('integer') else 'number'} [{values['low']}, {values['high']}]"
        if "low" in values
        else ""
    )


parts = []
for tool, kind in TOOLS.items():
    rows = []
    for a in parser(tool)._actions:
        flags = ", ".join(a.option_strings) if a.option_strings else a.dest.upper()
        default = a.default
        if default is None and kind in ("drum", "bass", "lead"):
            default = presets.DEFAULTS.get(
                a.dest, presets.SOUND_DEFAULTS.get(a.dest) if kind != "drum" else None
            )
        if default is None:
            default = "context-dependent / unset"
        elif default == argparse.SUPPRESS:
            default = "—"
        choice = ", ".join(map(str, a.choices)) if a.choices is not None else bounds(a)
        meaning = DESCRIPTIONS.get(a.dest, a.help or "See command help.")
        if kind == "fx" and a.dest == "preset":
            meaning = "Version 1 effect-chain JSON preset file."
        if kind == "mix" and a.dest == "sample_rate":
            default = 44100
            meaning = "Mix output sample rate in Hz."
        if kind == "mix" and a.dest == "channels":
            default = 2
            meaning = "Mix output channel count."
        rows.append(
            '<tr data-search="'
            + html.escape(tool + " " + flags + " " + meaning)
            + '"><td><code>'
            + html.escape(flags)
            + "</code></td><td>"
            + html.escape(meaning)
            + "</td><td>"
            + html.escape(str(default))
            + "</td><td>"
            + html.escape(choice or "—")
            + "</td></tr>"
        )
    parts.append(
        f'<section id="{tool}"><h2>{tool}</h2><div class="table-wrap"><table><thead><tr><th>Argument</th><th>Meaning / units</th><th>Default</th><th>Accepted values</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div></section>"
    )
head = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Complete flags · GrooveScripting</title><link rel="icon" href="assets/favicon.svg"><link rel="stylesheet" href="assets/site.css"><script defer src="assets/site.js"></script></head><body><a class="skip" href="#main">Skip to content</a><header><a href="index.html" class="brand">GROOVESCRIPTING / Reference</a><nav aria-label="Commands">"""
nav = "".join(f'<a href="#{tool}">{tool}</a>' for tool in TOOLS)
body = """</nav></header><main id="main"><section><div class="eyebrow">ALL COMMANDS / GENERATED FROM CLI</div><h1>Every flag.</h1><p>Generated directly from the CLI parsers and preset defaults. Presets and project files can override synthesis defaults; explicit flags override presets. Numeric bounds are inclusive. Repeated flags accumulate in input order.</p><label for="search">Search flags</label><input id="search" type="search" placeholder="Try vibrato, log, track-solo…"><p id="search-status" role="status" class="muted"></p></section>"""
effects = """<section id="effects"><h2>Effect object reference</h2><p>Pass each object through a repeated <code>--effect</code> flag. Every object requires <code>type</code>. Effect processing uses float audio; normalize or limit before integer export when needed.</p><div class="table-wrap"><table><thead><tr><th>Type</th><th>Properties / bounds</th><th>Defaults</th></tr></thead><tbody><tr><td>gain</td><td>db [-120, 60]</td><td>db=0</td></tr><tr><td>fade</td><td>in_seconds ≥0; out_seconds ≥0</td><td>both 0</td></tr><tr><td>lowpass</td><td>hz [1, sample_rate/2-1]; resonance [0,1]</td><td>hz=1000; resonance=0</td></tr><tr><td>saturation</td><td>drive [0.001,100]</td><td>drive=1</td></tr><tr><td>delay</td><td>seconds [0.001,30]; feedback [0,0.999]; mix [0,1]; repeats integer [1,64]</td><td>seconds=0.25; feedback=0.4; mix=0.3; repeats=8</td></tr><tr><td>reverb</td><td>seconds [0.001,30]; mix [0,1]; decay [0,0.999]</td><td>seconds=1; mix=0.3; decay=0.5</td></tr></tbody></table></div><p>cut keeps the original timeline; full preserves the generated tail; wrap folds the tail onto the original loop. Reverb uses a deterministic multitap approximation.</p></section>"""
(ROOT / "docs/reference.html").write_text(
    head
    + nav
    + body
    + "".join(parts)
    + effects
    + '</main><p id="copy-status" role="status" class="toast"></p></body></html>',
    encoding="utf-8",
)
print("Generated complete reference for eight tools")
