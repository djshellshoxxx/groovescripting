# CLI, presets and troubleshooting specification (v1)

## Commands and shared dispatch
Nine entry points: groovdrm, groovbss, groovld, groovmix, groovseq, groovfx, groovplay, groovinfo and groovmidi. `python -m groovescripting TOOL ...` is the portable fallback. Help and version always work without loading playback adapters. All invocations return 0 on success, 2 for input/schema/argument errors, 1 for runtime/IO/backend failures, 130 on user interruption.

## Configuration precedence
Parse command arguments with optional values unset. Resolve built-in defaults, then version 1 preset parameters, then project parameters, then explicit CLI values. Unknown preset keys fail. Preset JSON has `version:1`, `instrument:drum|bass|lead`, `name`, `params` object. Save resolved sound and musical values with overwrite protection. Built-ins: electronic, dance, breakbeat, experimental percussion; sub, plucked, acid, aggressive bass; pluck, sustained, soft_chord, experimental lead. Listing/inspection does not render.

## Output
--output defaults to tool.wav; --overwrite is required for any existing output. --format wav|flac and --subtype PCM_16|PCM_24|FLOAT (FLOAT only WAV). --play renders then plays; --play-only avoids disk writes. Offline default; device backend is imported only during playback. --effect takes repeatable JSON objects and preserves specified order; --tail cut|full|wrap defaults cut. --normalize and --limit are explicit options. Export conversion reports peak and clipping before encoding; integer clipping is documented and logged. Files containing spaces and Unicode are valid.

## Logging flags (all tools)
--log-file PATH enables append-mode UTF-8 file logging; no log is created unless selected. --log-level debug|info|warning|error defaults info. --log-format text|json defaults text; JSON uses one object per line. Levels require a log file. Log timestamps in UTC ISO8601, level, logger, message, and exceptions. Debug includes resolved configuration, package/Python/platform, timing and frame statistics, seed, requested sample rate, output path and audio backend decisions. Errors include traceback in enabled logs. Logs never change stdout JSON structure and never include raw audio samples. Log directory must exist; unwritable paths return runtime failure before rendering. Handler closes at completion, including failures. Appending is intentional and documented. Validation failures after logging flags are discovered are logged, including argparse errors.

## Flags and ranges
Musical defaults bpm120 [1,1000], bars1 integer [1,1024], beats4 [1,32], subdivision4 [1,64], swing0 [0,0.49], offset0 beats [-128,128], seed0 nonnegative integer, sample_rate44100 [8000,192000], channels2 one/two, gain0.7 [0,4], pan0 [-1,1]. Sound defaults and ranges in engine spec. Playback volume default0.7 [0,1]; mute opt-in; --visualizer/--no-visualizer ASCII playback waveform default off, --visualizer-height rows default9 [3,40], requires playback for rendering commands and rejects --devices/--diagnose; system volume [0,1] and system unmute opt-in only. --events PATH is a JSON list of explicit beat/duration/notes/velocity/probability events. --transpose semitones [-96,96]; --scale none|major|minor|pentatonic|chromatic; --root C4. --humanize seconds [0,0.1], --velocity-humanize [0,0.5]. Synth tools also accept --variation [0,1] and --density [0,1]; drums additionally accept --ghost-notes [0,1] and --fill-every integer [0,128]. Flag errors must name offending option.

Helper positional files and project schemas are specified in helpers spec. Repeatable track options map by input-file order and fail when more overrides than files. --json for info and diagnostics yields machine-readable objects; audio rendering status remains human-readable.

## Dispatcher pseudocode
1. Scan log flags independently; configure handler if valid, before full argument validation.
2. Parse tool parser; resolve preset and defaults; validate ranges and combinations.
3. If informational action, serialize metadata and exit.
4. Resolve project/events or input audio; render instrument/helper with seeded shared clock.
5. Apply ordered effects, optional normalization/limiting; inspect float peak; export protected path unless play-only.
6. If explicit system volume controls, invoke isolated adapter; if playback selected, apply app gain/mute and selected device.
7. Emit success, log elapsed seconds and shape; close log in finally.
8. On validation error log exception and return2; IO/backend error return1; interrupt stop playback and return130.

## Acceptance tests
Subprocess each console tool help/version and meaningful work; preset save/load equal arrays; flags override preset; logs contain debug settings and successful completion; invalid syntax/errors captured; JSON info remains parseable with logging; unwritable log fails; no log generated without flag; Unicode overwrite behavior; missing devices does not block rendering.

## Final integration behavior

Lead-only mode/voices/unison/arp controls are absent from the bass command. Tonal scale/transposition/frequency and sustained envelopes are absent from the percussion command; use per-voice pitch/envelope controls. groovseq accepts shared musical overrides, including BPM/meter/subdivision/swing/seed/humanization. Explicit section bars still define section lengths; --bars sets the default for sections without explicit bars. Arrangements use cumulative frame boundaries, so rounding never accumulates per-section drift. groovseq --tail full retains the final section's longest instrument release; wrap folds each section's instrument tails into its timeline; cut truncates every section. Audio effects then apply the selected tail policy independently. Mix/sequence stems are aligned pre-master tracks: global effects, normalization and limiting are applied only to final mixdown. Muted or nonsolo stems contain silence with mix length. Playback file --sample-rate and --channels perform actual conversion; tone mute/repeat and explicitly requested master controls are honored. Combining master controls with read-only device diagnostics fails. Unknown effect properties fail instead of being ignored.
