# Architecture Summary

Module responsibilities verified against the implementation.

- **Synthesis.** `synth.py`, `music.py` and `effects.py` generate and shape sound; `audio.py` handles audio file I/O and mixing; `devices.py` handles playback.
- **Sequencing and variation.** `projects.py` expands sections and renders arrangements; `variation.py`, `automation.py` and `presets.py` provide reproducible controls. `timeline.py` inspects and renders Git revisions.
- **Interchange.** `midi.py` handles MIDI; `projects.py` and `merge.py` manage project files.
- **Quality and diagnostics.** `validation.py`, `lint.py`, `diagnostics.py`, `trace.py` and `debug.py` check and explain output.
- **Command line.** `cli.py` (entry point `__main__.py`) provides the core audio commands; tool modules expose additional commands; `atomic.py` writes outputs atomically.
