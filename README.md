# GrooveScripting

Offline command line drum, bass and lead synthesis with sequencing, mixing, effects, playback and WAV inspection. Built for reproducible loops and shell based arrangements.

## Install

Requires Python 3.10+.

```sh
python -m pip install .
python -m pip install '.[playback]'
```

The second command adds optional playback support. Renderers work without audio hardware. Bash and PowerShell wrappers in `scripts/` delegate to the same engine; `GROOVESCRIPTING_PYTHON` selects its interpreter.

## First groove

```sh
groovseq examples/first-groove.json --output groove.wav --stems stems
groovplay groove.wav
groovinfo groove.wav --json
```

Use `examples/arrangement.json` for a section based arrangement. Protect existing outputs by default; add `--overwrite` deliberately when replacing them.

| Command | Purpose |
| --- | --- |
| `groovdrm` | Procedural seven voice drums |
| `groovbss` | Bass synthesis |
| `groovld` | Lead synthesis |
| `groovmix` | WAV track mixing |
| `groovseq` | JSON project arrangement and stems |
| `groovfx` | Ordered audio effects |
| `groovplay` | Playback, device listing and diagnostics |
| `groovinfo` | WAV metadata and signal statistics |

Each command exposes `--help`. Website source and detailed command documentation are in `docs/`; engineering specifications are in `spec/`. Every command has CLI help; `docs/reference.html` contains the generated full flag defaults and ranges.

## Troubleshooting logs

```sh
groovseq examples/first-groove.json --output debug.wav --log-file render.log --log-level debug --log-format text
groovplay --diagnose --log-file playback.jsonl --log-level debug --log-format json
```

Logs are opt in. Include the command, project, log, OS and Python version in bug reports. Fix the seed and sample rate for reproducible comparisons. Run `groovplay --devices` for playback target discovery. System volume and device access depend on OS support and local audio policy; hardware behavior requires local verification.

## Circuit Drift Labs

[Visit Circuit Drift Labs](https://djshellshoxxx.github.io/circuitdriftlabs/).

Run the offline recipes with `python examples/smoke.py --output-dir example-output`. Playback needs a local audio device. Linux playback may require `libportaudio2`; SoundFile source installs may require `libsndfile1`. Windows and macOS wheels generally bundle the required libraries.

## Platform installation and uninstall

On Windows use `py -m pip install .` from the source checkout; on Linux and macOS use `python3 -m pip install .` in a virtual environment. Install `.[playback]` for device access and `.[windows-volume]` only if Windows master-volume control is needed. Linux uses existing `pactl` or `amixer`; macOS uses `osascript`. Offline use needs no elevated privileges. Remove the package with `python -m pip uninstall groovescripting`. The portable fallback is `python -m groovescripting groovseq examples/first-groove.json --output groove.wav`.

## Development

```sh
python -m pip install '.[dev]'
python -m pytest
python -m build
python scripts/package_downloads.py
```

CI tests Python on Linux, Windows and macOS. The Pages workflow packages downloads then publishes `docs/`. Offline render validation and hardware validation are documented separately in `docs/verification.md`.

MIT licensed. See `LICENSE`.
