# GrooveScripting v0.5.0

Release candidate; publication requires validated native builds of this revision.

## Added
- MIDI percussion import with `groovmidi import --include-drums`, retaining the seven supported General MIDI voices, event timing and velocity alongside melodic tracks.
- Integrated developer wiki and consolidated all previously outstanding branch histories.

## Fixed
- Reject invalid MIDI timing and asynchronous files cleanly; preserve duplicate track names and sustained notes through file end.
- Preserve distinct stems when track names sanitize to identical filenames, and prevent master/stem path collisions.
- Repeat Euclidean macros using their expanded step count.
- Format arbitrary-Hz debugger notes and normalize rejected named notes for predicates.
- Apply mix normalization and limiting after the full effects chain.
- Resolve preset context when diagnosing ineffective controls.
- Publish protected outputs exclusively to preserve concurrently created files.
- Reject oversized silent arrangements before allocating audio buffers.

## Limits and compatibility
- Arrangements now enforce a total 10,000,000-frame output budget including repeats and full tails; split longer work into smaller projects.
- No-overwrite output requires hard-link support on the destination filesystem. Unsupported filesystems fail safely.
- Trace accepted/notes fields describe scheduler state; post-mix audibility and oscillator transposition are explicitly unavailable, with configured transpose shown separately.
- Retired the legacy hardcoded beta publisher; validated immutable tags use the main release workflow.
- Physical playback and OS volume need local hardware verification. Native Windows/macOS checks and signing/notarization are separate release requirements.
