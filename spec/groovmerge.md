# Spec: Semantic project merge (groovmerge)

## Status

Implemented in 0.3.0 (`groovescripting/merge.py`). Verified by `tests/test_tools.py`.

## Objective

Three-way merge project files by musical dimension rather than by text lines, so independent musical edits combine cleanly and true conflicts are named precisely.

## CLI

~~~text
groovmerge BASE OURS THEIRS [--output FILE] [--overwrite]
  [--take DIMENSION=ours|theirs ...] [--prefer ours|theirs] [--format text|json]
~~~

## Dimensions

`tempo` (bpm, beats, subdivision, swing), `global` (bars, sample_rate, channels, seed, humanize, velocity_humanize), `sections` (the whole section list), and per track `track:NAME` (presence), `track:NAME.sound` (instrument, preset), `track:NAME.pattern`, `track:NAME.mix` (gain, pan, mute, solo, offset, trim), `track:NAME.automation`, and `track:NAME.params.KEY` for every parameter.

## Rules

- Per dimension: equal on both sides → keep; changed on one side only → take that side; changed differently on both → conflict.
- A track deleted on one side and edited on the other is a conflict on `track:NAME`.
- `--take` resolves conflicts whose dimension equals or is nested under the given dimension (longest match wins); `--prefer` resolves the rest.
- Track order follows OURS, then tracks only in THEIRS.
- The merged project is validated; an invalid result is reported as a conflict on `project`.
- With unresolved conflicts nothing is written and the exit code is 1. Success exits 0; invalid inputs exit 2. Without `--output` the merged project is printed.
