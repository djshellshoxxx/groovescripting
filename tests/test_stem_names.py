import json

import numpy as np
import pytest
import soundfile as sf

from groovescripting import cli


def project_file(tmp_path, names):
    path = tmp_path / "project.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "bpm": 240,
                "beats": 1,
                "bars": 1,
                "sample_rate": 8000,
                "tracks": [
                    {"name": name, "instrument": "lead", "pattern": note, "gain": 0.2}
                    for name, note in zip(names, ["C4", "E4", "G4", "B4", "D5"])
                ],
            }
        )
    )
    return path


@pytest.mark.parametrize("overwrite", [False, True])
def test_colliding_stem_names_preserve_distinct_audio(tmp_path, overwrite):
    source = project_file(tmp_path, ["A/B", "A?B", "a_b", "A_B_2", "Ordinary"])
    directory = tmp_path / "stems"
    master = tmp_path / "master.wav"
    args = [str(source), "-o", str(master), "--stems", str(directory), "--subtype", "FLOAT"]
    if overwrite:
        args.append("--overwrite")
    assert cli.run("groovseq", args) == 0
    files = sorted(directory.glob("*.wav"))
    assert len(files) == 5
    assert len({p.name.casefold() for p in files}) == 5
    assert (directory / "Ordinary.wav").exists()
    assert (directory / "A_B_2.wav").exists()
    signals = [sf.read(p, always_2d=True)[0] for p in files]
    assert all(not np.array_equal(a, b) for i, a in enumerate(signals) for b in signals[i + 1 :])
    mix, _ = sf.read(master, always_2d=True)
    np.testing.assert_allclose(sum(signals), mix, atol=5 / 32768)


def test_existing_stem_rejected_before_master_write(tmp_path):
    source = project_file(tmp_path, ["Lead"])
    directory = tmp_path / "stems"
    directory.mkdir()
    (directory / "Lead.wav").write_bytes(b"preserve")
    master = tmp_path / "master.wav"
    assert cli.run("groovseq", [str(source), "-o", str(master), "--stems", str(directory)]) == 1
    assert not master.exists()
    assert (directory / "Lead.wav").read_bytes() == b"preserve"


def test_stem_cannot_replace_master_even_with_overwrite(tmp_path):
    source = project_file(tmp_path, ["Lead"])
    directory = tmp_path / "stems"
    directory.mkdir()
    master = directory / "Lead.wav"
    assert (
        cli.run(
            "groovseq",
            [
                str(source),
                "-o",
                str(master),
                "--stems",
                str(directory),
                "--overwrite",
            ],
        )
        == 2
    )
    assert not master.exists()
