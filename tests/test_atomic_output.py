"""Crash-consistency regression tests for user-owned project and MIDI outputs."""

from pathlib import Path

import mido
import pytest

from groovescripting import audio, midi, presets, projects


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
        original_write(self, "partial JSON", *args, **kwargs)
        raise OSError("simulated interrupted JSON write")

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


def test_audio_export_preserves_previous_file_on_encoder_failure(tmp_path, monkeypatch):
    import numpy as np

    destination = tmp_path / "mix.wav"
    destination.write_bytes(b"ORIGINAL AUDIO DATA")

    def fail_encode(filename, *args, **kwargs):
        Path(filename).write_bytes(b"partial WAV")
        raise OSError("simulated interrupted WAV encoding")

    monkeypatch.setattr(audio.sf, "write", fail_encode)
    with pytest.raises(OSError, match="interrupted"):
        audio.write(destination, np.zeros((100, 2)), 44100, overwrite=True)
    assert destination.read_bytes() == b"ORIGINAL AUDIO DATA"


def test_preset_save_preserves_previous_file_on_encoder_failure(tmp_path, monkeypatch):
    destination = tmp_path / "bass.json"
    destination.write_bytes(b"ORIGINAL PRESET DATA")

    def fail_encode(obj, stream, *args, **kwargs):
        stream.write("partial preset")
        raise OSError("simulated interrupted preset encoding")

    monkeypatch.setattr(presets.json, "dump", fail_encode)
    with pytest.raises(OSError, match="interrupted"):
        presets.save(destination, "bass", {"waveform": "sine"}, overwrite=True)
    assert destination.read_bytes() == b"ORIGINAL PRESET DATA"


def test_effect_preset_save_preserves_previous_file_on_failed_write(tmp_path, monkeypatch):
    destination = tmp_path / "effects.json"
    destination.write_bytes(b"ORIGINAL EFFECTS")

    original_write = Path.write_text

    def fail_write(self, text, *args, **kwargs):
        original_write(self, "partial effects", *args, **kwargs)
        raise OSError("simulated interrupted effect preset write")

    monkeypatch.setattr(Path, "write_text", fail_write)
    with pytest.raises(OSError, match="interrupted"):
        presets.save_effects(destination, [{"type": "gain", "db": -3}], overwrite=True)
    assert destination.read_bytes() == b"ORIGINAL EFFECTS"
