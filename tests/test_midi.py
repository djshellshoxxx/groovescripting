import json

import mido
import pytest

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
    notes = [note for event in imported["tracks"][0]["params"]["events"] for note in event["notes"]]
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


@pytest.mark.parametrize(
    "file_type,division,tempo,match",
    [
        (2, 480, 500000, "type"),
        (1, 0, 500000, "division"),
        (1, -6360, 500000, "division"),
        (1, 480, 0, "tempo"),
    ],
)
def test_import_invalid_timing_is_input_error(tmp_path, file_type, division, tempo, match):
    source = tmp_path / "invalid.mid"
    make_midi(source, tempos=(tempo,))
    mf = mido.MidiFile(source)
    mf.type = file_type
    mf.ticks_per_beat = division
    mf.save(source)
    with pytest.raises(ValueError, match=match):
        midi.import_file(source)
    output = tmp_path / "project.json"
    assert midi.cli(["import", str(source), "-o", str(output)]) == 2
    assert not output.exists()


def test_import_assigns_unique_names_without_losing_notes(tmp_path):
    source = tmp_path / "names.mid"
    mf = mido.MidiFile()
    for index, name in enumerate(["Piano", "Piano", "Piano (2)", "", "MIDI Track 4"]):
        track = mido.MidiTrack(
            [
                mido.MetaMessage("track_name", name=name),
                mido.Message("note_on", note=60 + index, velocity=100),
                mido.Message("note_off", note=60 + index, time=480),
            ]
        )
        mf.tracks.append(track)
    mf.save(source)
    project = midi.import_file(source)
    names = [track["name"] for track in project["tracks"]]
    assert len(set(names)) == 5
    assert names[0] == "Piano"
    assert [track["params"]["events"][0]["notes"] for track in project["tracks"]] == [
        [60],
        [61],
        [62],
        [63],
        [64],
    ]
    assert midi.import_file(source) == project


@pytest.mark.parametrize("conductor_first", [False, True])
def test_import_closes_unclosed_note_at_file_end(tmp_path, conductor_first):
    source = tmp_path / "sustain.mid"
    mf = mido.MidiFile()
    note = mido.MidiTrack([mido.Message("note_on", note=60, velocity=100)])
    conductor = mido.MidiTrack([mido.MetaMessage("end_of_track", time=1920)])
    mf.tracks.extend([conductor, note] if conductor_first else [note, conductor])
    mf.save(source)
    project = midi.import_file(source, quantize=False)
    assert project["tracks"][0]["params"]["events"][0]["duration"] == 4


def test_import_drums_requires_opt_in_and_maps_all_voices(tmp_path):
    source = tmp_path / "drums.mid"
    mf = mido.MidiFile()
    track = mido.MidiTrack([mido.MetaMessage("track_name", name="Kit")])
    mf.tracks.append(track)
    for note in [36, 38, 42, 46, 39, 45, 37]:
        track.append(mido.Message("note_on", note=note, velocity=96, channel=9))
        track.append(mido.Message("note_on", note=note, velocity=0, channel=9, time=120))
    mf.save(source)
    with pytest.raises(ValueError, match="percussion"):
        midi.import_file(source)
    project = midi.import_file(source, include_drums=True)
    assert projects.validate(project) is project
    assert [t["params"]["voice"] for t in project["tracks"]] == [
        "kick",
        "snare",
        "closed_hat",
        "open_hat",
        "clap",
        "tom",
        "rim",
    ]
    for index, imported in enumerate(project["tracks"]):
        assert imported["instrument"] == "drum"
        event = imported["params"]["events"][0]
        assert event["beat"] == index / 4
        assert event["duration"] == 0.25
        assert event["velocity"] == pytest.approx(96 / 127)
    output = tmp_path / "roundtrip.mid"
    midi.export_file(project, output)
    actual = [m.note for t in mido.MidiFile(output).tracks for m in t if m.type == "note_on"]
    assert actual == [36, 38, 42, 46, 39, 45, 37]


def test_import_mixed_channels_keeps_melody_and_drums_separate(tmp_path):
    source = tmp_path / "mixed.mid"
    mf = mido.MidiFile()
    mf.tracks.append(
        mido.MidiTrack(
            [
                mido.MetaMessage("track_name", name="Band"),
                mido.Message("note_on", note=60, velocity=100),
                mido.Message("note_on", note=36, velocity=64, channel=9, time=10),
                mido.Message("note_off", note=60, time=110),
                mido.Message("note_off", note=36, channel=9, time=10),
            ]
        )
    )
    mf.save(source)
    legacy = midi.import_file(source)
    assert len(legacy["tracks"]) == 1
    assert legacy["tracks"][0]["params"]["events"][0]["notes"] == [60]
    project = midi.import_file(source, instrument="bass", include_drums=True, quantize=False)
    assert [t["instrument"] for t in project["tracks"]] == ["bass", "drum"]
    event = project["tracks"][1]["params"]["events"][0]
    assert event["beat"] == pytest.approx(10 / 480)
    assert event["duration"] == 0.25
    assert event["velocity"] == pytest.approx(64 / 127)
    from groovescripting.synth import render

    audio, sr, stems = projects.render_project(dict(project, sample_rate=8000), render)
    assert sr == 8000 and audio.any() and len(stems) == 2


def test_import_drums_cli_and_unknown_note_errors(tmp_path):
    source = tmp_path / "drums.mid"
    make_midi(source, channel=9)
    output = tmp_path / "drums.json"
    with pytest.raises(ValueError, match="60"):
        midi.import_file(source, include_drums=True)
    assert midi.cli(["import", str(source), "--include-drums", "-o", str(output)]) == 2
    assert not output.exists()
    mf = mido.MidiFile(source)
    for message in mf.tracks[0]:
        if message.type in ("note_on", "note_off"):
            message.note = 36
    mf.save(source)
    assert midi.cli(["import", str(source), "--include-drums", "-o", str(output)]) == 0
    assert json.loads(output.read_text())["tracks"][0]["instrument"] == "drum"
    before = output.read_bytes()
    assert midi.cli(["import", str(source), "--include-drums", "-o", str(output)]) == 1
    assert output.read_bytes() == before


def test_import_drums_flag_requires_boolean(tmp_path):
    source = tmp_path / "source.mid"
    make_midi(source)
    with pytest.raises(ValueError, match="include_drums"):
        midi.import_file(source, include_drums="yes")


def test_import_drums_names_minimum_duration_and_unclosed_notes(tmp_path):
    source = tmp_path / "names-drums.mid"
    mf = mido.MidiFile()
    for name in ["Kit", "Kit", "Kit kick"]:
        mf.tracks.append(
            mido.MidiTrack(
                [
                    mido.MetaMessage("track_name", name=name),
                    mido.Message("note_on", note=36, velocity=100, channel=9),
                    mido.Message("note_off", note=36, channel=9, time=1),
                ]
            )
        )
    mf.tracks.append(
        mido.MidiTrack(
            [
                mido.Message("note_on", note=38, velocity=70, channel=9),
            ]
        )
    )
    mf.tracks.append(mido.MidiTrack([mido.MetaMessage("end_of_track", time=960)]))
    mf.save(source)
    project = midi.import_file(source, include_drums=True)
    tracks = project["tracks"]
    assert len(tracks) == len({t["name"] for t in tracks}) == 4
    assert [t["params"]["events"][0]["duration"] for t in tracks] == [0.25, 0.25, 0.25, 2]
    assert project == midi.import_file(source, include_drums=True)
