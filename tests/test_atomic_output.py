"""Crash-consistency regression tests for user-owned project and MIDI outputs."""

from pathlib import Path

import mido
import pytest

from groovescripting import midi, projects


def _project():
    return {
        "version": 1,
        "bpm": 120,
        "tracks": [{"name": "Lead", "instrument": "lead", "pattern": "C4"}],
    }


def test_project_save_preserves_previous_file_after_partial_write(tmp_path, monkeypatch):
    destination = tmp_path / "song.json"
    destination.write_bytes(b"ORIGINAL PROJECT DATA")
    original_write = Path.write_text

    def fail_after_partial_write(self, text, *args, **kwargs):
        if self == destination:
            original_write(self, "partial JSON", *args, **kwargs)
            raise OSError("simulated interrupted JSON write")
        return original_write(self, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_after_partial_write)
    with pytest.raises(OSError, match="interrupted"):
        projects.save(destination, _project(), overwrite=True)
    assert destination.read_bytes() == b"ORIGINAL PROJECT DATA"


def test_midi_export_preserves_previous_file_after_failed_save(tmp_path, monkeypatch):
    destination = tmp_path / "song.mid"
    destination.write_bytes(b"ORIGINAL MIDI DATA")

    def fail_after_partial_write(self, filename=None, *args, **kwargs):
        Path(filename).write_bytes(b"partial MIDI")
        raise OSError("simulated interrupted MIDI write")

    monkeypatch.setattr(mido.MidiFile, "save", fail_after_partial_write)
    with pytest.raises(OSError, match="interrupted"):
        midi.export_file(_project(), destination, overwrite=True)
    assert destination.read_bytes() == b"ORIGINAL MIDI DATA"


def test_midi_export_failure_leaves_no_partial_new_output(tmp_path, monkeypatch):
    destination = tmp_path / "new.mid"

    def fail_after_partial_write(self, filename=None, *args, **kwargs):
        Path(filename).write_bytes(b"partial MIDI")
        raise OSError("simulated interrupted MIDI write")

    monkeypatch.setattr(mido.MidiFile, "save", fail_after_partial_write)
    with pytest.raises(OSError, match="interrupted"):
        midi.export_file(_project(), destination)
    assert not destination.exists()
