# Spec: GrooveScripting Linter (groovlint)

## Status

Approved for specification on 2026-10-06. Implemented in 0.3.0 (see tests/test_tools.py).

## Objective

Add a deterministic CLI linter that checks GrooveScripting projects and rendered audio for measurable structural and signal-integrity conditions. It should catch malformed or risky inputs early, emit stable machine-readable findings, and support shell scripts and CI.

The first release is bounded to the repository's current formats: versioned JSON arrangement/preset documents and WAV/FLAC files supported by the existing audio layer. It must not judge whether music is good, infer artistic intent, or claim to detect every audible problem.

### Users and outcomes

- Composers receive actionable findings before or after rendering.
- Scripts can gate a render on selected severities with stable exit codes.
- CI can retain JSON output and compare findings between revisions.
- Render, validation, and playback behavior remains unchanged.

## Scope

### Included in v1

1. Static validation of a project or preset using existing schema validators.
2. Rendered-file inspection using current audio decoding/statistics plus deterministic analysis helpers.
3. Stable rule IDs, severity, location, measured evidence, and suggested remediation.
4. Text/JSON output, rule filters, severity thresholds, and machine-usable exit status.
5. Optional threshold profiles with bounded and documented values.

### Excluded from v1

- Semantic comparison, relational event queries, and MIDI import.
- Subjective quality, genre, or “bad music” judgments.
- Automatic repair or source/audio rewriting.
- Frequency-band-specific claims such as “bass must be mono” without a validated measurement method.
- Source-level groove analysis before a shared event representation exists.
- Real-time monitoring or device loopback capture.

## CLI contract

~~~text
groovlint INPUT [--audio RENDERED_AUDIO]
  [--format text|json]
  [--fail-on off|note|warning|error]
  [--only RULE_ID ...]
  [--ignore RULE_ID ...]
  [--thresholds FILE]
  [--strict]
~~~

- INPUT is one supported JSON project or preset. --audio adds a WAV/FLAC artifact to inspect in the same run.
- If INPUT is an audio file, run audio analysis directly; reject --audio.
- --format defaults to text. --fail-on defaults to error. off suppresses finding-based failure but not malformed input or IO failure.
- --only and --ignore accept repeatable or comma-separated stable rule IDs. Supplying both is invalid.
- --thresholds loads a versioned JSON profile. Unknown keys, invalid ranges, and unsupported versions fail before analysis.
- --strict raises the default threshold from error to warning. Explicit --fail-on takes precedence.
- Stdout contains only the selected report format. Diagnostics go to stderr. The command writes no files.

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Analysis completed; no finding met --fail-on |
| 1 | Analysis completed; at least one finding met --fail-on |
| 2 | Invalid argument, schema, format, malformed or unreadable input |
| 3 | Runtime analysis or serialization failure |
| 130 | User interruption |

The command never modifies inputs.

## Finding schema

JSON output is an object with schema_version, tool, input, summary, metrics, and findings. Each finding contains:

- rule_id: permanent identifier such as PRJ001 or AUD003.
- severity: note, warning, or error.
- category: project, audio, or render.
- message: concise factual statement.
- location: JSON Pointer when a project location applies; otherwise null.
- evidence: observed values and threshold values, including units.
- suggestion: optional next step, phrased as a suggestion.
- confidence: high, medium, or low only for heuristic rules.

Findings sort by category, source location, and rule ID. JSON serialization is deterministic. Absolute paths and elapsed timing are omitted by default.

~~~json
{
  "schema_version": 1,
  "tool": "groovlint",
  "input": {"path": "mix.wav", "kind": "audio"},
  "summary": {"errors": 0, "warnings": 1, "notes": 0},
  "metrics": {"sample_rate_hz": 44100, "channels": 2, "peak_dbfs": -0.2},
  "findings": [{
    "rule_id": "AUD001",
    "severity": "warning",
    "category": "audio",
    "message": "Samples reach the digital full-scale boundary.",
    "location": null,
    "evidence": {"peak_dbfs": 0.0, "clipped_sample_count": 6, "threshold_dbfs": 0.0},
    "suggestion": "Inspect the source mix and export headroom.",
    "confidence": "high"
  }]
}
~~~

## Initial rules

Rules are independently testable and documented. IDs are permanent; materially different behavior requires a new ID.

### Project and preset rules

| ID | Severity | Condition |
|---|---|---|
| PRJ001 | error | JSON parsing or required schema validation fails. Include the underlying path and validator message; return code 2. |
| PRJ002 | warning | A render request exceeds the documented per-render frame budget or would predictably exceed it before allocation. |
| PRJ003 | note | A valid configured option is known to have no audible effect in the selected instrument/path, based on schema and renderer contracts. |
| PRJ004 | warning | A configured value is at a documented cost boundary, such as maximum supported polyphony. Include actual value and bound. |

Reuse validate_project, validate_preset, and shared range contracts. Do not maintain a second copy of validation rules.

### Audio rules

| ID | Severity | Condition |
|---|---|---|
| AUD001 | warning | Decoded samples hit or exceed digital full scale. Describe the measured full-scale condition; do not claim audible clipping is proven for integer PCM. |
| AUD002 | note | Peak is below configurable near-silence threshold for a nonzero-duration file. |
| AUD003 | note | Mean/DC offset exceeds a configurable absolute threshold. |
| AUD004 | warning | First or last analysis window has a discontinuity above a configured threshold. State boundary and measured jump; do not claim every system will reproduce an audible click. |
| AUD005 | warning | A channel is silent or materially lower than the other using configurable RMS ratio and absolute floor. |
| AUD006 | note | Sample rate, channel count, or duration falls outside an optional target profile. No target applies by default. |

Every audio rule reports window size, channel scope, units, threshold, and observation. Decode through the existing audio module and bound memory using chunked reads or a measured analysis-window strategy.

The first release reports facts about project and audio independently. It must not claim that a rendered file matches an arrangement without a separately specified deterministic comparison.

## Threshold profile

Version 1:

~~~json
{
  "version": 1,
  "audio": {
    "near_silence_dbfs": -90.0,
    "dc_offset_peak": 0.01,
    "boundary_jump_peak": 0.25,
    "channel_rms_ratio_db": -45.0,
    "channel_rms_floor_dbfs": -90.0
  },
  "targets": {
    "sample_rate_hz": null,
    "channels": null,
    "duration_seconds": null
  }
}
~~~

Numbers must be finite and within documented physical ranges. Null disables a target. A profile is read-only and never becomes an implicit project setting.

## Architecture and project changes

- Add a linter module consuming validated project/preset objects and decoded audio metadata/signal windows.
- Represent each rule with explicit input requirements, stable ID, default severity, and evidence builder.
- Reuse current validation and audio inspection modules.
- Register the CLI entry point in pyproject.toml, dispatcher/help tests, reference generation, docs, and package manifest as required.
- Never import playback-device modules; linting works in the offline install.
- No new dependency is required for v1.

## Performance and safety

- Set and document a project-file size limit; fail cleanly above it.
- Audio analysis uses chunked reads or a bounded analysis-buffer strategy.
- Large-file processing allocates no more than one decoded analysis window plus existing decoder buffers.
- Malformed inputs fail before expensive analysis.
- Reports exclude elapsed timing by default.
- Rules are side-effect free.

## Tests and verification

- Unit-test every rule below, at, and above threshold; cover mono, stereo, finite, and malformed data.
- Project fixtures cover valid projects/presets, invalid JSON/schema, frame estimates, and boundary parameter values.
- Generate audio fixtures for silence, DC offset, full-scale samples, boundary jumps, mono, balanced stereo, and imbalanced stereo.
- CLI subprocess tests cover text/JSON validity, stable ordering, filters, strict/fail-on behavior, exit codes, stdout/stderr, and unchanged input hashes.
- Clean offline installation proves playback extras are unnecessary.
- A large-file test verifies bounded memory behavior.

## Acceptance criteria

1. Help lists supported options and ranges.
2. Project/preset schemas use existing validators.
3. Every v1 audio rule reports the expected rule ID and measured evidence on generated fixtures.
4. Identical inputs/options produce byte-identical JSON apart from documented path normalization.
5. --fail-on gates CI using the documented exit codes.
6. Inputs are unchanged and no playback device is opened.
7. Unsupported MIDI, arbitrary audio diagnosis, and subjective judgments are not implied.
8. README, CLI reference, tests, packaging, and this spec agree before release.

## Build order

1. Confirm validation and audio-reader contracts.
2. Add rule model and static project rules.
3. Add bounded audio metrics and rules.
4. Add CLI output, filters, thresholds, and exit behavior.
5. Add docs, generated reference, and fixtures.
6. Run full tests, lint, package build, offline smoke, and large-file memory verification.
