"""Debugger text and command output supports arbitrary-frequency note events."""

import io
import json

import pytest

from groovescripting import debug, trace


def hz_project(hz=440):
    return {
        "version": 1,
        "sample_rate": 8000,
        "tracks": [
            {
                "name": "Lead",
                "instrument": "lead",
                "params": {"events": [{"beat": 0, "notes": [{"hz": hz}, 60], "duration": 1}]},
            }
        ],
    }


@pytest.mark.parametrize("hz", [440, "440"])
def test_row_formats_hz_and_numeric_notes(hz):
    _, records = trace.collect(hz_project(hz))
    assert "notes 440Hz" in debug.row(records[0])
    assert "notes 60" in debug.row(records[1])


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_debug_commands_accept_hz_events(tmp_path, fmt):
    source = tmp_path / "hz.json"
    source.write_text(json.dumps(hz_project()), encoding="utf-8")
    commands = tmp_path / "commands.txt"
    commands.write_text("step\nevents\nquit\n", encoding="utf-8")
    output = io.StringIO()
    assert debug.cli([str(source), "--commands", str(commands), "--format", fmt], stdout=output) == 0
    if fmt == "text":
        assert "notes 440Hz" in output.getvalue()
        assert "notes 60" in output.getvalue()
    else:
        messages = [json.loads(line) for line in output.getvalue().splitlines()]
        assert messages[0]["record"]["notes"] == [{"hz": 440}]
        assert [record["notes"] for record in messages[1]["records"]] == [[{"hz": 440}], [60]]
