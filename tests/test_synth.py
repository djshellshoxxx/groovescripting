import unittest

import numpy as np

from groovescripting.music import beat_frame, frequency, parse_pattern
from groovescripting.synth import DRUMS, oscillator, render


class SynthesisTests(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(beat_frame(0.5, 60, 1001), 501)
        self.assertEqual(
            render("bass", {"bpm": 137, "bars": 3, "sample_rate": 8000}).shape, (beat_frame(12, 137, 8000), 2)
        )

    def test_parser(self):
        e = parse_pattern("C4+E4+G4:0.5:0.7:0.9 . A4!")
        self.assertEqual(e[0]["notes"], [60, 64, 67])
        self.assertEqual(e[1]["beat"], 0.5)
        self.assertTrue(e[1]["accent"])
        self.assertEqual(frequency(e[1]["notes"][0]), 440)
        with self.assertRaises(ValueError):
            parse_pattern("C4:0")

    def test_frequency(self):
        a = oscillator(np.full(8000, 440), 8000, "sine")
        self.assertEqual(np.argmax(abs(np.fft.rfft(a))), 440)

    def test_drums(self):
        sounds = []
        for voice in DRUMS:
            o = {"voice": voice, "sample_rate": 8000, "pattern": "x...", "bars": 0.25}
            a = render("drum", o)
            np.testing.assert_array_equal(a, render("drum", o))
            self.assertTrue(np.isfinite(a).all())
            self.assertGreater(np.max(abs(a)), 0.01)
            sounds.append(a)
        for a, b in zip(sounds, sounds[1:]):
            self.assertFalse(np.array_equal(a, b))

    def test_probability_offset(self):
        self.assertFalse(render("bass", {"pattern": "C4:1:1:0", "sample_rate": 8000}).any())
        a = render("drum", {"offset": 1, "pattern": "x", "sample_rate": 8000})
        self.assertFalse(a[:4000].any())
        self.assertTrue(a[4000:].any())

    def test_choke(self):
        a = render(
            "drum",
            {
                "drum_patterns": {"open_hat": "x...", "closed_hat": ".x.."},
                "drum_params": {"closed_hat": {"gain": 0}},
                "sample_rate": 8000,
            },
        )
        self.assertTrue(a[:1000].any())
        self.assertFalse(a[1000:4000].any())

    def test_glide(self):
        o = {"pattern": "C2:0.5 G2:0.5", "sample_rate": 8000, "waveform": "sine"}
        a = render("bass", o)
        b = render("bass", dict(o, glide=0.2, legato=True))
        np.testing.assert_array_equal(a[:1000], b[:1000])
        self.assertGreater(np.linalg.norm(a[1000:2000] - b[1000:2000]), 1)

    def test_stealing(self):
        o = {"pattern": "C4:2 G4:2", "sample_rate": 8000, "release": 0}
        a = render("lead", dict(o, voices=1))
        b = render("lead", dict(o, voices=2))
        np.testing.assert_array_equal(a[:970], b[:970])
        self.assertGreater(np.linalg.norm(a[1000:] - b[1000:]), 1)

    def test_controls(self):
        for waveform in ("sine", "triangle", "saw", "pulse"):
            a = render(
                "lead",
                {
                    "pattern": "C4+E4+G4:1",
                    "sample_rate": 8000,
                    "waveform": waveform,
                    "arp": "up",
                    "unison": 3,
                    "resonance": 1,
                    "filter_amount": 3,
                    "vibrato_depth": 20,
                    "saturation": 2,
                    "lfo_depth": 2,
                },
            )
            self.assertTrue(np.isfinite(a).all())
            self.assertTrue(a.any())

    def test_repetition_swing_humanization(self):
        o = {
            "pattern": "xx",
            "voice": "rim",
            "bars": 0.5,
            "sample_rate": 8000,
            "drum_params": {"rim": {"decay": 0.001}},
        }
        a = render("drum", o)
        self.assertTrue(a[2000:2100].any())
        b = render("drum", dict(o, swing=1))
        self.assertFalse(b[1000:1100].any())
        self.assertTrue(b[1500:1600].any())
        c = render("drum", dict(o, humanize=0.01, velocity_humanize=0.2))
        np.testing.assert_array_equal(c, render("drum", dict(o, humanize=0.01, velocity_humanize=0.2)))
        self.assertFalse(np.array_equal(a, c))

    def test_scale_transpose_pan(self):
        o = {"pattern": "C#4:1", "sample_rate": 8000, "waveform": "sine", "scale": "major", "root": "C"}
        a = render("bass", o)
        b = render("bass", dict(o, pattern="C4:1"))
        np.testing.assert_array_equal(a, b)
        c = render("bass", dict(o, transpose=12, pan=1))
        self.assertFalse(c[:, 0].any())
        self.assertTrue(c[:, 1].any())

    def test_validation(self):
        for o in (
            {"cutoff": -1},
            {"gain": float("nan")},
            {"voices": 0},
            {"pulse_width": 2},
            {"humanize": -1},
        ):
            with self.assertRaises(ValueError):
                render("lead", o)

    def test_ties_none_and_mono_glide(self):
        e = parse_pattern("C4 ~ ~ .")
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["duration"], 0.75)
        np.testing.assert_array_equal(
            render("bass", {"pattern": "C4 ~", "sample_rate": 8000}),
            render("bass", {"pattern": "C4:.5 .", "sample_rate": 8000, "scale": "none"}),
        )
        o = {"pattern": "C4:1 G4:1", "sample_rate": 8000, "mode": "mono"}
        self.assertGreater(np.linalg.norm(render("lead", o) - render("lead", dict(o, glide=0.1))), 1)

    def test_fades_and_invalid_events(self):
        a = render("lead", {"pattern": "C4:2 G4:2", "sample_rate": 8000, "mode": "mono"})
        self.assertEqual(a[999, 0], 0)
        for options in (
            {"pattern": "nonsense", "voice": "kick"},
            {"events": [{"beat": 0, "notes": [999], "probability": 0}]},
            {"events": [{"beat": float("nan"), "notes": [60]}]},
            {"events": [{"beat": 0, "notes": [{"hz": 5000}]}], "sample_rate": 8000},
            {"unsupported": 1},
        ):
            with self.assertRaises(ValueError):
                render("drum" if options.get("voice") else "lead", options)

    def test_upfront_drum_validation_and_frame_budget(self):
        invalid = (
            {"drum_params": {"kick": {"typo": 1}}},
            {"drum_params": {"ghost": {"gain": 1}}},
            {"drum_params": {"kick": {"gain": -1}}},
            {"drum_params": {"kick": {"pitch": 0}}},
            {"drum_params": {"kick": {"pan": 2}}},
            {"drum_params": {"kick": {"decay": float("nan")}}},
            {"drum_params": []},
            {"bars": 100000},
        )
        for options in invalid:
            with self.assertRaises(ValueError):
                render("drum", options)
        for event in (
            {"beat": 0, "notes": [60], "typo": 1},
            {"beat": 0, "notes": [{"hz": 5000}], "probability": 0},
        ):
            with self.assertRaises(ValueError):
                render("lead", {"sample_rate": 8000, "events": [event]})
