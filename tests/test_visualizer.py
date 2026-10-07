"""ASCII waveform visualizer contracts, tested without a terminal or audio hardware."""

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from groovescripting import cli, devices, visualizer


def test_frame_shape_playhead_and_status():
    sr = 8000
    tone = np.sin(np.arange(sr * 2) * 2 * np.pi * 220 / sr) * 0.5
    rows = visualizer.frame(tone, sr, 1.0, width=40, height=7)
    assert len(rows) == 8 and all(len(row) == 40 for row in rows)
    assert all(row[20] == "|" for row in rows[:-1])
    assert "#" in "".join(rows[:-1])
    assert rows[-1].startswith("00:01.0 / 00:02.0")
    assert "-6.0 dB" in rows[-1]


def test_frame_silence_and_edges():
    rows = visualizer.frame(np.zeros((800, 2)), 8000, 0.05, width=40, height=5, span=0.1)
    assert "#" not in "".join(rows[:-1])
    assert rows[2] == "-" * 20 + "|" + "-" * 19
    early = visualizer.frame(np.zeros(800), 8000, 0.0, width=40, height=5, span=0.1)
    assert early[2] == " " * 20 + "|" + "-" * 19
    assert "-inf dB" in rows[-1]
    with pytest.raises(ValueError):
        visualizer.frame(np.zeros(10), 8000, 0, width=4)


def test_display_redraws_in_place_until_audio_ends():
    stream = io.StringIO()
    ticks = iter([0.0, 0.0, 0.05, 0.11])
    display = visualizer.Display(
        np.ones(800) * 0.25,
        8000,
        stream=stream,
        height=3,
        width=40,
        clock=lambda: next(ticks),
        sleep=lambda _: None,
    )
    display.run()
    text = stream.getvalue()
    assert text.startswith("\x1b[?25l") and text.endswith("\x1b[?25h")
    assert text.count("\x1b[4F") == 2
    assert "00:00.1 / 00:00.1" in text


def test_play_draws_each_repeat_only_on_a_terminal():
    sd = MagicMock()
    with (
        patch.object(devices, "_backend", return_value=sd),
        patch.object(visualizer, "available", return_value=True),
        patch.object(visualizer.Display, "run") as run,
    ):
        devices.play(np.zeros(10), 44100, repeat=2, visualize=True)
        assert run.call_count == 2
        devices.play(np.zeros(10), 44100)
        assert run.call_count == 2
    with (
        patch.object(devices, "_backend", return_value=sd),
        patch.object(visualizer, "available", return_value=False),
        patch.object(visualizer.Display, "run") as run,
    ):
        devices.play(np.zeros(10), 44100, visualize=True)
        run.assert_not_called()


def test_cli_toggle(tmp_path, monkeypatch):
    import soundfile as sf

    path = tmp_path / "loop.wav"
    sf.write(path, np.zeros(800), 8000)
    seen = []
    monkeypatch.setattr(devices, "play", lambda data, sr, **kw: seen.append(kw))
    assert cli.run("groovplay", [str(path), "--visualizer", "--visualizer-height", "5"]) == 0
    assert cli.run("groovplay", [str(path), "--visualizer", "--no-visualizer"]) == 0
    assert cli.run("groovplay", [str(path)]) == 0
    assert [kw["visualize"] for kw in seen] == [True, False, False]
    assert seen[0]["visualizer_height"] == 5
    assert cli.run("groovdrm", ["--visualizer", "--output", str(tmp_path / "d.wav")]) == 2
    assert cli.run("groovplay", ["--devices", "--visualizer"]) == 2
