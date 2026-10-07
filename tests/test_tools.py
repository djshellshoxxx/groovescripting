"""Trace, predicate grammar, groovlint, groovdebug, groovtest, groovtime and groovmerge behavior."""

import copy
import hashlib
import io
import json
import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf

from groovescripting import debug, expr, lint, merge, musictest, projects, synth, timeline, trace


def project(**extra):
    base = {
        "version": 1,
        "bpm": 120,
        "bars": 2,
        "sample_rate": 8000,
        "channels": 2,
        "seed": 7,
        "humanize": 0.002,
        "velocity_humanize": 0.1,
        "swing": 0.1,
        "tracks": [
            {
                "name": "Drums",
                "instrument": "drum",
                "params": {"drum_patterns": {"kick": "x...x...", "closed_hat": "xxxxxxxx"}},
            },
            {
                "name": "Bass",
                "instrument": "bass",
                "pattern": "C2:0.25:1:0.5 . G2 . C2 . Eb2 .",
                "offset": 0.5,
            },
            {
                "name": "Lead",
                "instrument": "lead",
                "pattern": "C4+E4+G4 . . .",
                "params": {"arp": "up", "arp_rate": 0.25},
            },
        ],
        "sections": [
            {"name": "A", "bars": 1, "repeat": 2},
            {"name": "B", "bars": 1, "tracks": {"Bass": {"pattern": "F2 . . ."}}, "variation": 3},
        ],
    }
    base.update(extra)
    return base


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# trace -------------------------------------------------------------------------------------------


def test_trace_is_deterministic_and_fingerprint_tracks_inputs():
    a = trace.collect(project())
    assert a == trace.collect(project())
    header, records = a
    assert header["event_count"] == len(records) > 20
    assert {r["track"] for r in records} == {"Drums", "Bass", "Lead"}
    frames = [r["timing"]["frame"] for r in records if r["timing"]["frame"] is not None]
    assert frames == sorted(frames)
    assert len({r["event_id"] for r in records}) == len(records)
    assert trace.collect(project(), seed=8)[0]["run_fingerprint"] != header["run_fingerprint"]
    assert trace.fingerprint(project(bpm=121)) != trace.fingerprint(project())


def test_trace_records_provenance_and_decisions():
    _, records = trace.collect(project())
    bass_b = [r for r in records if r["track"] == "Bass" and r["source"]["section"] == "B"]
    assert bass_b and all(r["source"]["pointer"] == "/sections/1/tracks/Bass/pattern" for r in bass_b)
    assert records[0]["source"]["pointer"].startswith("/tracks/")
    kinds = {d["kind"] for r in records for d in r["decisions"]}
    assert {"probability", "velocity_humanize", "swing", "humanize"} <= kinds
    lead = [r for r in records if r["track"] == "Lead"]
    assert any("arp" not in r and r["notes"] for r in lead)
    rejected = [r for r in records if not r["accepted"]]
    assert all(r["timing"]["frame"] is None or r["decisions"][-1]["kind"] == "window" for r in rejected)


def test_tracing_does_not_change_rendered_audio():
    p = project()
    traced = []

    def render(instrument, params):
        sink = []
        synth.render(instrument, params, trace=sink)
        traced.append(len(sink))
        return synth.render(instrument, params)

    with_trace, _, _ = projects.render_project(p, render)
    plain, _, _ = projects.render_project(p, synth.render)
    assert traced and np.array_equal(with_trace, plain)


def test_trace_limits_and_jsonl_roundtrip(tmp_path):
    with pytest.raises(ValueError, match="max-events"):
        trace.collect(project(), max_events=3)
    header, records = trace.collect(project())
    path = trace.write_jsonl(tmp_path / "t.jsonl", header, records)
    assert trace.read_jsonl(path) == (header, records)
    with pytest.raises(FileExistsError):
        trace.write_jsonl(path, header, records)
    assert [p.name for p in tmp_path.iterdir()] == ["t.jsonl"]


# predicate grammar -------------------------------------------------------------------------------


def test_expression_grammar_and_rejections():
    record = trace.collect(project())[1][0]
    assert expr.compile_expression(f'track == "{record["track"]}" and bar >= 1')(record)
    assert expr.compile_expression("not (bar > 1 or accepted == false)")(record) is (record["accepted"])
    for bad, message in (
        ("__import__('os')", "unknown field"),
        ("bar >", "expected"),
        ("track < 3", "quoted string"),
        ("track > 'a'", "only == and !="),
        ("bar == 1 extra", "unexpected"),
        ("bar == 1 ;", "column"),
    ):
        with pytest.raises(expr.ExpressionError, match=message):
            expr.compile_expression(bad)


# groovdebug --------------------------------------------------------------------------------------


def test_debug_json_breakpoints_and_commands(tmp_path):
    path = write(tmp_path / "p.json", project())
    before = path.read_bytes()
    out = io.StringIO()
    assert debug.cli([str(path), "--break", "2", "--track", "Lead", "--format", "json"], stdout=out) == 0
    envelope = json.loads(out.getvalue())
    assert envelope["stops"] and all(r["bar"] == 2 or r["track"] == "Lead" for r in envelope["records"])
    event = envelope["records"][0]["event_id"]
    commands = write(tmp_path / "cmds.txt", {}).with_suffix(".txt")
    commands.write_text(f"c\nwhy {event}\ninspect {event}\nbar 2\nevents 1-2\nseed\nfingerprint\nhelp\nq\n")
    out = io.StringIO()
    trace_out = tmp_path / "trace.jsonl"
    assert (
        debug.cli(
            [str(path), "--break", "2", "--commands", str(commands), "--trace-out", str(trace_out)],
            stdout=out,
        )
        == 0
    )
    text = out.getvalue()
    assert "Stopped (bar 2)" in text and "probability roll" in text and "not captured" in text
    assert trace_out.exists() and path.read_bytes() == before
    assert (
        debug.cli(
            [str(path), "--commands", str(commands), "--trace-out", str(trace_out)], stdout=io.StringIO()
        )
        == 2
    )


def test_debug_rejects_non_tty_and_bad_expressions(tmp_path):
    path = write(tmp_path / "p.json", project())
    assert debug.cli([str(path)], stdin=io.StringIO(""), stdout=io.StringIO()) == 2
    assert debug.cli([str(path), "--where", "eval == 1", "--format", "json"], stdout=io.StringIO()) == 2


# groovlint ---------------------------------------------------------------------------------------


def lint_json(*args):
    out = io.StringIO()
    import contextlib

    with contextlib.redirect_stdout(out):
        code = lint.cli([*map(str, args), "--format", "json"])
    return code, json.loads(out.getvalue()) if out.getvalue() else None


def test_lint_project_rules(tmp_path):
    p = project()
    p["tracks"][2]["params"].update(vibrato_rate=4, unison_detune=10)
    p["tracks"][1]["mute"] = True
    p["tracks"][2]["params"]["voices"] = 32
    code, report = lint_json(write(tmp_path / "p.json", p))
    ids = [f["rule_id"] for f in report["findings"]]
    assert code == 1 or code == 0
    assert ids.count("PRJ003") == 3 and "PRJ004" in ids
    assert report["findings"] == sorted(report["findings"], key=lint._sort_key)
    assert lint_json(write(tmp_path / "p.json", p), "--strict")[0] == 1
    assert lint_json(write(tmp_path / "p.json", p), "--fail-on", "off")[0] == 0
    assert lint_json(write(tmp_path / "p.json", p), "--only", "PRJ004")[1]["summary"]["notes"] == 0
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    code, report = lint_json(bad)
    assert code == 2 and report["findings"][0]["rule_id"] == "PRJ001"
    assert lint.cli([str(bad), "--only", "PRJ001", "--ignore", "PRJ002"]) == 2


def test_lint_frame_budget():
    data = project(sample_rate=192000, bpm=1, sections=[{"name": "long", "bars": 64}])
    findings, _ = lint.lint_project(data)
    assert any(f["rule_id"] == "PRJ002" for f in findings)


@pytest.mark.parametrize(
    "signal, rule",
    [
        (np.zeros((800, 2)), "AUD002"),
        (np.full((800, 2), 0.05), "AUD003"),
        (np.column_stack([np.ones(800), np.ones(800)]) * 1.0, "AUD001"),
        (np.column_stack([np.sin(np.arange(800) * 0.3) * 0.5, np.zeros(800)]), "AUD005"),
    ],
)
def test_lint_audio_rules(tmp_path, signal, rule):
    path = tmp_path / "a.wav"
    sf.write(path, signal, 8000, subtype="FLOAT")
    assert rule in [f["rule_id"] for f in lint.lint_audio(path, lint.load_thresholds())[0]]


def test_lint_boundary_and_targets(tmp_path):
    path = tmp_path / "a.wav"
    sf.write(path, np.full(800, 0.5) * np.r_[np.ones(799), 1], 8000)
    profile = tmp_path / "t.json"
    profile.write_text(json.dumps({"version": 1, "targets": {"sample_rate_hz": 44100}}))
    found = [f["rule_id"] for f in lint.lint_audio(path, lint.load_thresholds(profile))[0]]
    assert "AUD004" in found and "AUD006" in found
    profile.write_text(json.dumps({"version": 1, "audio": {"dc_offset_peak": 7}}))
    with pytest.raises(lint.LintInputError):
        lint.load_thresholds(profile)
    assert lint.cli([str(path), "--audio", str(path)]) == 2


# groovtest ---------------------------------------------------------------------------------------


def test_musical_assertions(tmp_path):
    write(tmp_path / "song.json", project())
    fingerprint = trace.collect(project())[0]["run_fingerprint"]
    suite = write(
        tmp_path / "suite.json",
        {
            "version": 1,
            "project": "song.json",
            "tests": [
                {"name": "kicks", "where": 'voice == "kick" and accepted == true', "count": {"min": 4}},
                {"name": "bass range", "where": 'track == "Bass"', "all": "note >= 24 and note <= 60"},
                {"name": "no loud hats", "where": 'voice == "closed_hat"', "none": "velocity > 1"},
                {"name": "pinned", "fingerprint": fingerprint},
            ],
        },
    )
    assert musictest.cli([str(suite)]) == 0
    failing = json.loads(suite.read_text())
    failing["tests"][1]["all"] = "note > 100"
    write(suite, failing)
    assert musictest.cli([str(suite)]) == 1
    failing["tests"][1]["all"] = "nope == 1"
    write(suite, failing)
    assert musictest.cli([str(suite)]) == 2


# groovtime ---------------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git unavailable")
def test_time_history_show_and_diff(tmp_path, capsys):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    path = write(tmp_path / "song.json", project())
    git("add", "song.json")
    git("commit", "-qm", "first")
    changed = project()
    changed["tracks"][1]["pattern"] = "C2 . . . C2 . . ."
    write(path, changed)
    assert timeline.cli(["log", str(path), "--format", "json"]) == 0
    log = json.loads(capsys.readouterr().out)
    assert len(log) == 1 and log[0]["valid"]
    assert timeline.cli(["show", str(path), "--at", "HEAD"]) == 0
    assert json.loads(capsys.readouterr().out)["tracks"][1]["pattern"] == project()["tracks"][1]["pattern"]
    result = timeline.diff(timeline.state(path, "HEAD"), timeline.state(path))
    assert result["removed"] and all(r["track"] == "Bass" for r in result["removed"])
    assert timeline.cli(["show", str(path), "--at=--output=x"]) == 2
    out = tmp_path / "old.wav"
    assert timeline.cli(["render", str(path), "--at", "HEAD", "--output", str(out)]) == 0
    assert sf.info(out).frames > 0


# groovmerge --------------------------------------------------------------------------------------


def test_semantic_merge_combines_dimensions_and_reports_conflicts(tmp_path):
    base = project()
    ours = copy.deepcopy(base)
    theirs = copy.deepcopy(base)
    ours["tracks"][1]["pattern"] = "C2 . . ."
    theirs["tracks"][1].setdefault("params", {})["cutoff"] = 400
    theirs["bpm"] = 128
    merged, report = merge.merge(base, ours, theirs)
    assert not report["conflicts"]
    assert merged["bpm"] == 128 and merged["tracks"][1]["pattern"] == "C2 . . ."
    assert merged["tracks"][1]["params"]["cutoff"] == 400
    theirs["tracks"][1]["pattern"] = "G2 . . ."
    merged, report = merge.merge(base, ours, theirs)
    assert merged is None and report["conflicts"][0]["dimension"] == "track:Bass.pattern"
    merged, _ = merge.merge(base, ours, theirs, takes=[("track:Bass", "theirs")])
    assert merged["tracks"][1]["pattern"] == "G2 . . ."
    removed = copy.deepcopy(base)
    removed["tracks"].pop(2)
    merged, report = merge.merge(base, ours, removed)
    assert merged is not None and [t["name"] for t in merged["tracks"]] == ["Drums", "Bass"]
    edited = copy.deepcopy(base)
    edited["tracks"][2]["pattern"] = "D4 . . ."
    merged, report = merge.merge(base, edited, removed)
    assert merged is None and any(c["dimension"] == "track:Lead" for c in report["conflicts"])
    paths = [write(tmp_path / f"{n}.json", d) for n, d in (("b", base), ("o", ours), ("t", theirs))]
    out = tmp_path / "m.json"
    assert merge.cli([*map(str, paths), "--output", str(out)]) == 1 and not out.exists()
    assert merge.cli([*map(str, paths), "--output", str(out), "--prefer", "ours"]) == 0
    assert projects.load(out)["tracks"][1]["pattern"] == "C2 . . ."
    assert (
        hashlib.sha256(paths[0].read_bytes()).hexdigest()
        == hashlib.sha256(json.dumps(base).encode()).hexdigest()
    )
