import numpy as np
import pytest

from groovescripting import automation, projects


def lane(param, points, curve="linear"):
    return {"param": param, "curve": curve, "points": points}


def test_linear_and_step_curves_use_absolute_beats():
    linear = lane("gain", [{"beat": 0, "value": 0}, {"beat": 2, "value": 2}])
    step = lane("gain", [{"beat": 0, "value": 0.5}, {"beat": 2, "value": 2}], "step")
    beats = np.array([-1, 0, 1, 2, 3], dtype=float)
    np.testing.assert_allclose(automation.values(linear, beats), [0, 0, 1, 2, 2])
    np.testing.assert_allclose(automation.values(step, beats), [0.5, 0.5, 0.5, 2, 2])


def test_gain_automation_is_sample_accurate_and_length_preserving():
    data = np.ones((5, 1))
    lanes = [lane("gain", [{"beat": 0, "value": 0}, {"beat": 1, "value": 1}])]
    out = automation.apply(data, sample_rate=4, bpm=60, lanes=lanes)
    assert out.shape == data.shape
    np.testing.assert_allclose(out[:, 0], [0, 0.25, 0.5, 0.75, 1])


def test_pan_automation_changes_stereo_balance():
    data = np.ones((4, 2))
    lanes = [lane("pan", [{"beat": 0, "value": -1}, {"beat": 1, "value": 1}])]
    out = automation.apply(data, sample_rate=4, bpm=60, lanes=lanes)
    assert out.shape == data.shape
    assert out[0, 1] == 0
    assert out[-1, 0] < out[-1, 1]


def test_cutoff_and_saturation_automation_stays_finite():
    sr = 8000
    t = np.arange(1000) / sr
    data = np.sin(2 * np.pi * 1000 * t)[:, None]
    lanes = [
        lane("cutoff", [{"beat": 0, "value": 200}, {"beat": 1, "value": 3000}]),
        lane("saturation", [{"beat": 0, "value": 0}, {"beat": 1, "value": 2}]),
    ]
    out = automation.apply(data, sample_rate=sr, bpm=480, lanes=lanes)
    assert out.shape == data.shape
    assert np.isfinite(out).all()
    assert not np.allclose(out, data)


def test_project_automation_continues_across_repeated_sections():
    seen = []

    def render(kind, params):
        return np.ones((4000, 1))

    original_apply = automation.apply

    def capture(data, sample_rate, bpm, lanes, start_beat=0):
        seen.append(start_beat)
        return original_apply(data, sample_rate, bpm, lanes, start_beat)

    project = {
        "version": 1,
        "bpm": 120,
        "beats": 1,
        "bars": 1,
        "sample_rate": 8000,
        "channels": 1,
        "tracks": [
            {
                "name": "A",
                "instrument": "bass",
                "automation": [
                    lane("gain", [{"beat": 0, "value": 0}, {"beat": 2, "value": 1}])
                ],
            }
        ],
        "sections": [{"bars": 1, "repeat": 2}],
    }
    out, _, _ = projects.render_project(project, render, automation_fn=capture)
    assert len(out) == 8000
    assert seen == [0, 1]
    assert out[0, 0] == 0
    assert out[-1, 0] > out[4000, 0]


@pytest.mark.parametrize(
    "lanes",
    [
        [{"param": "gain", "curve": "bezier", "points": [{"beat": 0, "value": 1}]}],
        [{"param": "unknown", "curve": "linear", "points": [{"beat": 0, "value": 1}]}],
        [{"param": "gain", "curve": "linear", "points": []}],
        [
            {
                "param": "gain",
                "curve": "linear",
                "points": [{"beat": 2, "value": 1}, {"beat": 1, "value": 1}],
            }
        ],
        [
            {"param": "gain", "curve": "linear", "points": [{"beat": 0, "value": 1}]},
            {"param": "gain", "curve": "step", "points": [{"beat": 1, "value": 2}]},
        ],
        [{"param": "pan", "curve": "linear", "points": [{"beat": 0, "value": 2}]}],
    ],
)
def test_automation_validation_rejects_bad_lanes(lanes):
    with pytest.raises(ValueError):
        automation.validate(lanes)
