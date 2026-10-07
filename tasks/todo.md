# Verification checklist
- [x] Specifications before implementations
- [x] Synth and musical clock tests
- [x] Helpers and arrangement tests
- [x] CLI, presets and logging tests
- [x] Device adapter mock tests
- [x] Clean installation and examples
- [x] Website assets and browser checks
- [x] Final requirements traceability audit
- [x] Repository publication and CI checks

## Requested musical developer tools (2026-10-06)

Selected from the product differentiation review. All selected tools are specified and implemented in 0.3.0.

- [x] Specify groovlint, the quickest selected feature to implement: spec/groovlint.md
- [x] Implement groovlint using existing schema validation and audio inspection.
- [x] Specify groovdebug, the most distinctive selected feature: spec/groovdebug.md
- [x] Build the event trace model and deterministic debugger required by groovdebug.

### Remaining selected concepts

- [x] Specify and implement groovtest, a reusable musical assertion runner: spec/groovtest.md
- [x] Specify and implement event provenance, recording each event's source and transformations: spec/provenance.md
- [x] Specify and implement groovtime, deterministic inspection/rendering of prior composition states: spec/groovtime.md
- [x] Specify and implement semantic groovmerge, combining selected musical dimensions from branches: spec/groovmerge.md

### Suggested dependency order

1. groovlint can ship independently.
2. Stabilize event identity, event trace schema, and provenance.
3. Build groovdebug and groovtest on the trace/event contracts.
4. Add groovtime using persisted deterministic transformation history.
5. Add semantic groovmerge after shared event representation and conflict rules exist.

## Standalone binaries (0.3.0)

- [x] Release workflow builds PyInstaller executables for Windows (.exe) and Linux and attaches them to GitHub Releases: .github/workflows/release.yml
