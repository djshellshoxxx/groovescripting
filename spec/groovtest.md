# Spec: Musical assertion runner (groovtest)

## Status

Implemented in 0.3.0 (`groovescripting/musictest.py`). Verified by `tests/test_tools.py`.

## CLI

~~~text
groovtest SUITE.json [SUITE.json ...] [--seed N] [--format text|json] [--log-file PATH ...]
~~~

Exit codes: 0 all assertions passed, 1 at least one failed, 2 invalid suite/project/expression, 130 interrupted. Nothing is rendered or written.

## Suite format (version 1)

~~~json
{
  "version": 1,
  "project": "song.json",
  "seed": 42,
  "tests": [
    {"name": "four kicks", "where": "voice == \"kick\" and accepted == true", "count": {"min": 4}},
    {"name": "bass register", "where": "track == \"Bass\"", "all": "note >= 24 and note <= 60"},
    {"name": "no full-velocity hats", "where": "voice == \"closed_hat\"", "none": "velocity >= 1"},
    {"name": "unchanged", "fingerprint": "0123456789abcdef"}
  ]
}
~~~

- `project` is relative to the suite file. `seed` (optional) overrides the project seed; `--seed` overrides both.
- Each test has a unique `name`, an optional `where` predicate selecting trace records, and exactly one check: `count` (`min`/`max`/`eq` nonnegative integers), `all` (every selected record satisfies the predicate), `none` (no selected record satisfies it) or `fingerprint` (run fingerprint equals the value).
- Predicates use the safe grammar shared with groovdebug (`groovescripting/expr.py`): fields track, voice, instrument, section, origin, event_id, bar, beat, note, velocity (0..1), probability, duration, frame, accepted, accent; operators == != < <= > >=; and/or/not; parentheses. No evaluation of code.
- Failures list up to 20 offending event IDs with track, bar and beat.
