# Audio devices and explicit system volume

Optional `sounddevice` provides PortAudio output; NumPy is the engine array dependency.
Offline rendering imports neither sounddevice nor platform volume libraries. Install the
`playback` extra to use hardware. Hardware operations fail with actionable RuntimeError.
Device inventory is a JSON list of dictionaries including device index. Diagnosis checks
stereo float32 output at the requested rate and returns supported/error status without sound.
Playback accepts finite mono/stereo normalized floating arrays, scales stream gain 0..1,
optionally mutes, validates repeat 1..1000 and settings, and always stops on exit including
KeyboardInterrupt. Repetition streams the existing array sequentially without a large copy.
The test tone is 440 Hz for 0.5 seconds with short fades at default gain 0.1.

System master volume changes are explicit only: volume is scalar 0..1 and unmute is opt-in.
Windows uses optional pycaw endpoint API; Linux selects pactl or amixer; macOS uses
osascript. Subprocesses use argument lists, no shell, checked results and timeout. Unsupported
platform/dependency raises actionable errors. No playback call modifies master settings.
Capabilities reports dependency/adapter availability, explicitly unverified hardware status;
availability does not assert actual audio hardware or session access. Logs use the
`groovescripting.devices` logger, recording operations/errors without audio sample contents.

Pseudocode: validate inputs -> load optional backend -> check output format -> for repeats:
play + wait -> finally stop. Inventory -> query backend -> copy each mapping + index.
Diagnosis -> validate rate -> query output -> check settings -> return supported/error.
Master -> validate request -> select platform adapter -> invoke explicit mutations -> result.

Sources consulted 2026-10-03: official sounddevice usage/API and installation sources:
https://github.com/spatialaudio/python-sounddevice/blob/master/doc/usage.rst
https://github.com/spatialaudio/python-sounddevice/blob/master/src/sounddevice.py
https://github.com/spatialaudio/python-sounddevice/blob/master/doc/installation.rst
Hardware and platform master volume behavior require real-host verification; mocked unit
tests verify selection, arguments, validation and interruption cleanup only.

Windows endpoint API additionally checked against the maintainer documentation:
https://andremiras.github.io/pycaw/_modules/pycaw/utils.html
https://andremiras.github.io/pycaw/quickstart.html
