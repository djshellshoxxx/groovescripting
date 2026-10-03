# GrooveScripting implementation plan

Build eight commands around a shared Python engine. NumPy vectorizes oscillators and envelopes; SciPy provides stable filtering and resampling; SoundFile provides WAV/FLAC exports. Playback and master-volume dependencies remain optional. Float64 internal buffers, exact frame clocks and seeded randomization support scripted composition. Logs are opt-in and shared across every command.

## Ordered work
1. Inspect empty repository, research primary dependency documentation, write module specifications. Verify contracts and parameter defaults before implementation.
2. Implement musical clock and three instruments. Acceptance: deterministic finite synthesis with exact frames, expressive patterns and voice lifecycle tests.
3. Implement effects, mixing and project arrangements. Acceptance: sample conversion, stems and shared track alignment verified numerically.
4. Implement CLI, presets and opt-in logs. Acceptance: precedence, invalid flags, export/play workflows, logged failures and all entry points tested.
5. Implement optional devices. Acceptance: no offline playback dependency, mocked volume controls, interruption tests and explicit hardware limitations.
6. Package launchers and examples. Acceptance: clean environment install, runnable documented commands and downloadable archives.
7. Build Pages documentation. Acceptance: local asset/link checks and real browser inspection when available.
8. Audit requirements, run test/lint/build checks, commit and publish through authorized GitHub connector.

## Ownership
Engine agent owns music/synth/spec/tests. Helpers agent owns audio/effects/projects/spec/tests. Device agent owns adapters/spec/tests. Documentation agent owns website/examples/scripts/workflows. Main agent owns CLI, presets, diagnostics, integration, packaging and final audit.

## Risks
Hardware is unavailable: mock adapters and report playback unverified. Git transport authentication is unavailable: publish through GitHub contents/Git data API. Master volume is platform-specific and always opt-in. DSP is offline with no hard realtime guarantee.
