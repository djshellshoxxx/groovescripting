# Architecture Summary

From the package layout.

- **Synthesis.** `synth.py`, `music.py` and `effects.py` generate and shape sound; `audio.py` handles rendering and playback.
- **Sequencing and variation.** `timeline.py`, `variation.py`, `automation.py` and `presets.py` give deterministic, repeatable arrangements.
- **Interchange.** `midi.py` handles MIDI; `projects.py` and `merge.py` manage project files.
- **Quality and diagnostics.** `validation.py`, `lint.py`, `diagnostics.py`, `trace.py` and `debug.py` check and explain output.
- **Command line.** `cli.py` (entry point `__main__.py`) provides the `groovseq` commands; `atomic.py` writes outputs atomically.
