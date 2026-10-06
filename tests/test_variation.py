import copy

import pytest

from groovescripting import variation

BASE_NOTES = [
    {"beat": 0.0, "duration": 0.25, "notes": [60], "velocity": 0.8, "probability": 1},
    {"beat": 1.0, "duration": 0.25, "notes": [64], "velocity": 0.7, "probability": 1},
    {"beat": 2.0, "duration": 0.25, "notes": [67], "velocity": 0.9, "probability": 1},
]


def test_neutral_variation_preserves_events_without_mutating_input():
    source = copy.deepcopy(BASE_NOTES)
    result = variation.mutate(
        source,
        "note",
        total_beats=4,
        subdivision=4,
        seed=7,
    )
    assert result == BASE_NOTES
    assert source == BASE_NOTES
    assert result is not source


def test_variation_is_seeded_bounded_and_does_not_change_pitch():
    a = variation.mutate(
        BASE_NOTES,
        "note",
        total_beats=4,
        subdivision=4,
        seed=11,
        variation=1,
    )
    b = variation.mutate(
        BASE_NOTES,
        "note",
        total_beats=4,
        subdivision=4,
        seed=11,
        variation=1,
    )
    c = variation.mutate(
        BASE_NOTES,
        "note",
        total_beats=4,
        subdivision=4,
        seed=12,
        variation=1,
    )
    assert a == b
    assert a != c
    assert [e["notes"] for e in a] == [e["notes"] for e in BASE_NOTES]
    assert all(0 <= e["beat"] < 4 and 0 <= e["velocity"] <= 1 for e in a)


def test_density_zero_removes_existing_events():
    assert (
        variation.mutate(
            BASE_NOTES,
            "note",
            total_beats=4,
            subdivision=4,
            seed=1,
            density=0,
        )
        == []
    )


def test_drum_ghost_notes_only_use_empty_grid_positions():
    base = [{"beat": 0.0, "duration": 0.25, "notes": [], "velocity": 1.0, "probability": 1}]
    out = variation.mutate(
        base,
        "drum",
        total_beats=1,
        subdivision=4,
        seed=2,
        ghost_notes=1,
    )
    beats = [round(e["beat"], 8) for e in out]
    assert beats == [0.0, 0.25, 0.5, 0.75]
    ghosts = out[1:]
    assert all(0.15 <= e["velocity"] <= 0.45 for e in ghosts)


def test_drum_fill_operates_only_on_every_nth_bar_final_beat():
    out = variation.mutate(
        [],
        "drum",
        total_beats=8,
        subdivision=4,
        seed=3,
        variation=1,
        fill_every=2,
        beats_per_bar=4,
    )
    assert out
    assert all(7 <= e["beat"] < 8 for e in out)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"variation": -0.1},
        {"variation": 1.1},
        {"density": -0.1},
        {"density": 1.1},
        {"ghost_notes": 1.1},
        {"fill_every": -1},
        {"fill_every": 129},
        {"fill_every": 1.5},
    ],
)
def test_variation_rejects_invalid_controls(kwargs):
    with pytest.raises(ValueError):
        variation.mutate([], "drum", total_beats=4, subdivision=4, seed=0, **kwargs)


def test_tonal_variation_rejects_drum_only_controls():
    with pytest.raises(ValueError):
        variation.mutate(
            BASE_NOTES,
            "note",
            total_beats=4,
            subdivision=4,
            seed=0,
            ghost_notes=0.1,
        )
