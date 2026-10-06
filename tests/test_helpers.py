import numpy as np
import pytest

from groovescripting import audio, effects, presets, projects


def test_io_and_overwrite(tmp_path):
    p = tmp_path / "a.wav"
    x = np.array([[0.0], [0.25], [-0.25]])
    audio.write(p, x, 8000)
    y, sr = audio.read(p)
    assert sr == 8000 and np.allclose(x, y, atol=1 / 32768)
    assert audio.info(p)["frames"] == 3
    with pytest.raises(FileExistsError):
        audio.write(p, x, 8000)


def test_mixer_offsets_solo_and_resampling():
    x = np.ones((800, 1)) * 0.2
    y, r = audio.mix([dict(data=x, sample_rate=8000, offset_seconds=0.1, solo=True), dict(data=x)], 16000, 1)
    assert y.shape == (3200, 1) and r["active_tracks"] == 1
    assert np.all(y[:1600] == 0)
    y, _ = audio.mix([dict(data=x, offset_seconds=-0.05)], 8000, 1)
    assert len(y) == 400


def test_effect_tails_and_order():
    x = np.zeros((80, 1))
    x[0] = 1
    e = [dict(type="delay", seconds=0.01, repeats=2, feedback=0.5, mix=1)]
    full = effects.apply(x, 8000, e, "full")
    assert len(full) == 240 and full[80, 0] == 1 and full[160, 0] == 0.5
    assert len(effects.apply(x, 8000, e, "cut")) == 80
    assert effects.apply(x, 8000, e, "wrap")[0, 0] == 1.5
    with pytest.raises(ValueError):
        effects.apply(x, 8000, [dict(type="nonsense")])


def test_project_alignment_roundtrip_and_determinism(tmp_path):
    p = dict(
        version=1,
        bpm=120,
        bars=1,
        beats=4,
        sample_rate=8000,
        channels=1,
        seed=7,
        tracks=[
            dict(name="A", instrument="drum", params={}, offset=0.1),
            dict(name="B", instrument="bass", params={}),
        ],
        sections=[dict(bars=1, repeat=2, tracks={"B": dict(mute=True)})],
    )

    def render(instrument, params):
        return np.random.default_rng(params["seed"]).normal(0, 0.01, (100, 1))

    out, sr, stems = projects.render_project(p, render)
    assert out.shape == (32000, 1) and sr == 8000
    assert np.array_equal(out, stems["A"] + stems["B"])
    assert np.array_equal(out, projects.render_project(p, render)[0])
    f = tmp_path / "p.json"
    projects.save(f, p)
    assert projects.load(f) == p
    with pytest.raises(ValueError):
        projects.validate(dict(p, tracks=p["tracks"] * 2))


def test_invalid_buffers_and_project_overrides():
    with pytest.raises(ValueError):
        audio.mix([dict(data=[np.nan])], 8000, 1)
    with pytest.raises(ValueError):
        projects.validate(
            dict(tracks=[dict(name="A", instrument="drum")], sections=[dict(tracks={"unknown": {}})])
        )


def test_project_exact_clock_section_variation_and_overrides(tmp_path):
    seen = []

    def render(kind, params):
        seen.append(params.copy())
        return np.full((1000, 1), params.get("cutoff", 1))

    p = dict(
        version=1,
        bpm=240000,
        beats=1,
        bars=1,
        sample_rate=10000,
        channels=1,
        seed=2,
        humanize=0.01,
        velocity_humanize=0.1,
        tracks=[dict(name="A", instrument="bass", preset="sub", params={"cutoff": 2})],
        sections=[dict(bars=1, repeat=2, variation=3, tracks={"A": {"params": {"cutoff": 3}}})],
    )
    out, _, stems = projects.render_project(p, render)
    assert out.shape == (5, 1)  # global boundaries 0, 2.5, 5 round to 0, 3, 5 without drift
    assert np.all(out == 3) and np.array_equal(out, stems["A"])
    assert seen[0]["seed"] != seen[1]["seed"] and seen[0]["humanize"] == 0.01
    assert seen[0]["waveform"] == "sine" and seen[0]["velocity_humanize"] == 0.1
    f = tmp_path / "project.json"
    projects.save(f, p)
    assert projects.load(f) == p


@pytest.mark.parametrize(
    "change",
    [
        {"version": None},
        {"unknown": 1},
        {"tracks": [{"name": "A", "instrument": "drum", "mute": 1}]},
        {"tracks": [{"name": "A", "instrument": "drum", "params": {"made_up": 1}}]},
        {"tracks": [{"name": "A", "instrument": "drum", "invented": 1}]},
        {"sections": [{"unknown": 1}]},
    ],
)
def test_project_rejects_schema_errors(change):
    p = dict(version=1, tracks=[dict(name="A", instrument="drum")])
    p.update(change)
    with pytest.raises(ValueError):
        projects.validate(p)


def test_mix_stereo_normalize_limit_mute_and_trim():
    mono = np.ones((100, 1)) * 2
    y, _ = audio.mix([dict(data=mono, pan=-1, trim_seconds=0.005), dict(data=mono, mute=True)], 10000, 2)
    assert y.shape == (50, 2) and np.allclose(y[:, 0], 2) and np.allclose(y[:, 1], 0)
    y, r = audio.mix([dict(data=np.array([[4.0, 2.0]]))], 10000, 1, normalize=True)
    assert y[0, 0] == 1 and r["peak_before"] == 3
    y, _ = audio.mix([dict(data=mono)], 10000, 1, limit=True)
    assert np.all(y == 1)


def test_project_offset_trim_and_solo():
    p = dict(
        version=1,
        bpm=120,
        beats=1,
        bars=1,
        sample_rate=8000,
        channels=1,
        tracks=[
            dict(name="A", instrument="drum", solo=True, offset=0.1, trim=0.1),
            dict(name="B", instrument="bass"),
        ],
    )
    out, _, stems = projects.render_project(p, lambda *_: np.ones((8000, 1)))
    assert out.shape == (4000, 1) and np.all(out[:400] == 0) and np.all(out[400:800] == 1)
    assert np.all(out[800:] == 0) and np.all(stems["B"] == 0)


def test_lowpass_reduces_high_frequency_energy_and_resonance_changes_response():
    sr = 16000
    t = np.arange(sr) / sr
    x = (np.sin(2 * np.pi * 200 * t) + np.sin(2 * np.pi * 5000 * t))[:, None]
    y = effects.apply(x, sr, [dict(type="lowpass", hz=700)])[:, 0]
    spectrum = np.abs(np.fft.rfft(y[2000:]))
    freq = np.fft.rfftfreq(len(y) - 2000, 1 / sr)
    low = spectrum[np.argmin(abs(freq - 200))]
    high = spectrum[np.argmin(abs(freq - 5000))]
    assert high < low * 0.03
    a = effects.apply(x, sr, [dict(type="lowpass", hz=700, resonance=0.8)])
    assert not np.allclose(a[:, 0], y)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bpm", 1000.0001),
        ("beats", 33),
        ("bars", 1025),
        ("subdivision", 65),
        ("swing", 0.5),
        ("sample_rate", 192001),
        ("seed", 2**63),
        ("humanize", 0.100001),
        ("velocity_humanize", 0.500001),
    ],
)
def test_project_globals_match_cli_limits(field, value):
    project = dict(version=1, tracks=[dict(name="A", instrument="drum")])
    project[field] = value
    with pytest.raises(ValueError):
        projects.validate(project)


@pytest.mark.parametrize(
    ("instrument", "params"),
    [
        ("drum", {"waveform": "saw"}),
        ("drum", {"pitch": 20001}),
        ("bass", {"unison": 2}),
        ("bass", {"resonance": 1.01}),
        ("lead", {"voices": 33}),
        ("lead", {"arp_rate": 0}),
    ],
)
def test_project_rejects_incompatible_or_out_of_range_instrument_params(instrument, params):
    project = dict(version=1, tracks=[dict(name="A", instrument=instrument, params=params)])
    with pytest.raises(ValueError):
        projects.validate(project)


def test_project_accepts_cli_boundary_values():
    project = dict(
        version=1,
        bpm=1000,
        beats=32,
        bars=1024,
        subdivision=64,
        swing=0.49,
        sample_rate=192000,
        seed=2**63 - 1,
        humanize=0.1,
        velocity_humanize=0.5,
        tracks=[
            dict(
                name="A",
                instrument="lead",
                params={
                    "voices": 32,
                    "unison": 8,
                    "arp_rate": 0.01,
                    "resonance": 1,
                    "pulse_width": 0.95,
                },
            )
        ],
    )
    assert projects.validate(project) is project


@pytest.mark.parametrize(
    ("instrument", "params"),
    [
        ("drum", {"waveform": "triangle"}),
        ("bass", {"voices": 2}),
        ("lead", {"voices": 33}),
    ],
)
def test_preset_load_rejects_params_cli_would_reject(tmp_path, instrument, params):
    path = tmp_path / "invalid.json"
    path.write_text(
        __import__("json").dumps(
            {"version": 1, "instrument": instrument, "name": "invalid", "params": params}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        presets.load(instrument, path)
