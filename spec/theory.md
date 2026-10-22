# Spec: Music theory helpers (groovtheory)

## Status

Implemented in 0.4.0 (`groovescripting/theory.py`). Verified by `tests/test_theory.py`.

## Objective

Make patterns more musical with less typing: chord symbols, more scales/modes, Euclidean rhythms and roman-numeral progressions. All functions are pure (no IO, no audio).

## Pattern grammar additions

- **Chord token** (note instruments): `ROOT[quality]@OCTAVE[/INVERSION]`, e.g. `Cm7@3`, `F@2`, `Am@3/1`. Expands to a `+` joined note chord before event fields, so `Cm7@3:1:0.8:0.9` keeps duration/velocity/probability, and a trailing `!` accents. The `@` marker avoids ambiguity with note names such as `Bb4`.
- **Qualities**: major (empty), m, dim, aug, sus2, sus4, 5, 6, m6, 7, maj7, m7, m7b5, dim7, 9, maj9, m9, add9. Unknown quality or notes outside MIDI 0..127 raise `ValueError`.
- **Euclidean drum pattern**: `euclid(PULSES,STEPS[,ROTATION])` is a drum pattern; hits are distributed as evenly as possible; positive rotation shifts hits later.

## Scales

`scale` option accepts chromatic, major, minor, pentatonic, minor_pentatonic, dorian, phrygian, lydian, mixolydian, locrian, harmonic_minor, melodic_minor, blues, whole_tone. `root` may be a pitch class number or note name.

## CLI

~~~text
groovtheory scale ROOT SCALE [--octave N]
groovtheory chord SYMBOL... [--octave N]
groovtheory euclid PULSES STEPS [--rotate N]
groovtheory progression KEY NUMERAL... [--octave N]
~~~

Shared `--log-file`, `--log-level` and `--log-format` flags precede the subcommand, e.g. `groovtheory --log-file theory.log chord Cm7`. Scale and chord outputs must stay within MIDI 0–127.

Output is a single line suitable for shell substitution into a pattern. Invalid input prints `groovtheory: MESSAGE` to stderr and exits 2.

## Progression numerals

Roman numerals I–VII; uppercase = major triad, lowercase = minor; optional `b`/`#` prefix and `7`, `maj7`, `dim`, `sus2`, `sus4` suffix. A `7` suffix retains major/minor case; explicit `maj7`, `dim`, `sus2` and `sus4` qualities override it. Degrees are interpreted against the major scale from KEY.

## Effects added in 0.4.0

`highpass(hz,resonance)`, `normalize(peak_db)`, `limiter(ceiling_db)` (tanh soft ceiling), `chorus(rate_hz,depth_ms,mix)` (interpolated modulated delay).

## Limitations

No automatic voice leading, key detection or chord-name recognition. Limiter is a static waveshaper, not a look-ahead dynamics processor.
