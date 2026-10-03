"""Optional audio playback and explicit host volume adapters."""

import importlib
import logging
import platform
import shutil
import subprocess

import numpy as np

log = logging.getLogger("groovescripting.devices")


def _backend():
    try:
        return importlib.import_module("sounddevice")
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Playback requires sounddevice and PortAudio; install groovescripting[playback]."
        ) from exc


def _rate(sample_rate):
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, (int, float))
        or not np.isfinite(sample_rate)
        or not 8000 <= sample_rate <= 192000
    ):
        raise ValueError("sample_rate must be between 8000 and 192000 Hz")


def _gain(volume):
    if (
        isinstance(volume, bool)
        or not isinstance(volume, (int, float))
        or not np.isfinite(volume)
        or not 0 <= volume <= 1
    ):
        raise ValueError("volume must be a finite scalar between 0 and 1")


def list_devices():
    """Return JSON serializable device mappings with stable backend indexes."""
    try:
        return [dict(device, index=i) for i, device in enumerate(_backend().query_devices())]
    except RuntimeError:
        raise
    except Exception as exc:
        log.exception("Device enumeration failed")
        raise RuntimeError(f"Cannot enumerate audio devices: {exc}") from exc


def diagnose(sample_rate=44100, device=None, channels=2):
    """Probe selected float32 settings without producing sound."""
    _rate(sample_rate)
    if channels not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    result = {"sample_rate": sample_rate, "channels": channels, "device": device, "supported": False}
    try:
        sd = _backend()
        result["output"] = dict(sd.query_devices(device, "output"))
        sd.check_output_settings(device=device, channels=channels, dtype="float32", samplerate=sample_rate)
        result["supported"] = True
    except Exception as exc:
        result["error"] = str(exc)
        log.info("Output diagnosis failed: %s", exc)
    return result


def play(data, sample_rate, device=None, volume=0.7, mute=False, repeat=1):
    """Play finite normalized audio; never change host master volume."""
    _rate(sample_rate)
    _gain(volume)
    if isinstance(repeat, bool) or not isinstance(repeat, int) or not 1 <= repeat <= 1000:
        raise ValueError("repeat must be an integer from 1 to 1000")
    samples = np.asarray(data, dtype=np.float32)
    if (
        samples.ndim not in (1, 2)
        or not len(samples)
        or (samples.ndim == 2 and samples.shape[1] not in (1, 2))
    ):
        raise ValueError("audio must be a nonempty mono or stereo array")
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) > 1:
        raise ValueError("audio samples must be finite and normalized to -1..1")
    sd = _backend()
    channels = 1 if samples.ndim == 1 else samples.shape[1]
    try:
        sd.check_output_settings(device=device, channels=channels, dtype="float32", samplerate=sample_rate)
        output = samples * (0 if mute else volume)
        log.info(
            "Playback rate=%s device=%s channels=%s repeat=%s mute=%s",
            sample_rate,
            device,
            channels,
            repeat,
            mute,
        )
        for _ in range(repeat):
            sd.play(output, samplerate=sample_rate, device=device)
            sd.wait()
    except KeyboardInterrupt:
        log.info("Playback interrupted")
        raise
    except Exception as exc:
        log.exception("Playback failed")
        raise RuntimeError(f"Audio playback failed: {exc}") from exc
    finally:
        sd.stop()


def test_tone(sample_rate=44100, device=None, volume=0.1, repeat=1, channels=1):
    _rate(sample_rate)
    _gain(volume)
    count = int(sample_rate * 0.5)
    tone = np.sin(2 * np.pi * 440 * np.arange(count) / sample_rate)
    fade = min(int(sample_rate * 0.01), count // 2)
    tone[:fade] *= np.linspace(0, 1, fade)
    tone[-fade:] *= np.linspace(1, 0, fade)
    if channels not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    if channels == 2:
        tone = np.repeat(tone[:, None], 2, axis=1)
    play(tone, sample_rate, device=device, volume=volume, repeat=repeat)


def capabilities():
    try:
        _backend()
        playback = True
    except RuntimeError:
        playback = False
    host = platform.system()
    adapter = None
    if host == "Linux":
        adapter = next((name for name in ("pactl", "amixer") if shutil.which(name)), None)
    elif host == "Darwin" and shutil.which("osascript"):
        adapter = "osascript"
    elif host == "Windows":
        try:
            importlib.import_module("pycaw.pycaw")
            adapter = "pycaw"
        except (ImportError, OSError):
            pass
    return {
        "platform": host,
        "playback_dependency_available": playback,
        "system_volume_adapter": adapter,
        "hardware_verified": False,
        "note": "Adapter availability does not verify hardware or session permissions; run diagnose.",
    }


def _run(args):
    log.info("System volume adapter: %s", args[0])
    try:
        subprocess.run(args, check=True, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"System volume command failed ({args[0]}): {exc}") from exc


def set_system_volume(volume=None, unmute=False):
    """Explicitly mutate host default output only when requested."""
    if volume is not None:
        _gain(volume)
    if volume is None and not unmute:
        raise ValueError("Specify volume or unmute=True for a system volume change")
    host = platform.system()
    if host == "Linux":
        if shutil.which("pactl"):
            adapter = "pactl"
            if volume is not None:
                _run([adapter, "set-sink-volume", "@DEFAULT_SINK@", f"{round(volume * 100)}%"])
            if unmute:
                _run([adapter, "set-sink-mute", "@DEFAULT_SINK@", "0"])
        elif shutil.which("amixer"):
            adapter = "amixer"
            args = [adapter, "-q", "sset", "Master"]
            if volume is not None:
                args.append(f"{round(volume * 100)}%")
            if unmute:
                args.append("unmute")
            _run(args)
        else:
            raise RuntimeError("Install pactl (PulseAudio/PipeWire) or amixer (ALSA) for system volume")
    elif host == "Darwin":
        adapter = "osascript"
        if not shutil.which(adapter):
            raise RuntimeError("macOS system volume requires osascript")
        if volume is not None:
            _run([adapter, "-e", f"set volume output volume {round(volume * 100)}"])
        if unmute:
            _run([adapter, "-e", "set volume output muted false"])
    elif host == "Windows":
        adapter = "pycaw"
        try:
            from pycaw.pycaw import AudioUtilities

            endpoint = AudioUtilities.GetSpeakers().EndpointVolume
            if volume is not None:
                endpoint.SetMasterVolumeLevelScalar(float(volume), None)
            if unmute:
                endpoint.SetMute(0, None)
        except Exception as exc:
            raise RuntimeError(
                "Windows system volume requires current pycaw/comtypes and an accessible default endpoint"
            ) from exc
    else:
        raise RuntimeError(f"System volume is unsupported on {host}; use your operating system mixer")
    return {"platform": host, "adapter": adapter, "volume": volume, "unmute": bool(unmute), "applied": True}
