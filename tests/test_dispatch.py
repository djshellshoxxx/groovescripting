"""Device dispatch and arrangement edge behavior not covered by subprocess renders."""

import io
import json
import sys

import numpy as np
import pytest
import soundfile as sf

from groovescripting import cli, devices, projects
from groovescripting.music import beat_frame


def test_play_dispatch_converts_and_honors_mute(tmp_path, monkeypatch):
    path = tmp_path / "test.wav"
    sf.write(path, np.sin(np.arange(800) * 0.1) * 0.1, 8000)
    seen = {}

    def play(data, sr, **options):
        seen.update(data=data, sr=sr, options=options)

    monkeypatch.setattr(devices, "play", play)
    assert (
        cli.run(
            "groovplay", [str(path), "--sample-rate", "16000", "--channels", "2", "--mute", "--repeat", "3"]
        )
        == 0
    )
    assert seen["data"].shape == (1600, 2) and seen["sr"] == 16000
    assert seen["options"]["mute"] and seen["options"]["repeat"] == 3


def test_testtone_dispatch_explicit_master_and_mute(monkeypatch):
    calls = []
    monkeypatch.setattr(devices, "set_system_volume", lambda v, u: calls.append(("master", v, u)))
    monkeypatch.setattr(devices, "test_tone", lambda *a, **kw: calls.append(("tone", a, kw)))
    assert (
        cli.run(
            "groovplay",
            ["--test-tone", "--mute", "--system-volume", ".2", "--system-unmute", "--repeat", "2"],
        )
        == 0
    )
    assert calls[0] == ("master", 0.2, True)
    assert calls[1][2]["volume"] == 0 and calls[1][2]["repeat"] == 2


def test_project_rounding_does_not_accumulate_and_humanization_precedence():
    seen = []
    p = {
        "version": 1,
        "bpm": 240000,
        "beats": 1,
        "bars": 1,
        "sample_rate": 10000,
        "channels": 1,
        "tracks": [{"name": "B", "instrument": "bass", "preset": "sub", "params": {"humanize": 0.02}}],
        "sections": [{"bars": 1, "repeat": 100}],
    }

    def render(kind, options):
        seen.append(options)
        return np.zeros((3, 1))

    result, _, _ = projects.render_project(p, render)
    assert len(result) == beat_frame(100, p["bpm"], 10000) == 250
    assert all(o["humanize"] == 0.02 for o in seen)
    p["humanize"] = 0.01
    projects.render_project(p, render)
    assert seen[-1]["humanize"] == 0.01


def test_project_tail_cut_full_wrap():
    from groovescripting.synth import render

    p = {
        "version": 1,
        "bpm": 240,
        "beats": 1,
        "bars": 1,
        "sample_rate": 8000,
        "channels": 1,
        "tracks": [{"name": "B", "instrument": "bass", "pattern": "C2:1", "params": {"release": 0.2}}],
    }
    cut, _, _ = projects.render_project(p, render, tail="cut")
    full, _, _ = projects.render_project(p, render, tail="full")
    wrap, _, _ = projects.render_project(p, render, tail="wrap")
    assert len(cut) == len(wrap) == 2000 and len(full) == 3600
    assert np.max(np.abs(full[2000:])) > 0.001
    np.testing.assert_allclose(wrap[:1600], full[:1600] + full[2000:], atol=1e-10)
    with pytest.raises(ValueError):
        projects.render_project(p, render, tail="unknown")


def test_sequence_cli_clock_overrides(tmp_path):
    path = tmp_path / "clock.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "bpm": 120,
                "bars": 1,
                "beats": 4,
                "sample_rate": 8000,
                "channels": 1,
                "tracks": [{"name": "Bass", "instrument": "bass", "pattern": "C2"}],
            }
        )
    )
    out = tmp_path / "clock.wav"
    assert cli.run("groovseq", [str(path), "--bpm", "240", "--beats", "1", "--output", str(out)]) == 0
    assert sf.info(out).frames == 2000


def test_high_cutoff_effect_preset_inspection_is_rate_independent(tmp_path, capsys):
    p = tmp_path / "effects.json"
    data = {
        "version": 1,
        "effects": [{"type": "lowpass", "hz": 12000}, {"type": "delay", "seconds": 30, "repeats": 64}],
    }
    p.write_text(json.dumps(data))
    assert cli.run("groovinfo", [str(p), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == data


def test_testtone_stereo_and_diagnostic_channels(monkeypatch):
    seen = []
    monkeypatch.setattr(devices, "play", lambda data, sr, **kw: seen.append(data))
    devices.test_tone(sample_rate=8000, channels=2)
    assert seen[0].shape == (4000, 2)
    np.testing.assert_array_equal(seen[0][:, 0], seen[0][:, 1])

    class Backend:
        def query_devices(self, *args):
            return {"name": "mock"}

        def check_output_settings(self, **kw):
            seen.append(kw)

    monkeypatch.setattr(devices, "_backend", lambda: Backend())
    assert devices.diagnose(8000, channels=1)["supported"]
    assert seen[-1]["channels"] == 1


def test_json_status_survives_windows_legacy_console(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)
    cli.emit({"path": "groove 音 ü.wav"}, as_json=True)
    stream.flush()
    encoded = raw.getvalue()
    assert encoded.isascii()
    assert json.loads(encoded)["path"] == "groove 音 ü.wav"
