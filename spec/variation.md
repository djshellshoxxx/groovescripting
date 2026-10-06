# Pattern mutation and variation specification

## Purpose

GrooveScripting variation is deterministic musical mutation, not unconstrained random generation. The same input, options and seed must always produce the same event list. Existing patterns remain unchanged when variation controls are omitted or set to their neutral values.

## Public controls

Instrument renderers accept:

- `variation` float 0..1, default 0. Controls the strength/probability of timing and velocity mutation.
- `density` float 0..1, default 1. Existing events are retained independently with this probability before other mutation.
- `ghost_notes` float 0..1, default 0. Drum-only probability of adding low-velocity hits on empty subdivision steps.
- `fill_every` integer 0..128, default 0. Drum-only. When nonzero, every Nth bar may receive additional low-velocity hits in its final beat.
- Existing `seed` controls repeatability. Per-drum voice streams derive stable child seeds so voices do not mutate identically.

CLI spellings are `--variation`, `--density`, `--ghost-notes`, and `--fill-every`. Bass and lead expose variation/density; drum additionally exposes ghost notes and fills.

## Event behavior

Mutation operates after pattern expansion so total bars and loop boundaries are known.

1. Copy input events; never mutate the caller's objects.
2. Retain each event when RNG <= density.
3. When variation > 0, perturb retained event velocity by at most ±0.25 * variation and clamp to 0..1.
4. When variation > 0, perturb event beat by at most ±0.25 subdivision step * variation, clamp to [0,total_beats), and sort by beat.
5. For drums, ghost_notes samples empty subdivision positions and inserts hits with velocity 0.15..0.45 and normal probability 1.
6. For drums, fill_every considers the final beat of every Nth bar and inserts additional low-velocity hits on empty subdivision steps. Fill strength scales with variation; if variation is zero, fill_every alone uses a conservative fixed 0.35 fill probability.
7. Mutation never changes pitched-note identity. Tonal pitch mutation is intentionally deferred.

Explicit event JSON and pattern-generated events both use the same mutation path.

## Validation

Nonfinite values fail. density, variation and ghost_notes must be within 0..1. fill_every must be integer 0..128. ghost_notes/fill_every are rejected for bass/lead persisted parameters.

## Acceptance tests

- neutral controls are bit-for-bit event-equivalent
- same seed produces identical mutated events; different seed changes at least one event when mutation is active
- density 0 removes existing events
- velocity and beat remain within bounds
- ghost/fill insertion only occurs for drums and only on empty subdivision positions
- mutation never alters note pitch data
- CLI/preset/project validation uses the same ranges
