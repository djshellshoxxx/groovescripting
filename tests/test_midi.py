import json

import pytest

mido = pytest.importorskip("mido")

from groovescripting import midi, projects


def make_midi(path, tempos=(500000,), channel=0):
    mf = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mf.tracks.append(track)
    for tempo in tempos:
        track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    track.append(mido.Message("note_on", note=60, velocity=100, channel=channel, time=0))
    track.append(mido.Message("note_on", note=64, velocity=100, channel=channel, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, channel=channel, time=480))
    track.append(mido.Message("note_on", note=64, velocity=0, channel=channel, time=0))
    mf.save(path)


def test_import_groups_chord_and_builds_valid_project(tmp_path):
    path = tmp_path / "chord.mid"
    make_midi(path)
    project = midi.import_file(path, subdivision=4)
    assert projects.validate(project) is project
    assert project["bpm"] == pytest.approx(120)
    assert project["beats"] == 4
    events = project["tracks"][0]["params"]["events"]
    assert len(events) == 1
    assert events[0]["notes"] == [60, 64]
    assert events[0]["beat"] == 0
    assert events[0]["duration"] == 1


def test_import_rejects_conflicting_tempo_map(tmp_path):
    path = tmp_path / "tempo.mid"
    make_midi(path, tempos=(500000, 400000))
    with pytest.raises(ValueError, match="tempo"):
        midi.import_file(path)


def test_import_rejects_percussion_only_midi(tmp_path):
    path = tmp_path / "drums.mid"
    make_midi(path, channel=9)
    with pytest.raises(ValueError, match="percussion"):
        midi.import_file(path)


def test_export_and_reimport_project_sections_and_transpose(tmp_path):
    project = {
        "version": 1,
        "bpm": 120,
        "beats": 4,
        "bars": 1,
        "subdivision": 4,
        "tracks": [
            {
                "name": "Lead",
                "instrument": "lead",
                "pattern": "C4 . E4 .",
                "params": {"transpose": 12},
            }
        ],
        "sections": [{"bars": 1, "repeat": 2}],
    }
    path = tmp_path / "song.mid"
    midi.export_file(project, path)
    assert path.exists()
    imported = midi.import_file(path, quantize=False)
    notes = [
        note
        for event in imported["tracks"][0]["params"]["events"]
        for note in event["notes"]
    ]
    assert 72 in notes and 76 in notes
    assert max(e["beat"] for e in imported["tracks"][0]["params"]["events"]) >= 4


def test_export_drum_uses_general_midi_channel_10(tmp_path):
    project = {
        "version": 1,
        "bpm": 120,
        "beats": 4,
        "bars": 1,
        "tracks": [
            {
                "name": "Drums",
                "instrument": "drum",
                "params": {"voice": "kick"},
                "pattern": "x...x...x...x...",
            }
        ],
    }
    path = tmp_path / "drums.mid"
    midi.export_file(project, path)
    mf = mido.MidiFile(path)
    notes = [m for t in mf.tracks for m in t if m.type == "note_on" and m.velocity]
    assert notes
    assert all(m.channel == 9 and m.note == 36 for m in notes)


def test_export_overwrite_protection(tmp_path):
    project = {
        "version": 1,
        "tracks": [{"name": "Lead", "instrument": "lead", "pattern": "C4"}],
    }
    path = tmp_path / "exists.mid"
    path.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        midi.export_file(project, path)


def test_groovmidi_cli_import_export(tmp_path):
    source = tmp_path / "source.mid"
    make_midi(source)
    project_path = tmp_path / "project.json"
    assert midi.cli(["import", str(source), "--output", str(project_path)]) == 0
    project = json.loads(project_path.read_text())
    assert project["tracks"]
    output = tmp_path / "out.mid"
    assert midi.cli(["export", str(project_path), "--output", str(output)]) == 0
    assert output.exists()
