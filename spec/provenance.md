# Spec: Event trace and provenance

## Status

Implemented in 0.3.0 (`groovescripting/trace.py`, `synth.render(..., trace=list)`, `projects.expand`). Verified by `tests/test_tools.py`.

## Objective

Record, for every scheduled event, where it came from and every transformation the engine applied, without changing audio. This is the shared contract consumed by groovdebug, groovtest and groovtime.

## Capture rules

- `projects.expand` is the single expansion path used by both rendering and tracing, so seeds, section overrides and timing are identical.
- `synth.render(instrument, options, trace=sink)` performs scheduling exactly as a render (same RNG draws, same order), appends one record per evaluated event, and returns before synthesis. No PCM is produced.
- Normal renders (`trace=None`) allocate no trace objects. A test proves rendered samples are identical whether or not a trace was taken for the same parameters.

## Record (trace_schema_version 1)

`event_id` (12 hex, hash of track, section index, repetition, voice, source identity, chord/arp step), `track`, `instrument`, `voice`, `source` {`pointer` (JSON Pointer of the producing pattern/events), `section`, `section_index`, `repetition`, `origin` (`pattern` or `variation`), `source_index`}, `bar`, `beat` (1-based), `timing` {`requested_beat`, `resolved_beat`, `frame`, `sample_rate`}, `notes`, `duration`, `velocity`, `probability`, `accent`, `accepted`, ordered `decisions`, `resolved_parameters` with origin labels (`default`, `preset`, `project`, `section`), `trace_schema_version`, `run_fingerprint`.

Decision kinds: `variation_insert`, `variation_shift`, `velocity_humanize`, `probability` (roll, threshold, pass/fail), `swing`, `humanize` (frames), `note_resolution` (scale/arpeggio), `voice_limit` (truncation frame), `window` (dropped outside render window).

Not captured (always listed in the header `unavailable`): automation values, oscillator phase, effect processing.

## Fingerprint

SHA-256 (first 16 hex) of canonical JSON of the validated project, CLI overrides, engine version and trace schema version. Paths and timestamps are excluded.

## Files

JSON Lines: one header record (`kind: "header"`, derived per-section/per-track seeds, event count, unavailable fields) followed by event records in frame order. Writes go to a temporary sibling and are atomically replaced; existing files require `--overwrite`. `--max-events` (default 100000) bounds collection.
