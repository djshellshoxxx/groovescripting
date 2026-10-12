# GrooveScripting v0.3.1 beta 1 — Windows x64

This prerelease integrates the October 11 audit fixes and improves resilience during interrupted writes.

## Included
- A self-contained Windows x64 executable. Python is not required.
- All 14 GrooveScripting commands, including MIDI interchange, waveform synthesis, event tracing, composition diffing, merge, and QA tools.
- Crash-safe output replacement for projects, WAV/FLAC files, MIDI files, instrument presets, and effect presets. On write failures the previous destination is preserved.
- Updated website download version and regression tests.

## Running on Windows

In PowerShell, from the directory holding the executable:

```powershell
.\groovescripting-windows-x64.exe --version
.\groovescripting-windows-x64.exe groovseq examples/first-groove.json --output groove.wav
.\groovescripting-windows-x64.exe groovinfo groove.wav --json
```

The JSON examples are available in the source distribution or repository.

Native audio device playback, MIDI hardware integration, and antivirus reputation require verification on a physical Windows machine. The automated release tests cover Windows execution, audio rendering, MIDI export/import, CLI help, lint/debug, and packaging. Playback uses the optional sounddevice integration and the local system's audio stack.

This is an experimental beta, not the stable v0.3.0 release.
