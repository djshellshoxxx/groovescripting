# MIDI import/export specification

## Command

Add a ninth console command: `groovmidi`.

```
groovmidi import INPUT.mid --output project.json [--instrument lead] [--subdivision 4] [--no-quantize] [--overwrite]
groovmidi export project.json --output arrangement.mid [--overwrite]
```

MIDI file I/O uses Mido. It does not require a realtime MIDI backend.

## Import

Version 1 imports Standard MIDI Files type 0 or 1 into one GrooveScripting project.

- ticks are converted to beats using `ticks_per_beat`
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
- imported note events are stored as `params.events`
- project bars are ceiling(max event end / beats-per-bar), minimum 1
- channel 10 percussion import is deferred; a file containing only channel 10 notes fails with an actionable message in version 1

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
