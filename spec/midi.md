# MIDI import/export specification

## Command

Add a ninth console command: `groovmidi`.

```
groovmidi import INPUT.mid --output project.json [--instrument lead] [--subdivision 4] [--no-quantize] [--include-drums] [--overwrite]
groovmidi export project.json --output arrangement.mid [--overwrite]
```

MIDI file I/O uses Mido. It does not require a realtime MIDI backend.

## Import

Version 1 imports Standard MIDI Files type 0 or 1 into one GrooveScripting project.

- type 2 files with independent track timelines and SMPTE time divisions are rejected; ticks-per-beat divisions must be positive
- ticks are converted to beats using `ticks_per_beat`
- zero tempo values are rejected as invalid input
- the first tempo event sets project BPM, default 120
- multiple distinct tempo values are rejected because project v1 has one global BPM
- the first time signature sets beats-per-bar, default 4/4; non-quarter-note denominators are accepted only when they map cleanly to quarter-note beats
- note_on velocity 0 is note_off
- overlapping same-channel/same-note notes are paired FIFO
- unclosed notes close at end-of-file
- simultaneous notes with equal start/duration/velocity are grouped into chord events
- import ignores non-note controller/program/meta events other than tempo, time signature and track name
- quantization defaults to the requested subdivision and rounds start/duration to subdivision steps; `--no-quantize` preserves beat fractions
- velocity maps 1..127 to 0..1
- each MIDI track containing notes becomes a GrooveScripting track; the selected instrument is bass or lead (default lead)
- duplicate track names are disambiguated in file order with numbered suffixes, including collisions with generated fallback names
- imported note events are stored as `params.events`
- project bars are ceiling(max event end / beats-per-bar), minimum 1
- channel 10 percussion import is opt-in through `--include-drums` (API `include_drums=True`); without it, percussion is ignored and percussion-only input fails with an actionable message
- enabled percussion import creates one drum track per source track and supported voice, with explicit events preserving timing/duration/velocity and a voice suffix on the source track name
- the supported GM notes are kick36, snare38, closed_hat42, open_hat46, clap39, tom45 and rim37 (the export mapping); unsupported channel-10 notes fail explicitly when drum import is enabled
- bass/lead selection applies only to melodic channels; drum import requires no new schema or dependencies

## Export

Export writes a type-1 Standard MIDI File with one MIDI track per active GrooveScripting track.

- bass/lead patterns and explicit event arrays are exported
- transpose and section offsets are reflected
- section repetition, track mute/solo, pattern override and preset resolution are respected
- event velocity maps 0..1 to 1..127; probability is not rolled during export and is encoded by omitting events whose probability is exactly 0
- note frequencies supplied as arbitrary Hz are rejected because Standard MIDI cannot represent them exactly without pitch-bend policy
- drum export uses General MIDI percussion channel 10 with voice mapping: kick 36, snare 38, closed_hat 42, open_hat 46, clap 39, tom 45, rim 37
- project BPM is emitted as set_tempo; beats-per-bar is emitted as time_signature when representable
- output ticks_per_beat defaults to 480
- automation/effects are audio-domain features and are not exported as MIDI CC in version 1

## Safety and file behavior

Existing output files require `--overwrite`. Invalid MIDI/project input returns the normal CLI input-error status. Import/export never opens a realtime MIDI port.

## Acceptance tests

- simple note/chord MIDI round-trips into a valid project
- import handles note_on velocity zero and overlapping notes
- conflicting tempo maps reject
- export respects sections, mute/solo and transpose
- drum voice mapping uses channel 10
- overwrite protection works
- `groovmidi --help` and `--version` work with no MIDI hardware/backend
