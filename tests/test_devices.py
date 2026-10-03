"""Device contracts tested without touching hardware or host master volume."""

import json
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from groovescripting import devices


class DeviceTests(unittest.TestCase):
    def test_inventory_and_diagnosis(self):
        sd = MagicMock()
        sd.query_devices.side_effect = [[{"name": "mock", "max_output_channels": 2}], {"name": "mock"}]
        with patch.object(devices, "_backend", return_value=sd):
            inventory = devices.list_devices()
            self.assertEqual(inventory[0]["index"], 0)
            json.dumps(inventory)
            self.assertTrue(devices.diagnose()["supported"])
        sd.check_output_settings.assert_called_once()

    def test_missing_backend_diagnosis(self):
        with patch.object(devices, "_backend", side_effect=RuntimeError("install playback")):
            self.assertIn("install playback", devices.diagnose()["error"])
            with self.assertRaises(RuntimeError):
                devices.play(np.zeros(10), 44100)

    def test_gain_repeat_and_cleanup(self):
        sd = MagicMock()
        with patch.object(devices, "_backend", return_value=sd):
            devices.play(np.ones(10), 44100, volume=0.25, repeat=2)
        self.assertEqual(sd.play.call_count, 2)
        np.testing.assert_equal(sd.play.call_args.args[0], np.full(10, 0.25))
        sd.stop.assert_called_once()

    def test_interrupt_stops(self):
        sd = MagicMock()
        sd.wait.side_effect = KeyboardInterrupt
        with patch.object(devices, "_backend", return_value=sd), self.assertRaises(KeyboardInterrupt):
            devices.play(np.zeros(10), 44100)
        sd.stop.assert_called_once()

    def test_mute_and_invalid_inputs(self):
        sd = MagicMock()
        with patch.object(devices, "_backend", return_value=sd):
            devices.play(np.ones(10), 44100, mute=True)
        np.testing.assert_equal(sd.play.call_args.args[0], np.zeros(10))
        for kwargs in ({"repeat": 0}, {"repeat": 1001}, {"volume": float("nan")}, {"sample_rate": 0}):
            args = {"sample_rate": 44100, **kwargs}
            with self.assertRaises(ValueError):
                devices.play(np.zeros(10), **args)
        for audio in ([], [np.nan], [2], np.zeros((2, 3))):
            with self.assertRaises(ValueError):
                devices.play(audio, 44100)

    def test_test_tone_contract(self):
        with patch.object(devices, "play") as play:
            devices.test_tone()
        tone, rate = play.call_args.args
        self.assertEqual(rate, 44100)
        self.assertEqual(len(tone), 22050)
        self.assertEqual(play.call_args.kwargs["volume"], 0.1)
        self.assertAlmostEqual(float(tone[0]), 0)
        self.assertAlmostEqual(float(tone[-1]), 0)

    def test_pactl_explicit_request(self):
        with (
            patch.object(devices.platform, "system", return_value="Linux"),
            patch.object(devices.shutil, "which", return_value="/bin/pactl"),
            patch.object(devices, "_run") as run,
        ):
            result = devices.set_system_volume(0.4, unmute=True)
        self.assertEqual(result["adapter"], "pactl")
        self.assertEqual(run.call_args_list[0].args[0], ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "40%"])
        self.assertEqual(run.call_args_list[1].args[0][-1], "0")
        with self.assertRaises(ValueError):
            devices.set_system_volume()

    def test_other_adapters_and_unsupported(self):
        with (
            patch.object(devices.platform, "system", return_value="Linux"),
            patch.object(devices.shutil, "which", side_effect=lambda name: name == "amixer"),
            patch.object(devices, "_run") as run,
        ):
            devices.set_system_volume(0.5, unmute=True)
            self.assertEqual(run.call_args.args[0], ["amixer", "-q", "sset", "Master", "50%", "unmute"])
        with (
            patch.object(devices.platform, "system", return_value="Darwin"),
            patch.object(devices.shutil, "which", return_value="/usr/bin/osascript"),
            patch.object(devices, "_run") as run,
        ):
            devices.set_system_volume(unmute=True)
            self.assertEqual(run.call_args.args[0][-1], "set volume output muted false")
        with patch.object(devices.platform, "system", return_value="Other"), self.assertRaises(RuntimeError):
            devices.set_system_volume(0.5)

    def test_windows_endpoint_adapter(self):
        module = MagicMock()
        endpoint = module.AudioUtilities.GetSpeakers.return_value.EndpointVolume
        with (
            patch.object(devices.platform, "system", return_value="Windows"),
            patch.dict(sys.modules, {"pycaw": MagicMock(), "pycaw.pycaw": module}),
        ):
            devices.set_system_volume(0.25, unmute=True)
        endpoint.SetMasterVolumeLevelScalar.assert_called_once_with(0.25, None)
        endpoint.SetMute.assert_called_once_with(0, None)

    def test_command_error_and_no_shell(self):
        import subprocess

        with patch.object(devices.subprocess, "run") as run:
            devices._run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertTrue(run.call_args.kwargs["check"])
        with patch.object(devices.subprocess, "run", side_effect=subprocess.TimeoutExpired("pactl", 10)):
            with self.assertRaises(RuntimeError):
                devices._run(["pactl"])

    def test_capabilities_do_not_claim_verification(self):
        with (
            patch.object(devices, "_backend", side_effect=RuntimeError("missing")),
            patch.object(devices.platform, "system", return_value="Linux"),
            patch.object(devices.shutil, "which", return_value=None),
        ):
            result = devices.capabilities()
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["playback_dependency_available"])
        self.assertIsNone(result["system_volume_adapter"])


if __name__ == "__main__":
    unittest.main()
