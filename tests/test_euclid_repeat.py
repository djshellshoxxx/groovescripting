import numpy as np
import pytest

from groovescripting import expr, synth, trace
from groovescripting.theory import euclid_string


@pytest.mark.parametrize(
    "macro,pulses,steps,rotation",
    [
        ("euclid(3,8)", 3, 8, 0),
        (" euclid( 3, 8, 2 ) ", 3, 8, 2),
        ("euclid(0,8)", 0, 8, 0),
        ("euclid(5,8,-1)", 5, 8, -1),
    ],
)
def test_euclidean_macro_repeats_like_expanded_pattern(macro, pulses, steps, rotation):
    options = {"pattern": macro, "bars": 1, "beats": 4, "subdivision": 4, "sample_rate": 8000}
    expanded = dict(options, pattern=euclid_string(pulses, steps, rotation))
    assert synth._events(options, "drum") == synth._events(expanded, "drum")
    np.testing.assert_array_equal(synth.render("drum", options), synth.render("drum", expanded))


def test_probability_rejected_explicit_note_is_normalized_for_predicates():
    project = {
        "version": 1,
        "sample_rate": 8000,
        "tracks": [
            {
                "name": "Lead",
                "instrument": "lead",
                "params": {
                    "events": [{"beat": 0, "notes": ["C4"], "duration": 1, "probability": 0}],
                },
            }
        ],
    }
    _, records = trace.collect(project)
    assert len(records) == 1
    assert records[0]["notes"] == [60]
    assert expr.compile_expression("note == 60")(records[0])


def test_euclidean_repetition_is_shared_by_trace_and_midi(tmp_path):
    import mido

    from groovescripting import midi

    project = {
        "version": 1,
        "sample_rate": 8000,
        "tracks": [{"name": "Kick", "instrument": "drum", "pattern": "euclid(3,8)"}],
    }
    _, records = trace.collect(project)
    assert [record["timing"]["requested_beat"] for record in records] == [0, 0.75, 1.5, 2, 2.75, 3.5]
    output = tmp_path / "euclid.mid"
    midi.export_file(project, output)
    absolute = 0
    onsets = []
    for message in mido.MidiFile(output).tracks[1]:
        absolute += message.time
        if message.type == "note_on":
            onsets.append(absolute)
    assert onsets == [0, 360, 720, 960, 1320, 1680]
