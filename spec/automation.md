# Arrangement automation specification

## Purpose

Automation lanes allow project parameters to change over arrangement time while preserving the existing offline deterministic renderer. Version 1 implements post-synthesis automation for controls that can be applied accurately to rendered PCM without reinterpreting note scheduling.

## Project schema

A track may contain:

```json
"automation": [
  {
    "param": "gain",
    "curve": "linear",
    "points": [
      {"beat": 0, "value": 0.2},
      {"beat": 8, "value": 1.0}
    ]
  }
]
```

Supported parameters in version 1:

- gain: 0..4, multiplicative linear amplitude
- pan: -1..1, stereo balance
- cutoff: 10..20000 Hz, post-synthesis low-pass automation
- saturation: 0..10, post-synthesis soft clipping drive

Supported curves: `linear` and `step`.

Points use absolute arrangement beats, not section-local beats. This means an automation lane continues across repeated or different sections. Points must be ordered strictly by beat and contain finite beat/value numbers. Beat must be >= 0. A lane requires at least one point. Duplicate params on one track are rejected.

Section track overrides may replace the complete `automation` array.

## Rendering

For each rendered section, automation receives that section's absolute starting beat. Values are evaluated for each output sample:

- before first point: first value
- between points: linear interpolation or previous-value step hold
- after last point: last value

Processing order for a track is:

instrument render -> track automation -> static track gain/pan/offset/trim -> stem/mix

Cutoff uses the existing stable lowpass implementation with a per-sample cutoff vector, clamped below Nyquist at application time. Saturation uses the same tanh transfer shape as the synth/effect path. Mono pan is a no-op. Automation does not alter MIDI/event scheduling in version 1.

## Validation and compatibility

Projects without automation render exactly as before. Automation is project-only in version 1; presets do not store arrangement automation. Unknown params/curves/keys fail. Automation values obey the same published parameter ranges.

## Acceptance tests

- validation rejects malformed lanes, duplicate params, unordered points and out-of-range values
- linear and step interpolation return exact endpoint values
- absolute-beat interpolation continues correctly across repeated sections
- gain automation changes amplitude sample-by-sample
- pan automation affects stereo balance without changing length
- cutoff/saturation automation produce finite output
- projects without automation remain unchanged
