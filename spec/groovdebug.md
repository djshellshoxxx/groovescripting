# Spec: Deterministic Composition Debugger (groovdebug)

## Status

Approved for specification on 2026-10-06. This architecture-dependent feature is planned; the current renderer does not yet retain the complete event provenance it needs.

## Objective

Build a read-only debugger for GrooveScripting compositions. Let a composer stop an offline composition at a musical position, inspect events scheduled there, see which source data and resolved settings produced them, and reproduce the run.

This is the most distinctive of the selected concepts because it applies source-debugger operations to a musical timeline. It must be honest: it explains decisions only when the engine recorded evidence and labels unavailable causes instead of inventing explanations.

## Users and outcomes

- Composition authors inspect why an event was included, shifted, or omitted when trace data exists.
- Composers inspect a bar or event without manually searching a waveform.
- Developers reproduce a bug from the project, CLI options, engine version, and seed.
- Debugging is offline and read-only. It never changes device state or project files.

## Scope

### v1 includes

1. Deterministic expansion of a supported JSON arrangement into an ordered event schedule.
2. Breakpoints by bar, beat, track, event ID, and documented event predicates.
3. Continue, step one event, inspect current bar, list nearby events, and quit.
4. Event inspection for source path, track, instrument/voice, musical position, exact sample-frame position, note/velocity/duration, and known resolved settings.
5. Probability, swing/humanization, seed derivation, and voice-scheduling decisions only where instrumented and captured.
6. Noninteractive mode emitting the same structured trace for scripts/tests.
7. Replay of the same project/seed/options with a stable run fingerprint.

### Not in v1

- Recovering source events by analyzing rendered WAVs.
- Debugging arbitrary Python or external synth code.
- Claiming that the current engine has a candidate/rule system where it does not.
- Pausing a real-time audio callback.
- Editing events or projects in the debugger.
- Musical quality ratings or automatic repair.

## Foundation and prerequisites

Before release:

1. Add an internal event record separating source musical time from resolved playback time. Store track/instrument/voice, source pointer, event ID, and resolved sample-frame boundaries.
2. Derive random streams from documented stable inputs; capture probability outcomes and offsets without depending on unspecified iteration order.
3. Add an optional trace sink to project expansion/scheduling. Tracing is disabled in normal renders and cannot change audio output.
4. Define a stable run fingerprint from normalized project data, CLI overrides, engine version, and seed. Exclude machine paths and transient timestamps.
5. Map repetitions and generated events to source JSON Pointer, section/pattern, repeated bar, and iteration.

Initial support is for groovseq JSON arrangements and built-in drum/bass/lead event scheduling. Direct one-shot commands may follow when the shared trace format is stable.

## CLI and interaction contract

~~~text
groovdebug PROJECT.json
  [--seed INTEGER]
  [--break BAR[:BEAT]]
  [--track NAME]
  [--event EVENT_ID]
  [--where EXPR]
  [--commands FILE]
  [--format text|json]
  [--trace-out PATH]
  [--max-events INTEGER]
~~~

- Without --commands, a TTY opens the line-oriented debugger.
- In non-TTY mode, require --commands or --format json; never wait for terminal input.
- Breakpoint flags are repeatable; a match at any enabled breakpoint stops the view.
- --where uses a small documented grammar over event fields: track, voice, bar, beat, note, velocity, probability, accepted. It does not use eval or arbitrary code.
- --trace-out writes a protected trace file; existing files require --overwrite.
- --max-events is a positive bound against accidental unbounded output.

Interactive commands:

| Command | Behavior |
|---|---|
| continue / c | Continue to next breakpoint or end |
| step / s | Advance through the next scheduled/evaluated event |
| bar [N] | Show current or requested bar summary |
| events [RANGE] | List events in current or specified range |
| inspect EVENT_ID | Show one event and recorded inputs/decisions |
| why EVENT_ID | Explain captured decisions and list missing trace capabilities |
| seed | Show root and derived per-track/per-section seeds |
| fingerprint | Show normalized run fingerprint |
| help | Show commands |
| quit / q | Exit without modifications |

The debugger may precompute a bounded event schedule before interaction. Step advances the debugger view; it never pauses running audio.

## Trace event contract

Each trace record contains:

- trace_schema_version
- run_fingerprint
- event_id: stable within a run, derived from source identity and deterministic expansion identity, not array order alone.
- source: project-relative path, JSON Pointer, track, pattern/section, and repeat index.
- musical_position: 1-based bar and beat plus tick/subdivision when available.
- timing: requested beat/time, resolved beat/time after supported offsets, exact integer sample frame, and sample rate.
- event: instrument/voice, notes or drum action, duration, velocity, and probability when applicable.
- decisions: ordered records such as probability roll/pass/fail, humanization delta, swing displacement, quantization, and voice-scheduling result.
- resolved_parameters: effective event-relevant values with origin labels (default, preset, project, CLI, derived).
- availability: fields not implemented by a trace provider are marked unavailable.

Do not include secrets or absolute paths. Do not write PCM samples. Trace files use UTF-8 JSON Lines with a header and bounded event records.

## Deterministic scheduling and why

- Preserve the exact sample-frame scheduler and cumulative section-boundary behavior.
- Trace timing uses resolved integer frame values; musical location is explanatory and does not replace frame truth.
- Trace capture must not consume or reorder random values used in rendering. Observe decisions at their existing deterministic decision points.
- Same project, engine version, overrides, and seed yield identical ordered records and fingerprint.
- Changing source, seed, timing override, or engine version changes the fingerprint.
- Explain only facts that were captured. If an RNG draw is unavailable, say so. Do not show candidate notes until the generator actually enumerates and records candidates.

## Breakpoint expression grammar

Support finite numeric comparisons, equality/inequality, parentheses, and and/or over allowlisted fields. Example:

~~~text
track == "bass" and bar >= 17 and velocity < 80
~~~

Unknown fields, functions, attribute access, indexing, and executable input fail before project expansion with a useful position/column.

## Output and errors

Text mode shows current position, stop reason, event table, and trace availability. JSON mode emits a versioned envelope with fingerprint, status, breakpoint, position, and records. Stdout contains only selected format; diagnostics use stderr.

| Code | Meaning |
|---:|---|
| 0 | Session completed or user quit normally |
| 1 | Runtime or trace-write failure |
| 2 | Invalid project, command, expression, or option |
| 130 | User interruption |

No project mutation, rendering, playback, or device enumeration occurs.

## Real-time and performance boundaries

- Trace providers run at offline scheduling boundaries, never in the audio callback.
- A normal render without tracing must produce identical samples and allocate no per-event trace objects.
- Debug precomputation and output obey configurable event and byte limits.
- Oversized arrangements stop with a clear limit message before unbounded allocation.
- The line-oriented interface is intentional for accessibility, automation, and copy/paste workflows.
- Interruption leaves no partial trace at the final path; write a temporary sibling and atomically replace on success.

## Architecture and project changes

- Add a versioned event-trace model and serializer.
- Instrument project expansion, scheduling, RNG gates, and relevant renderer decisions via optional trace callbacks.
- Add a safe breakpoint-expression parser independent of Python evaluation.
- Register the groovdebug entry point and portable module fallback.
- Integrate tests, generated CLI reference, docs, and packaging.
- Keep trace schema independent of debugger UI so later groovtrace, provenance, profiler, coverage, and bisect tools can consume it.
- Add no playback or GUI dependency.

## Tests and verification

- Golden trace fixture with drums, bass, lead, repeated sections, overrides, probability, swing, humanization, and fixed seed.
- Repeat-run test compares trace bytes and fingerprint.
- Render-equivalence test proves tracing on/off yields sample-identical output and RNG behavior.
- Event identity covers repeats and stable source pointers.
- Breakpoint tests cover exact position, field filters, expression precedence, invalid syntax, unknown fields, and safe rejection of executable input.
- Subprocess tests cover commands, non-TTY behavior, limits, write errors, protected output, and JSON/text formats.
- Capability tests ensure unsupported causal fields are marked unavailable.
- Run package, CLI-reference, offline-install, and cross-platform CI checks.

## Acceptance criteria

1. Load a supported project and stop at a requested bar/beat without rendering or opening a device.
2. List events in exact sample-frame order and link them to source locations.
3. Reproduce captured probability/timing decisions using the same project and seed.
4. Distinguish recorded evidence from unsupported explanations.
5. Leave project bytes and audio behavior unchanged.
6. Keep JSONL versioned, deterministic, bounded, and pipe-friendly.
7. Add no blocking or trace allocation to normal audio callback/render paths.
8. Provide an event-trace schema reusable by provenance and musical test tools.

## Build order

1. Implement the versioned trace-event contract and stable run fingerprint.
2. Add optional trace capture at expansion and frame scheduling.
3. Capture probability/swing/humanization/seed decisions without altering RNG behavior.
4. Implement the safe predicate parser and breakpoints.
5. Implement batch output and protected JSONL writing.
6. Implement line-oriented interactive commands.
7. Add docs, examples, tests, and cross-platform verification.
8. Build provenance/time-travel consumers only after event identity and trace stability.
