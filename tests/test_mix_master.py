import json

import numpy as np
import pytest
import soundfile as sf

from groovescripting import cli


@pytest.mark.parametrize("flags", [["--limit"], ["--normalize"], ["--normalize", "--limit"]])
def test_mix_protection_applies_after_positive_gain(tmp_path, flags):
    source = tmp_path / "source.wav"
    sf.write(source, np.full(80, 0.5), 8000, subtype="FLOAT")
    output = tmp_path / "mix.wav"
    assert (
        cli.run(
            "groovmix",
            [
                str(source),
                "-o",
                str(output),
                "--sample-rate",
                "8000",
                "--channels",
                "1",
                "--effect",
                json.dumps({"type": "gain", "db": 12}),
                "--subtype",
                "FLOAT",
                *flags,
            ],
        )
        == 0
    )
    data, rate = sf.read(output)
    assert rate == 8000
    assert np.max(np.abs(data)) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "flags,expected",
    [([], 0.5), (["--limit"], 0.5), (["--normalize"], 1.0), (["--normalize", "--limit"], 1.0)],
)
def test_mix_without_effects_keeps_existing_targets(tmp_path, flags, expected):
    source = tmp_path / "source.wav"
    sf.write(source, np.full(80, 0.5), 8000, subtype="FLOAT")
    output = tmp_path / "mix.wav"
    assert (
        cli.run(
            "groovmix",
            [
                str(source),
                "-o",
                str(output),
                "--sample-rate",
                "8000",
                "--channels",
                "1",
                "--subtype",
                "FLOAT",
                *flags,
            ],
        )
        == 0
    )
    data, _ = sf.read(output)
    np.testing.assert_allclose(data, expected)


def test_mix_keeps_headroom_until_effects_before_limit(tmp_path):
    source = tmp_path / "source.wav"
    sf.write(source, np.array([0.5, 1.5]), 8000, subtype="FLOAT")
    output = tmp_path / "mix.wav"
    assert (
        cli.run(
            "groovmix",
            [
                str(source),
                "-o",
                str(output),
                "--sample-rate",
                "8000",
                "--channels",
                "1",
                "--effect",
                json.dumps({"type": "gain", "db": -6}),
                "--subtype",
                "FLOAT",
                "--limit",
            ],
        )
        == 0
    )
    data, _ = sf.read(output)
    np.testing.assert_allclose(data, [0.25059362, 0.75178085], atol=1e-7)


def test_mix_without_protection_keeps_float_effect_headroom(tmp_path):
    source = tmp_path / "source.wav"
    sf.write(source, np.full(80, 0.5), 8000, subtype="FLOAT")
    output = tmp_path / "mix.wav"
    assert (
        cli.run(
            "groovmix",
            [
                str(source),
                "-o",
                str(output),
                "--sample-rate",
                "8000",
                "--channels",
                "1",
                "--effect",
                json.dumps({"type": "gain", "db": 12}),
                "--subtype",
                "FLOAT",
            ],
        )
        == 0
    )
    data, _ = sf.read(output)
    np.testing.assert_allclose(data, 1.99053585, atol=1e-7)
