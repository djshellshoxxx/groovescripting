# GrooveScripting v0.4.1

This patch preserves the v0.4.0 theory tools, chord/Euclidean patterns, scales and effects while correcting edge cases found by regression tests.

- All documented scales and modes are available through CLI flags, projects and presets.
- Roman-numeral progressions accept explicit suspended, diminished and major-seventh qualities with lowercase degrees.
- Scale output rejects notes outside MIDI 0–127.
- Chorus uses silence before the start of its delay instead of repeating the first sample.
- `groovtheory` supports the same opt-in troubleshooting logs as the other commands.
- Native Windows x64, Linux x64, macOS arm64 and macOS x64 executables, wheel and source distribution are published with SHA-256 checksums after source tests and executable smoke checks.

Run the executable with a command such as `groovseq examples/first-groove.json --output groove.wav`. Examples and specifications are included in the source distribution. `groovtime` requires Git on PATH. Playback requires an audio device; hardware playback and host volume remain separate physical-device checks. macOS executables are unsigned and unnotarized.
