"""Subprocess contracts for rendering, presets and troubleshooting."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
TOOLS = [
    "groovdrm",
    "groovbss",
    "groovld",
    "groovseq",
    "groovmix",
    "groovfx",
    "groovplay",
    "groovinfo",
    "groovmidi",
    "groovlint",
    "groovdebug",
    "groovtest",
    "groovtime",
    "groovmerge",
]


def cli(*args, ok=True):
    result = subprocess.run(
        [sys.executable, "-m", "groovescripting", *map(str, args)],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT)),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if ok:
        assert result.returncode == 0, result.stderr
    return result


def audio(path, frames=None):
    data, sr = sf.read(path, always_2d=True)
    assert sr == 8000 and data.shape[1] == 1 and np.isfinite(data).all()
    assert np.max(np.abs(data)) > 0
    if frames is not None:
        assert len(data) == frames
    return data


def render(tool, path, *extra):
    return cli(
        tool,
        "--sample-rate",
        8000,
        "--channels",
        1,
        "--bpm",
        240,
        "--bars",
        1,
        "--beats",
        1,
        "--output",
        path,
        "--json",
        *extra,
    )


@pytest.mark.parametrize("tool", TOOLS)
def test_help_version(tool):
    assert "--log-file" in cli(tool, "--help").stdout
    assert cli(tool, "--version").stdout.strip() == cli("--version").stdout.strip()


@pytest.mark.parametrize("tool", TOOLS[:3])
def test_render_audio(tool, tmp_path):
    out = tmp_path / "audio.wav"
    status = json.loads(render(tool, out).stdout)
    assert status["frames"] == 2000 and status["sample_rate"] == 8000
    audio(out, 2000)


@pytest.mark.parametrize("tool", TOOLS[:3])
def test_builtin_presets_precedence_roundtrip(tool, tmp_path):
    names = json.loads(cli(tool, "--list-presets", "--json").stdout)
    assert len(names) >= 4
    for i, name in enumerate(names):
        inspected = json.loads(cli(tool, "--preset", name, "--inspect-preset", "--json").stdout)
        assert inspected["version"] == 1 and inspected["name"] == name
        saved = tmp_path / f"preset {i}.json"
        first = tmp_path / f"first{i}.wav"
        second = tmp_path / f"second{i}.wav"
        render(tool, first, "--preset", name, "--gain", 0.12, "--save-preset", saved)
        params = json.loads(saved.read_text())["params"]
        assert params["gain"] == 0.12 and params["bpm"] == 240
        render(tool, second, "--preset", saved)
        np.testing.assert_array_equal(audio(first, 2000), audio(second, 2000))


@pytest.mark.parametrize("fmt", ["text", "json"])
@pytest.mark.parametrize("level", ["debug", "info", "warning", "error"])
def test_logging_append_levels_clean_stdout(fmt, level, tmp_path):
    log = tmp_path / "troubleshooting ü.log"
    for i in range(2):
        result = render(
            "groovbss", tmp_path / f"{i}.wav", "--log-file", log, "--log-format", fmt, "--log-level", level
        )
        assert json.loads(result.stdout)["frames"] == 2000
    contents = log.read_text(encoding="utf-8")
    if level in ("warning", "error"):
        assert contents == ""
    else:
        assert (
            contents.count("Starting groovbss") == 2
            and contents.count("Completed groovbss") == 2
            and contents.count("Rendered frames=") >= 2
        )
        if fmt == "json":
            records = [json.loads(line) for line in contents.splitlines()]
            assert all({"timestamp", "level", "logger", "message"} <= set(row) for row in records)
            assert any(row["level"] == "debug" for row in records) == (level == "debug")
        else:
            assert (" DEBUG " in contents) == (level == "debug")


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_invalid_cli_schema_logged_stacktrace(tmp_path, fmt):
    log = tmp_path / "errors.jsonl"
    result = cli("groovbss", "--bpm", "nan", "--log-file", log, "--log-format", fmt, ok=False)
    assert result.returncode == 2 and not result.stdout
    contents = log.read_text()
    assert "Argument error" in contents
    project = tmp_path / "invalid.json"
    project.write_text(json.dumps({"version": 1, "tracks": [], "unexpected": True}))
    result = cli("groovseq", project, "--log-file", log, "--log-format", fmt, ok=False)
    assert result.returncode == 2 and not result.stdout
    contents = log.read_text()
    if fmt == "json":
        rows = [json.loads(line) for line in contents.splitlines()]
        assert any(
            "Traceback" in row.get("exception", "") and "ValueError" in row["exception"] for row in rows
        )
    else:
        assert "Traceback" in contents and "ValueError" in contents


def test_paths_overwrite_missing_log_directory(tmp_path):
    path = tmp_path / "groove 音 ü.wav"
    render("groovld", path)
    original = path.read_bytes()
    failed = cli("groovld", "--output", path, ok=False)
    assert failed.returncode == 1 and path.read_bytes() == original
    render("groovld", path, "--overwrite")
    audio(path, 2000)
    failed = cli(
        "groovld",
        "--log-file",
        tmp_path / "missing" / "log.txt",
        "--output",
        tmp_path / "absent.wav",
        ok=False,
    )
    assert failed.returncode == 1 and "No such file" in failed.stderr
    assert not (tmp_path / "absent.wav").exists()
    failed = cli("groovld", "--log-level", "debug", ok=False)
    assert failed.returncode == 2 and "require --log-file" in failed.stderr


def test_explicit_frequency_notes_events_and_tails(tmp_path):
    events = tmp_path / "events.json"
    events.write_text(
        json.dumps([{"beat": 0, "duration": 1, "notes": ["A4"], "velocity": 1, "probability": 1}])
    )
    arrays = []
    for mode in ("cut", "full", "wrap"):
        path = tmp_path / f"{mode}.wav"
        render("groovld", path, "--frequency", 440, "--waveform", "sine", "--release", 0.2, "--tail", mode)
        arrays.append(audio(path))
    assert len(arrays[0]) == len(arrays[2]) == 2000 and len(arrays[1]) == 3600
    assert np.max(np.abs(arrays[1][2000:])) > 0 and not np.array_equal(arrays[0], arrays[2])
    event_path = tmp_path / "events.wav"
    render("groovld", event_path, "--events", events, "--waveform", "sine", "--release", 0.2)
    np.testing.assert_array_equal(audio(event_path), arrays[0])
    signal = arrays[0][400:1800, 0]
    dominant = np.fft.rfftfreq(len(signal), 1 / 8000)[np.argmax(np.abs(np.fft.rfft(signal)))]
    assert abs(dominant - 440) < 8


def test_arrangement_stems_mix_fx_info(tmp_path):
    project = {
        "version": 1,
        "bpm": 240,
        "beats": 1,
        "bars": 1,
        "sample_rate": 8000,
        "channels": 1,
        "tracks": [
            {"name": "Bass", "instrument": "bass", "pattern": "C2", "gain": 0.3},
            {"name": "Lead", "instrument": "lead", "pattern": "C4", "gain": 0.2},
        ],
        "sections": [{"bars": 1, "tracks": {"Lead": {"mute": True}}}, {"bars": 1, "repeat": 2}],
    }
    path = tmp_path / "arrangement.json"
    path.write_text(json.dumps(project))
    stems = tmp_path / "stems"
    out = tmp_path / "arrangement.wav"
    cli("groovseq", path, "--output", out, "--stems", stems, "--subtype", "FLOAT", "--json")
    result = audio(out, 6000)
    bass = audio(stems / "Bass.wav", 6000)
    lead = audio(stems / "Lead.wav", 6000)
    assert not lead[:2000].any() and np.max(np.abs(lead[2000:])) > 0
    np.testing.assert_allclose(result, bass + lead, atol=7e-5)
    assert json.loads(cli("groovinfo", path, "--json").stdout) == project
    info = json.loads(cli("groovinfo", out, "--json").stdout)
    assert info["frames"] == 6000 and info["sample_rate"] == 8000
    mixed = tmp_path / "mixed.wav"
    cli(
        "groovmix",
        stems / "Bass.wav",
        stems / "Lead.wav",
        "--output",
        mixed,
        "--sample-rate",
        8000,
        "--channels",
        1,
        "--subtype",
        "FLOAT",
        "--stems",
        tmp_path / "mix stems",
    )
    np.testing.assert_allclose(audio(mixed, 6000), result, atol=7e-5)
    fx = tmp_path / "fx.wav"
    cli(
        "groovfx",
        mixed,
        "--output",
        fx,
        "--effect",
        '{"type":"gain","db":-6.020599913279624}',
        "--subtype",
        "FLOAT",
    )
    np.testing.assert_allclose(audio(fx, 6000), audio(mixed) * 0.5, atol=1e-6)


def test_offline_render_does_not_import_sounddevice(tmp_path):
    (tmp_path / "sounddevice.py").write_text('raise RuntimeError("offline imported sounddevice")\n')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tmp_path), str(ROOT)]))
    out = tmp_path / "offline.wav"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "groovescripting",
            "groovbss",
            "--frequency",
            "110",
            "--sample-rate",
            "8000",
            "--channels",
            "1",
            "--output",
            str(out),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    audio(out)


@pytest.mark.parametrize("selection", [("--track-solo", "1"), ("--track-mute", "2")])
def test_mix_stems_follow_global_selection_and_pre_master(selection, tmp_path):
    sr = 8000
    first = np.sin(2 * np.pi * 220 * np.arange(1200) / sr) * 0.2
    second = np.sin(2 * np.pi * 440 * np.arange(2400) / sr) * 0.1
    inputs = [tmp_path / "first.wav", tmp_path / "second.wav"]
    sf.write(inputs[0], first, sr, subtype="FLOAT")
    sf.write(inputs[1], second, sr, subtype="FLOAT")
    output = tmp_path / "mix.wav"
    stems = tmp_path / "selected stems"
    cli(
        "groovmix",
        *inputs,
        "--sample-rate",
        sr,
        "--channels",
        1,
        "--output",
        output,
        "--stems",
        stems,
        "--subtype",
        "FLOAT",
        "--effect",
        '{"type":"gain","db":-6.020599913279624}',
        *selection,
    )
    master = audio(output, 1200)
    selected = audio(stems / "track_1.wav", 1200)
    silent, stem_sr = sf.read(stems / "track_2.wav", always_2d=True)
    assert stem_sr == sr and silent.shape == selected.shape and not silent.any()
    np.testing.assert_allclose(selected[:, 0], first, atol=4e-5)
    np.testing.assert_allclose(master[:, 0], first * 0.5, atol=1e-7)


def test_explicit_drum_voice_pattern_replace_preset_layers(tmp_path):
    plain = tmp_path / "plain.wav"
    preset = tmp_path / "preset.wav"
    render("groovdrm", plain, "--voice", "rim", "--pattern", "x...............")
    render("groovdrm", preset, "--preset", "electronic", "--voice", "rim", "--pattern", "x...............")
    np.testing.assert_array_equal(audio(plain, 2000), audio(preset, 2000))


@pytest.mark.parametrize("params", [{"gain": 5}, {"attack": -1}, {"cutoff": 30000}, {"channels": 3}])
def test_invalid_json_preset_ranges_fail_with_log(params, tmp_path):
    preset = tmp_path / "bad preset.json"
    log = tmp_path / "bad.log"
    output = tmp_path / "output.wav"
    preset.write_text(json.dumps({"version": 1, "instrument": "lead", "params": params}))
    result = cli("groovld", "--preset", preset, "--output", output, "--log-file", log, ok=False)
    assert result.returncode == 2 and not result.stdout and not output.exists()
    assert "Traceback" in log.read_text() and "Invalid input" in log.read_text()


def test_unknown_effect_property_rejected_before_output(tmp_path):
    source = tmp_path / "source.wav"
    sf.write(source, np.ones(32) * 0.1, 8000)
    output = tmp_path / "output.wav"
    result = cli("groovfx", source, "--output", output, "--effect", '{"type":"gain","typo":4}', ok=False)
    assert result.returncode == 2 and "Unknown effect properties" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "document",
    [
        {"version": 1, "instrument": "bass", "params": []},
        {"version": 1, "instrument": "bass", "params": {"unrecognized": 1}},
        {"version": 2, "instrument": "bass", "params": {}},
    ],
)
def test_info_rejects_malformed_synth_preset(document, tmp_path):
    preset = tmp_path / "malformed.json"
    preset.write_text(json.dumps(document))
    result = cli("groovinfo", preset, "--json", ok=False)
    assert result.returncode == 2 and not result.stdout


def test_bass_rejects_lead_only_arp_before_writing(tmp_path):
    output = tmp_path / "bass.wav"
    result = cli("groovbss", "--arp", "up", "--output", output, ok=False)
    assert result.returncode == 2 and "unrecognized arguments" in result.stderr and not output.exists()
