# MIDI Drum Import Implementation Plan

**Goal:** Complete file-based percussion interchange without changing default melodic imports.
**Architecture:** Extend the existing importer to collect channel-10 notes only when include_drums=True. Emit one drum track per supported voice per source track, using existing params.events and params.voice. Use the existing seven-voice export mapping in reverse; reject unsupported notes explicitly. Keep melodic notes and metadata in the same project, sharing quantization and EOF behavior.
**Tech stack:** Python 3.10+, Mido, existing project validation/rendering.
**Spec:** spec/midi.md (updated alongside implementation).

## Constraints and decisions
- API: import_file(path, instrument='lead', subdivision=4, quantize=True, include_drums=False).
- CLI: groovmidi import --include-drums. Default remains melodic-only.
- No new dependencies or project schema. Preserve deterministic names and output protection.
- Supported GM notes: kick36, snare38, closed_hat42, open_hat46, clap39, tom45, rim37.
- Unknown channel-10 notes produce ValueError with note number when enabled; ignored under legacy melodic-only behavior.
- Bass/lead selection applies only to melodic tracks. Drum duration/velocity use existing event fields. Channels other than10 remain melodic.

## Tasks
- [x] GS-11 (lead, midi.py/test_midi.py/spec/midi.md): Write failing real-file tests for percussion-only import, mixed melodic/drum import, all seven voices, zero-velocity note-offs, unknown notes, names, no-quantize, and API flag validation. Verify expected failure before implementation.
- [x] GS-11: Implement opt-in import using existing timing/grouping paths and deterministic disambiguation. Verify renderable projects, exact MIDI export round-trip of notes/timing/velocities, CLI output and overwrite protection. Update README/help/spec/reference.
- [x] GS-12 (lead): Consolidate branch histories; record each remote tip and ancestor check. Already merged three outstanding heads, no conflicts; preserve remote branches and user history.
- [x] GS-13 (audit workers): Audit every production module on the final integrated source, tests and packaging/CI. Report evidence and reproduce defects. Lead resolves material findings using failing regressions.
- [x] GS-14 (lead): Full pytest, Ruff, coverage gate, build, offline examples, generated docs/download checks and clean-wheel smoke; commit integrated delivery and final audit report.

## Review focus
Mixed channels must not become melodic percussion; colliding source/voice names must remain unique; note_on velocity0 must close notes; quantization must not create zero-duration events; malformed MIDI must return an input error without output. Test each in GS-11. Native/hardware verification remains external. Public release and destructive branch deletion are excluded.
