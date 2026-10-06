# GrooveScripting

Offline command line drum, bass and lead synthesis with sequencing, deterministic variation, automation, MIDI interchange, mixing, effects, playback and WAV inspection. Built for reproducible loops and shell based arrangements.

## Install

Requires Python 3.10+. Follow the [Linux and Windows installation guide](docs/installation.md) for prerequisites, isolated environments, playback, troubleshooting and uninstall commands.

Linux / macOS, from the source directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[playback]"
```

Windows PowerShell, from the source directory (activation is optional):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[playback]"
.\.venv\Scripts\groovseq.exe --help
```

Install `.` instead of `.[playback]` for offline rendering alone.

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
| `groovmidi` | MIDI project import/export |

Use `--variation` and `--density` on synth commands for seeded pattern mutation; drums also support `--ghost-notes` and `--fill-every`. Project tracks support gain, pan, cutoff and saturation automation lanes. `groovmidi import` converts melodic MIDI into a project and `groovmidi export` writes project arrangements as Standard MIDI Files.

Each command exposes `--help`. Website source and detailed command documentation are in `docs/`; engineering specifications are in `spec/`. Every command has CLI help; `docs/reference.html` contains the generated full flag defaults and ranges.

## Troubleshooting logs

```sh
groovseq examples/first-groove.json --output debug.wav --log-file render.log --log-level debug --log-format text
groovplay --diagnose --log-file playback.jsonl --log-level debug --log-format json
```

Logs are opt in. Include the command, project, log, OS and Python version in bug reports. Fix the seed and sample rate for reproducible comparisons. Run `groovplay --devices` for playback target discovery. System volume and device access depend on OS support and local audio policy; hardware behavior requires local verification.

## More groove formulas

The [groove cookbook](examples/GROOVE_COOKBOOK.md) includes ten complete projects: house, techno, drum and bass, half time, hip hop, UK garage, hard trance, electro, dub and 7/8. Each recipe shows its drum and note patterns, tempo, swing and render commands. Editable JSON files are in `examples/grooves/`; the same recipes appear on the Pages site.

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
