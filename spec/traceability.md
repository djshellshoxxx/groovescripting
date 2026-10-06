# User requirements traceability

Source: the complete implementation request attached on 2026-10-03 and the additional troubleshooting-log flag request. No requirement is removed by this matrix. Related bullets are grouped in rows; each row explicitly names its covered requirements. Paths are repository-relative. Status distinguishes code inspection from executed evidence: **implemented** means code exists, **pending verification** means the final verification report must record the actual run, **partial** identifies an omission to resolve, **external** requires a host/service unavailable locally, and **optional omitted** is an explicitly optional feature. Test references name behavioral suites, not a claim that their latest run passed. Final test counts and publication identifiers belong in `docs/verification.md`. Local evidence supplied after reinspection: 85 tests passed in the previous full run; five dispatch/clock/tail regressions passed separately; the final 86-test suite was running at this update. Wheel/sdist builds, clean venv installation, all14 offline smoke recipes, Bash composition, Ruff, Node syntax and static local links passed. Physical devices, real browser interactions and remote CI/publication remain separate evidence requirements.

| ID | Requirements covered | Specification / implementation | Verification / status |
|---|---|---|---|
| W01 | Inspect repository, branches, existing files and AGENTS before edits; preserve unrelated work | Repository history and task execution record | Final report must record inspected baseline and branch; pending verification |
| W02 | Autonomous routine decisions, documented assumptions; questions only for essential blockers | `docs/research.md`, `spec/*.md` | Python/offline/shared-engine decision documented; implemented |
| W03 | Current primary documentation and relevant existing projects researched before dependency/device choice | `docs/research.md`, `spec/devices.md` | Primary NumPy/SciPy/SoundFile/sounddevice/pycaw references; implemented |
| W04 | Proper dependency/asset licensing and attribution | `LICENSE`, `pyproject.toml`, `docs/research.md` | Dependency license record; final distribution/license check pending |
| W05 | Implement specifications; no TODO handlers/demo buttons/misleading claims | All modules, static website | Tests plus final code/docs audit; pending verification |
| W06 | Independent parallel agents with clear ownership when available | Task execution record | Implementation/docs/testing work delegated; execution evidence outside source |
| W07 | Honest platform, hardware, test and publication claims | `spec/devices.md`, final verification report | Hardware explicitly unverified; actual CI/publication outcomes external |
| W08 | Keep code, specs, research and docs in this repo; commit/push; Pages if permitted; exact blockers otherwise | Repository, `.github/workflows/pages.yml` | Final commit/remote/Pages records pending external operation |
| A01 | Appropriate language evaluated for portability, audio, packaging, performance and scripting; compiled DSP where useful | `docs/research.md`, `pyproject.toml` | Python with compiled NumPy/SciPy; implemented |
| A02 | Maintainable ports, honest distinction between launchers and native DSP; no duplicate engine | `scripts/groov*.sh`, `scripts/groov*.ps1`, README | Shared runtime launchers; Bash/runtime checks pending; PowerShell requires available runtime |
| A03 | Shared parsing/validation, music clock/notes/scales/patterns, synthesis/effects, IO/playback, presets/projects, mixing/export, RNG/errors | `cli.py`, `music.py`, `synth.py`, `effects.py`, `audio.py`, `devices.py`, `presets.py`, `projects.py`, `diagnostics.py` | All behavioral suites; implemented |
| A04 | Offline without device; optional playback; no JACK/admin/special hardware required | `pyproject.toml` extras, lazy device imports | `test_devices.py`, clean-install/render smoke; pending verification |
| S01 | Full specs before implementation for every primary/helper; purpose/workflows/syntax/complete flags/defaults/ranges/units/combinations | `spec/cli.md`, `spec/engine.md`, `spec/helpers.md`, generated `docs/reference.html` | Reference generation from parsers; chronology and all defaults audit pending |
| S02 | DSP signal flow, grammar, IO schemas, preset versioning, device/platform behavior, errors/exit codes/performance limits | `spec/engine.md`, `spec/helpers.md`, `spec/devices.md`, `spec/cli.md` | Algorithms/schema documented; practical performance measurement in final report pending |
| S03 | Detailed pseudocode, acceptance criteria/tests, executable examples | `spec/*.md`, `examples/smoke.py`, tests | Pseudocode and acceptance suites; every example execution pending |
| S04 | Requirements→implementation→test matrix updated and examined in final audit; never delete requirements to pass | This file | Final audit must close partial/pending rows with evidence |
| M01 | BPM/bars/meter/subdivision/swing/offset with exact clock and frame rounding for alignment | `music.beat_frame`, `synth.render`, `projects.render_project` | `test_synth.py` clock/swing tests; `test_helpers.py` exact-section alignment; implemented |
| M02 | Note duration/rests/ties/velocity/accents/probability; compact safe unambiguous grammar | `music.parse_pattern`, `synth._events` | Pattern/invalid/tie/probability/accent tests; implemented |
| M03 | Named octaves, MIDI notes, tuning and Hz sound design | `music.note_value/frequency`, CLI `--frequency` and `--pitch` | Frequency/note conversion and bounds tests; A4=440 equal temperament; implemented |
| M04 | Transposition and optional scale quantization | `synth.render`, CLI `--transpose/--scale/--root` | Transpose/scale tests; implemented |
| M05 | Deterministic randomization, timing and velocity humanization | Local NumPy RNG, project seed derivation | Synth/project determinism and humanization tests; implemented |
| M06 | Sample rate, mono/stereo, output gain, WAV/FLAC and export conversion | `audio.py`, CLI output flags | IO/channel/resampling tests; CLI roundtrip checks pending |
| M07 | Output paths, overwrite protection, spaces/non-ASCII | `audio.write`, presets/save, project/save | `test_io_and_overwrite`; CLI Unicode tests pending |
| M08 | Preset load/save/list/inspect; versioning; flags override preset/project override defaults | `presets.py`, `cli.render_options`, `projects.py` | Preset roundtrip/precedence tests pending |
| M09 | Render-only/play-only/render-and-play; help/version/errors/machine-readable info | `cli.py` | All eight CLI smoke and exit-code/JSON tests pending |
| M10 | JSON expressive event files and validated project schemas | `cli.json_data`, `synth._events`, `projects.validate` | Invalid events/project override/schema tests; implemented |
| M12 | Track-specific override precedence including humanization | projects.render_project parameter resolution | Resolved: preserve preset/track values unless global explicitly set; `test_project_rounding_does_not_accumulate_and_humanization_precedence` regression |
| M11 | Portable Bash/PowerShell examples; synchronized shared renderer instead of independent transports | Launchers, `groovseq`, example projects | Bash/PowerShell composition examples and runtimes pending |
| D01 | Kick/snare/closed hat/open hat/clap/tom/rim procedural voices | `synth.DRUMS` and drum branch | Each drum voice finite/nonempty/deterministic test; implemented |
| D02 | Pitch/pitch envelope/tone-noise/envelopes/cutoff/resonance/saturation/velocity/pan/gain | Drum controls in `synth.render`, CLI | Voice parameter effect/pan/gain tests; implemented |
| D03 | Per-voice parameters/patterns, simultaneous voices, hi-hat choke | `drum_patterns`, `drum_params`, closed-hat jobs | Multi-drum/choke tests; implemented |
| D05 | Unknown per-voice keys rejected and controls validated on every input path | Drum params in preset/project/render API | Resolved: upfront drum validation rejects unknown voice/control and invalid ranges; `test_upfront_drum_validation_and_frame_budget` regression |
| D04 | Clean electronic/dance/breakbeat/experimental presets; no unsupported commercial emulation claim | `presets.BUILTINS['drum']` | Built-in renders/examples pending verification |
| B01 | Monophonic sine/triangle/saw/pulse-square, sub oscillator, mixing/detune/pulse width | Bass oscillator branch in `synth.py` | Oscillator frequency/waveforms/sub tests; implemented |
| B02 | Amp/filter envelopes, stable resonant lowpass, glide with legato, accents, saturation, LFO | `synth.envelope/lowpass/render` | Envelope/frequency/glide/accent/extreme-parameter tests; implemented |
| B03 | Notes/velocity/rests/ties; sub/plucked/acid/aggressive presets | `music.py`, bass built-ins | Pattern/tie tests, preset examples pending |
| B04 | Band limiting/justified alias strategy, extreme filters stable | Harmonic summation below Nyquist, 64-harmonic cap | Oscillator/filter numerical tests; capped low-note timbre limitation documented |
| B05 | All exposed controls act or reject incompatible settings | CLI bass flags versus forced mono/no-arp/no-unison engine | Resolved: lead-only flags removed from bass parser; regression test rejects --arp |
| L01 | Mono/poly, defined limit and oldest stealing, waveforms/unison/detune within bounds | `synth.render` scheduler/oscillators | Polyphony/stealing/mono/glide/unison tests; implemented |
| L02 | Amp/filter ADSR, cutoff/resonance, LFO/vibrato/glide | Shared synth signal flow | Param/envelope/modulation tests; implemented |
| L03 | Chords/arpeggiation/patterns/scales/delay/reverb, pluck/sustained/soft chord/experimental presets | Lead built-ins, `synth`, shared `effects` | Chord/arp tests, effect/tail tests, example render pending |
| L04 | Click avoidance, retrigger/release/overlap explicitly defined | ADSR and 3ms boundary fades, oldest stealing | Boundary click tests; documented approximate legato behavior |
| H01 | groovmix files and/or project tracks | `audio.mix`, project renderer shared mix; CLI file inputs | File/project mixing tests; implemented via project renderer for project tracks |
| H02 | Per-track gain/pan/mute/solo/offset/trim; mismatched rate handling | `audio.mix`, CLI track flags | `test_helpers.py` mixing tests; implemented |
| H03 | Headroom report, optional normalization/limiting, mixdown/stems | `audio.mix`, CLI `--stems` | Resolved: global solo/mute selection and equal-length padding tested; stems explicitly pre-master |
| H04 | groovseq versioned project, shared tempo/meter/swing/timeline, presets/overrides | `projects.py` | Roundtrip/schema/clock/alignment tests; implemented |
| H05 | Repeated sections/variation/deterministic humanization; arrangement/loop/stems | Project section expansion and seed derivation | `test_project_exact_clock_section_variation_and_overrides`; implemented |
| H06 | groovfx gain/fades/filter/saturation/delay/reverb; effect ordering/reusable presets/tails/length | `effects.apply`, CLI fx presets | Effect order/tail/filter tests; preset CLI roundtrip pending |
| H07 | groovplay devices/select/file/loops/application gain/mute/repeat/clean interruption | `devices.py`, CLI play | Device mocks and dispatch regressions passed; physical external |
| H08 | Unsupported formats/missing backends actionable | `devices._backend/diagnose/play` | Missing dependency/check-settings mocks; implemented |
| H09 | groovinfo metadata/duration/rate/channels/peak/RMS/clipping; preset/project JSON | `audio.info`, CLI info | IO/statistics tests; Resolved: preset instrument, version, object structure and unknown keys validated; malformed preset regression cases pass |
| V01 | Appropriate backend; Windows/Linux/macOS actual dependencies/support documented | sounddevice/PortAudio, optional platform adapters | Mocked `test_devices.py`; hardware external |
| V02 | Distinguish synthesis gain/application volume/OS master/mute | CLI `--gain/--volume/--system-volume/--system-unmute` | Device mocks and docs; implemented |
| V03 | Explicit opt-in master controls only; range validation; isolate optional adapters; honest unsupported response | `devices.set_system_volume`, optional extras | Linux/macOS/Windows mocks, unsupported/range failures; implemented |
| V04 | Device diagnostics enumeration/backend/rate; conservative short opt-in tone | CLI `--devices/--diagnose/--test-tone`, devices functions | Tone fades/rate/level and diagnosis mocks; hardware external |
| V05 | Accepted play flags honored consistently | CLI file/tone branches | Resolved: file conversion, tone mute/repeat/master dispatch verified through mock tests |
| Q01 | Float processing/deliberate exports; finite output/stable filters/bounded feedback | `synth.py`, `effects.py`, `audio.py` | Finite/extreme/effect tests; implemented |
| Q02 | Click prevention/envelopes/headroom/clipping; no silent normalization | Explicit normalization/limiting, export clipping report | Boundary/envelope/mixer tests; implemented |
| Q03 | Exact loops versus full tails; explicit repeat-loop tail strategy | CLI `--tail cut/full/wrap`, effects fold tails | Effect length/wrap tests; implemented |
| Q04 | Event placement/duration/swing/boundaries tested | Shared clock, renderer scheduler | Synth timing/boundary tests; implemented |
| Q05 | Latency documented; offline distinct from live; no hard real-time guarantee | Research/spec/site limitations | Offline benchmark 151200 frames in0.329 seconds on local host; no realtime claim; actual host latency unmeasured |
| P01 | Installable console package, bounded dependencies | `pyproject.toml`, nine entry points | Wheel and sdist built; wheel installed into clean venv; local entry-point smoke passed |
| P02 | Windows/Linux/macOS install, uninstall, runtime fallback; accurate failure behavior/no privilege escalation | README/site, launchers | Local clean wheel install passed; uninstall instructions and runtime fallback documented; Windows/macOS remote CI external |
| P03 | Optional playback/system-volume extras preserve offline use | `pyproject.toml` | Dependency mock and offline installation tests pending |
| P04 | Downloadable archives/scripts and honest native/launcher explanation | `scripts/package_downloads.py`, `docs/downloads` | Download bundles regenerated and static local links passed; external served downloads remain to verify |
| E01 | Single hit; one-bar drums; accented gliding bass; lead; chord/arp | `examples/smoke.py`, built-in presets | Resolved: 16-step one-onset pattern; executed example smoke passes |
| E02 | Synced three-instrument groove; multiple sections; stems/final mix; effects existing file | Two JSON example projects, smoke recipes | All 14 offline smoke recipes passed; Bash composition passed |
| E03 | Device selection/playback; Bash/PowerShell composition workflows | `examples/README.md`, launchers/site | Hardware playback external; composition example coverage pending |
| E04 | Several short demo WAVs from committed presets/projects; exact commands/seeds; sensible size | Build/demo process, website audio assets | Four normalized mono 16-kHz PCM16 demos committed with reproduction commands/seeds |
| G01 | Complete Pages site; CDL dark blue/gray styling/typography/technical feel; inspect accessible original assets | `docs/index.html`, assets, research | Browser/responsive/verified CDL link check pending |
| G02 | Explanation; each tool; supported installs; searchable flag reference; copyable Bash/PS commands | `index.html`, `reference.html`, `site.js` | Static links and browser copy/search checks pending |
| G03 | Loop/arrangement tutorials; embedded demos; preset/project/script/package/release downloads | Site tutorials/downloads/audio | Static local download/audio links passed; actual browser controls and external links pending |
| G04 | Architecture/limits/troubleshooting/license/repo and verified CDL links | Site and specs/research | Link verification and browser check pending |
| G05 | Favicon/responsiveness/keyboard/mobile readable; all controls work | SVG, CSS focus/skip link, JS copy/search | Real browser checks pending |
| G06 | Optional browser playground synchronized controls/export with honest parity | `spec/website.md` | Optional omitted; no nonfunctional placeholder |
| G07 | Pages established/suitable Actions deployment; repo-subpath asset paths | `.github/workflows/pages.yml` and relative local links | Local links/build passed; live Pages deployment succeeded |
| T01 | CLI parsing/ranges/incompatibilities/exit codes; patterns and invalid notes | CLI validation and music parser tests | 141-test 0.2.0 matrix run passed; see verification report |
| T02 | Timing/frame counts/alignment; every instrument/helper; seed determinism | Synth/helpers/devices suites | 89-test final full run passed; see verification report |
| T03 | Audio finite/nonempty/formatted; frequency/envelope tolerances | Synth and IO numerical assertions | 89-test final full run passed; see verification report |
| T04 | Polyphony/stealing/glide/accents/choking | `test_synth.py` | 89-test final full run passed; see verification report |
| T05 | Effects stability/tails/clipping/limiting; preset/project roundtrip/schema | Helpers and CLI suites | 89-test final full run passed; see verification report |
| T06 | Mix offset/channel/resampling; overwrite/spaced paths; interruption/dependency errors | Helpers/devices/CLI suites | 89-test final full run passed; see verification report |
| T07 | Bash/PS launchers when runtime available; clean installation; every doc example | Smoke runner, CI, launcher tests | Bash local and PowerShell Windows CI passed; see verification report |
| T08 | Real behavioral assertions, not file-existence-only; mocks and real devices when available | Behavioral numerical suites/device mocks | Tests inspected; physical host unavailable |
| T09 | Lint/tests/package/site checks; OS CI; inspect/fix/rerun actual failures | CI workflow and final verification report | 0.2.0: 141 tests passed across 15 OS/Python matrix jobs; coverage and dependency audit passed; see verification report |
| T10 | Actual browser links/downloads/audio/copy/responsive/playground checks | Website test workflow | Live copy/search/audio/source download passed; desktop checked; mobile viewport unavailable; playground omitted |
| C01 | Nine stages through audit/commit/push/publication, no premature completion | Work record and verification report | Repository published and live Pages checked; see verification report |
| C02 | Final report tools/install/smoke/test results/performed/unperformed platform checks/limits/blockers/verified links/commit/release | `docs/verification.md` | Must be generated from actual evidence |
| C03 | Concise final response built/repo/site/download/install/groove/tests/limits; no unsupported complete/published claims | Final response | Pending final handoff |
| LOG01 | Additional request: opt-in troubleshooting log flag throughout project | `diagnostics.py`, all-tool `--log-file/--log-level/--log-format`; `spec/cli.md` | CLI text/JSON logging, append, exception/stdout/lifecycle regressions included in passing local suites |

## 0.2.0 composition feature traceability

| ID | Requirement / feature | Specification / implementation | Verification |
|---|---|---|---|
| F01 | Deterministic pattern mutation without changing note identity | `spec/variation.md`, `variation.py`, synth integration | `test_variation.py`; seeded equality/difference, density, bounds, ghost/fill behavior; included in 141-test matrix |
| F02 | Project automation lanes continuing across arrangement time | `spec/automation.md`, `automation.py`, `projects.py` | `test_automation.py`; linear/step interpolation, gain/pan/cutoff/saturation, section continuity and schema failures |
| F03 | Standard MIDI File import/export without realtime MIDI hardware | `spec/midi.md`, `midi.py`, `groovmidi` entry point and launchers | `test_midi.py`; chords, tempo rejection, percussion boundary, sections/transpose, GM drums, overwrite and CLI flow |
| F04 | New controls use shared persisted/CLI validation | `validation.py`, `presets.py`, CLI parser | Variation/density/ghost/fill ranges exercised by unit and full matrix tests |
| F05 | New command participates in docs/packaging/platform workflows | `build_reference.py`, Bash/PowerShell launchers, README, CI | nine-tool reference generation and packaging passed; Windows launcher matrix passed |
| F06 | Cross-platform and dependency quality gates | expanded GitHub Actions matrix, pytest-cov, pip-audit | run 37397677493: all 15 matrix jobs, coverage and dependency audit succeeded |

## Final audit resolutions and evidence

All material audit findings were corrected: nested drum schemas/ranges validate before allocation; track/preset humanization persists unless a global override exists; cumulative section clocks prevent rounding drift; CLI presets cannot supersede explicit voice/pattern flags; unknown effects properties reject; bass rejects lead-only flags; device dispatch honors conversions/mute/repeat; stems are globally selected, padded and explicitly pre-master. Relevant regressions are in test_synth.py, test_cli.py, test_dispatch.py and test_helpers.py. Final executed outcomes and remaining external hardware/browser/publication boundaries are recorded in docs/verification.md. Optional playground omitted by design, as permitted in the request.
