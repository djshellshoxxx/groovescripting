# GrooveScripting 0.1.0 verification

Date: 2026-10-03 UTC. Baseline: repository had no branches or source; initialized main at fad5f9f2e9c318e623524fb6f1407c862819a1be. No AGENTS.md or prior project work existed. Specifications were written before their corresponding implementations; module contracts were established before parallel work.

## Built
Eight Python console commands, shared frame clock/pattern grammar, seven procedural percussion voices, monophonic bass, mono/poly lead, envelopes/filter/modulation/portamento/chords/arpeggiation, project sections and stems, WAV/FLAC IO, mixing/resampling/effects, versioned presets, optional PortAudio playback and explicit OS volume adapters. All commands share append-mode text/JSON troubleshooting logs via --log-file, --log-level and --log-format. Bash and PowerShell launchers and synchronized composition scripts call the same Python engine. Static Pages documentation includes full searchable references, copy commands, four embedded demo WAVs and source/launcher/example downloads.

## Local evidence
- Full pytest run: 86 passed in 62.09 seconds; final edge checks added rate-independent effect-preset inspection and stereo test tone/mono device diagnosis. The 48-test core/device/dispatch/helper subset also passed; final full count will be recorded after the current run.
- ruff check groovescripting tests scripts examples: passed. Python source formatted by ruff.
- python -m build: wheel and source distribution built. Installed the wheel into a new isolated virtual environment with its own dependencies; console drum rendering and metadata inspection passed for a Unicode path, with debug logs and no clipping.
- python examples/smoke.py --output-dir /tmp/groovescripting-final-examples: every offline recipe passed, including all three instruments, mixing, project sections/stems, gain/delay processing, logs, metadata, single percussion onset, accents/glide, arpeggiation and missing-backend diagnostics. No clipping warnings in those recipes.
- Bash composition launcher rendered successfully; all Bash launchers were syntax checked. PowerShell unavailable locally; Windows CI covers those wrappers.
- node --check docs/assets/site.js: passed. Static local links checked against repository subpath. Downloads regenerate deterministically from source; four mono 16-kHz PCM16 demo files contain nonempty finite audio and committed reproduction commands/seeds.
- Benchmark: two-bar three-track groove at 44.1 kHz stereo rendered 151,200 frames (3.429 seconds of audio) in 0.329 seconds on this host; mix buffer 2.419 MB. This is a local offline measurement, not a realtime/latency guarantee.

## Limitations
Physical output devices and host volume changes were unavailable and are unverified; playback/settings/interruption/master-volume adapters are tested through mocks. Browser preview of localhost was blocked by the cloud browser (net::ERR_BLOCKED_BY_CLIENT); live Pages interaction will be checked after deployment if accessible. Optional browser playground omitted; no placeholder controls. Windows/macOS execution is delegated to CI and must be reported with actual outcomes. Reverb is a deterministic multitap approximation; additive oscillators cap at64 harmonics and reject Nyquist crossings; filter coefficients update in64-frame blocks. Tone-edge fades are3 ms and legato suppresses envelope attack without retaining full oscillator/filter state. Render buffers are capped at10 million frames per instrument. Arrangement sections use cumulative exact clocks; stems are pre-master and final mix effects/normalization/limiting are not baked into them. Full arrangement tails apply only beyond the final section; wrap folds instrument tails by section. Playback repeats use blocking PortAudio calls and are not a hard realtime gapless transport. Master volume adapters target the default OS output, which can differ from an explicitly chosen playback device.

## Publication
Repository: https://github.com/djshellshoxxx/groovescripting . Publication, Pages, CI and commit evidence will be recorded after remote verification. No GitHub Release tag has been created; downloadable 0.1.0 distributions are provided by the website build.

## Dependencies/licenses
Local verification uses Python3.12.14, NumPy2.3.5, SciPy1.17.0, SoundFile0.13.1, pytest9.1.1. Python source/assets are original MIT work. NumPy/SciPy/SoundFile BSD-3-Clause; SoundFile wheels include LGPL libsndfile. PortAudio MIT, sounddevice MIT; optional pycaw/comtypes MIT. Dependencies ship their own bundled license texts; repository licenses and third-party references are documented in research/device specs. No third-party synthesis code or protected hardware-emulation assets copied.
