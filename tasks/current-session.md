# Integrated verification and delivery audit

Base revision: 027ea70. Integration owner: lead. Workspace: /workspace/groovescripting.

## Brief and acceptance
Preserve the existing 0.4.1 product and finish reproducible correctness and delivery gaps found against its specifications. No speculative new features or public release without authority. Acceptance: baseline and final full tests, Ruff, source packaging, documented offline recipes, regression tests for any corrections, independent review. Physical audio and native non-Linux builds require external runners/hardware.

## Tasks
| ID | Owner | Status | Scope / owned files | Dependencies | Verification / latest handoff |
| --- | --- | --- | --- | --- | --- |
| GS-01 | audit worker | DONE | Read-only spec/code/release gap review; no edits | none | Reproducible findings with evidence |
| GS-02 | lead | DONE | Environment setup and baseline; work/ only | none | Full pytest and Ruff; system Python lacks pytest, isolated environment installing |
| GS-03 | lead | DONE | Fix confirmed gaps; specific files assigned after discovery | GS-01, GS-02 | Failing reproduction then regression pass |
| GS-04 | lead | DONE | Integration, packaging, offline smoke, docs/verification.md | GS-03 | Full tests, build and independent review |

All tasks exclude unrelated repositories, public publication and physical device assertions. Existing module specifications under spec/ remain authoritative contracts. No API/schema change planned. All work integrates in the existing clean delivery workspace; concurrent worker is read-only.

## Decisions and resources
- Use one existing cloud environment; no new paid capacity required.
- One read-only audit worker; lead owns all mutations.
- Development dependencies live under /workspace/work/groovescripting-venv, outside the repository.
- Release publication remains incomplete in existing task history; inspect available evidence before changing status.

## Final integration and handoff
- GS-01: audit identified five MIDI import correctness gaps; seven generated regressions reproduced them.
- GS-02: pre-fix full suite passed 272 existing tests and failed the seven added regressions (144.13s). Dependencies installed successfully through the configured proxy with network permission.
- GS-03: lead owns midi.py, test_midi.py and spec/midi.md; all five defects corrected without schema/API changes. Focused suite PASS: 14 tests.
- GS-04: final full suite PASS: 279 tests in 144.20s. Ruff PASS, git diff --check PASS, documented offline examples PASS, wheel/sdist build PASS, installed-wheel MIDI help PASS.
- GS-05: audit worker independently reviewed the implementation and reran focused tests/Ruff; DONE, no actionable findings. Read-only review task owns no files and depends on GS-03.
- Delivery: uncommitted integrated changes based on 027ea7072ff1d0e0634e5c8fda45a283b74b8ecb. Review changes in the delivery workspace; distributions are in /workspace/work/groovescripting-dist. The configured chat output path is unavailable on this cloud host (read-only /codex filesystem). No public release or deployment performed.
- Retained resources: existing cloud environment and /workspace/work/groovescripting-venv (lead-owned development workspace). Audit worker finished; no extra instances.
- Remaining external work: run native CI on all four release targets and verify physical playback/OS volume. Obtain release authority before public publication. Existing tasks/verification.md release checkbox remains incomplete.
