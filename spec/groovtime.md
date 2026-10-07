# Spec: Composition time travel (groovtime)

## Status

Implemented in 0.3.0 (`groovescripting/timeline.py`). Verified by `tests/test_tools.py`.

## Objective

Inspect, render and compare earlier composition states deterministically. A state is a committed Git revision of a project file (or `WORKTREE`, the current file). Because rendering is deterministic for a given project, engine version and seed, a revision plus its fingerprint fully identifies what was heard.

## CLI

~~~text
groovtime log PROJECT [--limit N] [--format text|json]
groovtime show PROJECT [--at REV]
groovtime render PROJECT [--at REV] --output FILE [--overwrite] [--seed N]
groovtime diff PROJECT [--from REV] [--to REV] [--seed N] [--format text|json]
~~~

- `log` lists commits touching the file with date, subject and run fingerprint (or the validation error for invalid states).
- `show` prints the validated project at a revision.
- `render` renders a revision through the normal groovseq path; outputs are protected unless `--overwrite`.
- `diff` compares event traces by `event_id`: added, removed, and changed events (notes, velocity, accepted, duration, probability, bar, beat, frame). Defaults: `--from HEAD --to WORKTREE`.
- Revisions starting with `-` are rejected. Git is required; nothing in the repository or working tree is modified.

Exit codes: 0 success, 1 git/IO failure, 2 invalid project/revision/option, 130 interrupted.
