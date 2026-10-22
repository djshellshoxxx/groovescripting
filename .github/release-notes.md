# GrooveScripting v0.4.1

Standalone executables for Windows x64, Linux x64 and macOS (Apple silicon and Intel), plus Python wheel and source distribution. Python is not required for standalone executables.

## Fixes

- All documented scales and modes now work through synthesis CLI arguments, presets and project JSON, using one shared list.
- Roman-numeral progressions with explicit maj7, dim, sus2 and sus4 suffixes produce supported chord symbols for lowercase numerals.
- Chorus starts with silent delay history and handles empty buffers.
- Event provenance pointers resolve section track names containing `/` or `~` correctly and identify the actual scheduled events, drum map or pattern according to source precedence.
- Music theory accepts numeric pitch-class roots, validates MIDI note ranges and supports shared troubleshooting logs including argument errors.
- Release publishing verifies an immutable tag matches the package version, generates SHA256SUMS and refuses to overwrite existing assets.
- Native release packaging now requires source lint, the full regression suite and documented offline examples before building executables; executable smoke tests remain required.

Includes the v0.4.0 music theory helpers, chord and Euclidean patterns, scales/modes and new effects. Run `groovescripting-<platform> --help` or pass any of the 15 tool names as the first argument.

Physical audio playback and OS volume changes require local audio hardware and are not validated by cloud rendering tests. macOS binaries are unsigned; signing and notarization are not included.
