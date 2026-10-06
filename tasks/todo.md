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

Selected from the product differentiation review. Specs are planning documents; none of these features is implemented yet.

- [x] Specify groovlint, the quickest selected feature to implement: spec/groovlint.md
- [ ] Implement groovlint using existing schema validation and audio inspection.
- [x] Specify groovdebug, the most distinctive selected feature: spec/groovdebug.md
- [ ] Build the event trace model and deterministic debugger required by groovdebug.

### Remaining selected concepts

- [ ] Specify and implement groovtest, a reusable musical assertion runner.
- [ ] Specify and implement event provenance, recording each event's source and transformations.
- [ ] Specify and implement groovtime, deterministic inspection/rendering of prior composition states.
- [ ] Specify and implement semantic groovmerge, combining selected musical dimensions from branches.

### Suggested dependency order

1. groovlint can ship independently.
2. Stabilize event identity, event trace schema, and provenance.
3. Build groovdebug and groovtest on the trace/event contracts.
4. Add groovtime using persisted deterministic transformation history.
5. Add semantic groovmerge after shared event representation and conflict rules exist.
