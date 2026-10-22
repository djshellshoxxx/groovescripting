import pytest

from groovescripting import theory
from groovescripting.music import parse_pattern
from groovescripting.synth import render


def test_chord_symbols_expand_in_note_patterns():
    event = parse_pattern("Cm7@3 . Am@2/1", "note")
    assert [len(e["notes"]) for e in event] == [4, 3]
    assert event[0]["notes"] == [48, 51, 55, 58]
    assert event[1]["notes"] == [48, 52, 57]  # A minor first inversion: C E A


def test_euclid_known_rhythms():
    assert theory.euclid_string(3, 8) == "x..x..x."
    assert theory.euclid_string(5, 8).count("x") == 5
    assert theory.euclid_string(0, 4) == "...."
    assert theory.euclid_string(3, 8, 1) == ".x..x..x"
    with pytest.raises(ValueError):
        theory.euclid_string(9, 8)


def test_euclid_drum_pattern_and_modes():
    assert len(parse_pattern("euclid(4,16)", "drum")) == 4
    assert theory.SCALES["dorian"] == [0, 2, 3, 5, 7, 9, 10]
    assert theory.scale_notes("D", "dorian")[:3] == ["D4", "E4", "F4"]


def test_progression_and_errors(capsys):
    chords = theory.progression("C", ["I", "vi", "IV", "V"])
    assert chords == ["C@3", "Am@3", "F@3", "G@3"]
    assert theory.main(["progression", "A", "i", "iv"]) == 0
    assert theory.main(["chord", "Xyz"]) == 2
    with pytest.raises(ValueError):
        theory.chord_midi("Cfoo")


def test_new_mode_renders_in_scale():
    audio = render("lead", {"pattern": "C4 E4", "scale": "dorian", "root": "D", "bars": 1})
    assert audio.shape[0] > 0


def test_new_effects():
    import numpy as np

    from groovescripting import effects

    t = np.arange(4410) / 44100
    x = np.stack([0.2 * np.sin(2 * np.pi * 440 * t)] * 2, axis=1) + 0.1
    y = effects.apply(x, 44100, [{"type": "highpass", "hz": 100}])
    assert abs(y[-2000:].mean()) < abs(x.mean())  # DC removed
    n = effects.apply(x, 44100, [{"type": "normalize", "peak_db": -6}])
    assert abs(np.abs(n).max() - 10 ** (-6 / 20)) < 1e-9
    lim = effects.apply(x * 10, 44100, [{"type": "limiter", "ceiling_db": -3}])
    assert np.abs(lim).max() <= 10 ** (-3 / 20) + 1e-9
    c = effects.apply(x, 44100, [{"type": "chorus"}])
    assert c.shape == x.shape and np.isfinite(c).all()


@pytest.mark.parametrize("numeral,expected", [
    ("isus2", [48, 50, 55]),
    ("iisus4", [50, 55, 57]),
    ("vimaj7", [57, 61, 64, 68]),
    ("viidim", [59, 62, 65]),
])
def test_progression_suffixes_produce_renderable_chords(numeral, expected):
    for token in theory.progression("C", [numeral]):
        assert parse_pattern(token, "note")[0]["notes"] == expected


def test_theory_invalid_octave_is_a_cli_error(capsys):
    assert theory.main(["scale", "C", "major", "--octave", "10"]) == 2
    assert "MIDI" in capsys.readouterr().err


def test_chorus_delayed_signal_starts_with_silence():
    import numpy as np

    from groovescripting import effects

    impulse = np.zeros((8, 1))
    impulse[0] = 1
    delayed = effects.apply(impulse, 8000, [{"type": "chorus", "depth_ms": 0, "mix": 1}])
    np.testing.assert_array_equal(delayed[:, 0], [0, 1, 0, 0, 0, 0, 0, 0])


def test_theory_logging_preserves_pattern_stdout(tmp_path, capsys):
    log = tmp_path / "theory.log"
    assert theory.main(["--log-file", str(log), "chord", "Cm7"]) == 0
    assert capsys.readouterr().out.strip() == "C3+D#3+G3+A#3"
    assert "Completed groovtheory" in log.read_text()


@pytest.mark.parametrize("scale", sorted(theory.SCALES))
def test_every_documented_scale_is_available_in_cli_and_presets(scale):
    from groovescripting.cli import parser
    from groovescripting.validation import validate_instrument_params

    assert parser("groovld").parse_args(["--scale", scale]).scale == scale
    validate_instrument_params("lead", {"scale": scale})


def test_theory_cli_accepts_documented_numeric_pitch_class_root(capsys):
    assert theory.main(["scale", "2", "dorian"]) == 0
    assert capsys.readouterr().out.strip() == "D4 E4 F4 G4 A4 B4 C5 D5"


@pytest.mark.parametrize("root", ["12", "-1"])
def test_numeric_pitch_class_root_rejects_out_of_range(root, capsys):
    assert theory.main(["scale", root, "dorian"]) == 2
    assert capsys.readouterr().err


def test_theory_argument_error_is_logged(tmp_path):
    log = tmp_path / "invalid.log"
    with pytest.raises(SystemExit) as stopped:
        theory.main(["--log-file", str(log), "scale", "C", "not-a-scale"])
    assert stopped.value.code == 2
    assert "Argument error" in log.read_text()
