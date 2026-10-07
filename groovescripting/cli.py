"""Shared CLI dispatcher and configuration resolution for eight tools."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

from . import __version__, diagnostics, presets

TOOLS = {
    "groovdrm": "drum",
    "groovbss": "bass",
    "groovld": "lead",
    "groovmix": "mix",
    "groovseq": "seq",
    "groovfx": "fx",
    "groovplay": "play",
    "groovinfo": "info",
    "groovmidi": "midi",
}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        logging.getLogger("groovescripting").error("Argument error: %s", message)
        super().error(message)


def number(low, high, integer=False):
    def convert(text):
        try:
            value = int(text) if integer else float(text)
            if not np.isfinite(value) or not low <= value <= high:
                raise ValueError()
            return value
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"must be {'an integer' if integer else 'a number'} in [{low}, {high}]"
            ) from None

    convert.bounds = (low, high, integer)
    return convert


def finish_parser(p, kind):
    defaults = dict(presets.DEFAULTS)
    if kind in ("bass", "lead"):
        defaults.update(presets.SOUND_DEFAULTS)
    descriptions = {
        "pattern": "Step pattern; notes C4 or C4+E4, drums x/X, rest ., tie ~; token[:beats[:velocity[:probability]]]",
        "events": "JSON explicit event array instead of a repeating pattern",
        "humanize": "Deterministic event timing jitter in seconds",
        "velocity_humanize": "Deterministic velocity jitter",
        "offset": "Timing offset in beats",
        "gain": "Linear synthesis gain",
        "tail": "cut keeps exact loop; full retains tails; wrap folds tails into loop",
        "track_offset": "Repeatable per-file offset in seconds; positional input order",
        "trim": "Repeatable per-file maximum length in seconds",
        "track_mute": "Mute one input by its 1-based index (repeatable)",
        "track_solo": "Solo one input by its 1-based index (repeatable)",
        "normalize": "Explicit peak normalization (mix 1.0; other renderers 0.95)",
        "limit": "Explicit hard clipping limiter (mix ±1.0; other renderers ±0.98)",
        "stems": "Export aligned pre-master stems; final effects/normalization/limiting remain on mixdown",
    }
    for action in p._actions:
        if action.help is argparse.SUPPRESS:
            continue
        text = action.help or descriptions.get(action.dest, action.dest.replace("_", " ").capitalize())
        bounds = getattr(action.type, "bounds", None)
        if bounds:
            text += f"; range {bounds[0]}..{bounds[1]}"
        if action.dest in defaults:
            text += f"; default {defaults[action.dest]}"
        action.help = text
    return p


def parser(tool):
    p = Parser(prog=tool, description=f"GrooveScripting {TOOLS[tool]} tool")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--log-file", metavar="PATH", help="append troubleshooting logs to a UTF-8 file")
    p.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info")
    p.add_argument("--log-format", choices=["text", "json"], default="text")
    p.add_argument("--json", action="store_true", help="machine-readable information/status")
    kind = TOOLS[tool]
    if kind == "midi":
        from .midi import parser as midi_parser

        return midi_parser()
    if kind == "info":
        p.add_argument("input")
        return finish_parser(p, kind)
    p.add_argument("--sample-rate", type=number(8000, 192000, True))
    p.add_argument("--channels", type=int, choices=[1, 2])
    p.add_argument("--device", help="output device index or name")
    p.add_argument("--volume", type=number(0, 1), default=0.7, help="application playback volume")
    p.add_argument("--mute", action="store_true")
    p.add_argument("--system-volume", type=number(0, 1), help="explicitly change OS master volume")
    p.add_argument("--system-unmute", action="store_true", help="explicitly clear OS master mute")
    p.add_argument(
        "--visualizer",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="draw an ASCII waveform in the terminal that follows playback (off by default)",
    )
    p.add_argument(
        "--visualizer-height",
        type=number(3, 40, True),
        default=9,
        help="waveform rows for --visualizer",
    )
    if kind == "play":
        p.add_argument("input", nargs="?")
        p.add_argument("--devices", action="store_true")
        p.add_argument("--diagnose", action="store_true")
        p.add_argument("--test-tone", action="store_true")
        p.add_argument("--repeat", type=number(1, 1000, True), default=1)
        return finish_parser(p, kind)
    p.add_argument("--output", "-o")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--format", choices=["wav", "flac"])
    p.add_argument("--subtype", choices=["PCM_16", "PCM_24", "FLOAT"], default="PCM_16")
    p.add_argument("--play", action="store_true")
    p.add_argument("--play-only", action="store_true")
    p.add_argument("--tail", choices=["cut", "full", "wrap"], default="cut")
    p.add_argument(
        "--effect",
        action="append",
        default=[],
        metavar="JSON",
        help='ordered effect object, e.g. {"type":"delay"}',
    )
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--limit", action="store_true")
    if kind in ("drum", "bass", "lead"):
        for name, low, high, integer in [
            ("bpm", 1, 1000, False),
            ("bars", 1, 1024, True),
            ("beats", 1, 32, True),
            ("subdivision", 1, 64, True),
            ("swing", 0, 0.49, False),
            ("offset", -128, 128, False),
            ("seed", 0, 2**63 - 1, True),
            ("gain", 0, 4, False),
            ("pan", -1, 1, False),
            ("transpose", -96, 96, True),
            ("humanize", 0, 0.1, False),
            ("velocity-humanize", 0, 0.5, False),
        ]:
            if kind != "drum" or name != "transpose":
                p.add_argument("--" + name, type=number(low, high, integer))
        p.add_argument("--variation", type=number(0, 1))
        p.add_argument("--density", type=number(0, 1))
        p.add_argument("--pattern")
        p.add_argument("--events", metavar="PATH")
        if kind != "drum":
            p.add_argument("--frequency", type=number(10, 20000), help="single frequency event in Hz")
        if kind != "drum":
            p.add_argument("--scale", choices=["none", "major", "minor", "pentatonic", "chromatic"])
            p.add_argument("--root")
        p.add_argument("--preset", metavar="NAME_OR_PATH")
        p.add_argument("--save-preset", metavar="PATH")
        p.add_argument("--list-presets", action="store_true")
        p.add_argument("--inspect-preset", action="store_true")
        for name, lo, hi in [
            ("attack", 0, 10),
            ("decay", 0.001, 10),
            ("sustain", 0, 1),
            ("release", 0, 10),
            ("cutoff", 10, 20000),
            ("resonance", 0, 1),
            ("saturation", 0, 10),
        ]:
            if kind != "drum" or name not in ("sustain", "release"):
                p.add_argument("--" + name, type=number(lo, hi))
        if kind == "drum":
            p.add_argument(
                "--voice", choices=["kick", "snare", "closed_hat", "open_hat", "clap", "tom", "rim"]
            )
            p.add_argument("--pitch", type=number(10, 20000))
            p.add_argument("--pitch-envelope", type=number(0, 24))
            p.add_argument("--tone-noise", type=number(0, 1))
            p.add_argument("--drum-pattern", action="append", default=[], metavar="VOICE=PATTERN")
            p.add_argument("--drum-param", action="append", default=[], metavar="VOICE.KEY=VALUE")
            p.add_argument("--ghost-notes", type=number(0, 1))
            p.add_argument("--fill-every", type=number(0, 128, True))
        else:
            p.add_argument("--waveform", choices=["sine", "triangle", "saw", "pulse", "square"])
            for name, lo, hi in [
                ("filter-attack", 0, 10),
                ("filter-decay", 0.001, 10),
                ("filter-sustain", 0, 1),
                ("filter-release", 0, 10),
                ("filter-amount", -8, 8),
                ("glide", 0, 5),
                ("sub-mix", 0, 1),
                ("detune", -100, 100),
                ("pulse-width", 0.05, 0.95),
                ("lfo-rate", 0, 100),
                ("lfo-depth", 0, 8),
                ("unison-detune", 0, 100),
                ("vibrato-rate", 0, 30),
                ("vibrato-depth", 0, 200),
                ("arp-rate", 0.01, 16),
            ]:
                if kind == "lead" or name not in ("unison-detune", "arp-rate"):
                    p.add_argument("--" + name, type=number(lo, hi))
            p.add_argument("--legato", action=argparse.BooleanOptionalAction, default=None)
            if kind == "lead":
                p.add_argument("--voices", type=number(1, 32, True))
                p.add_argument("--unison", type=number(1, 8, True))
                p.add_argument("--arp", choices=["off", "up", "down", "random"])
                p.add_argument("--mode", choices=["mono", "poly"])
    elif kind == "seq":
        p.add_argument("project")
        for name, lo, hi, integer in [
            ("bpm", 1, 1000, False),
            ("bars", 1, 1024, True),
            ("beats", 1, 32, True),
            ("subdivision", 1, 64, True),
            ("swing", 0, 0.49, False),
            ("seed", 0, 2**63 - 1, True),
            ("humanize", 0, 0.1, False),
            ("velocity-humanize", 0, 0.5, False),
        ]:
            p.add_argument("--" + name, type=number(lo, hi, integer))
        p.add_argument("--stems", metavar="DIRECTORY")
    elif kind == "mix":
        p.add_argument("inputs", nargs="+")
        for name in ["track-gain", "track-pan", "track-offset", "trim"]:
            p.add_argument("--" + name, type=float, action="append", default=[])
        p.add_argument("--stems", metavar="DIRECTORY")
        p.add_argument(
            "--track-mute", action="append", type=number(1, 10000, True), default=[], metavar="INDEX"
        )
        p.add_argument(
            "--track-solo", action="append", type=number(1, 10000, True), default=[], metavar="INDEX"
        )
    elif kind == "fx":
        p.add_argument("input")
        p.add_argument("--preset", help="version 1 effect preset JSON")
        p.add_argument("--save-preset")
    return finish_parser(p, kind)


def json_data(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def emit(item, as_json=False):
    if as_json:
        print(json.dumps(item, ensure_ascii=True, allow_nan=False))
    elif isinstance(item, list):
        print("\n".join(map(str, item)))
    else:
        print(json.dumps(item, indent=2, ensure_ascii=True, allow_nan=False))


def early_logs(argv):
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--log-file")
    pre.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info")
    pre.add_argument("--log-format", choices=["text", "json"], default="text")
    options, _ = pre.parse_known_args(argv)
    if not options.log_file and any(a.startswith(("--log-level", "--log-format")) for a in argv):
        raise ValueError("--log-level and --log-format require --log-file")
    return diagnostics.configure(options.log_file, options.log_level, options.log_format)


def render_options(args, kind):
    keys = set(presets.DEFAULTS) | set(presets.SOUND_DEFAULTS) | presets.EXTRA
    overrides = {key: value for key, value in vars(args).items() if key in keys and value is not None}
    overrides.pop("tail", None)
    if args.events and (args.pattern or getattr(args, "frequency", None)):
        raise ValueError("--events cannot be combined with --pattern or --frequency")
    if args.pattern and getattr(args, "frequency", None):
        raise ValueError("--pattern cannot be combined with --frequency")
    if args.events:
        overrides["events"] = json_data(args.events)
    if getattr(args, "frequency", None):
        if kind == "drum":
            raise ValueError("--frequency is for bass/lead; use --pitch for drums")
        overrides["events"] = [
            dict(beat=0, duration=1, notes=[{"hz": args.frequency}], velocity=1, probability=1)
        ]
    if kind == "drum":
        patterns = {}
        for item in args.drum_pattern:
            voice, sep, pattern = item.partition("=")
            if not sep:
                raise ValueError("--drum-pattern requires VOICE=PATTERN")
            patterns[voice] = pattern
        if patterns:
            overrides["drum_patterns"] = patterns
        params = {}
        for item in args.drum_param:
            name, sep, value = item.partition("=")
            voice, dot, key = name.partition(".")
            if (
                not sep
                or not dot
                or key
                not in {
                    "pitch",
                    "pitch_envelope",
                    "tone_noise",
                    "attack",
                    "decay",
                    "cutoff",
                    "resonance",
                    "saturation",
                    "gain",
                    "pan",
                }
            ):
                raise ValueError("--drum-param requires VOICE.KEY=VALUE with a supported parameter")
            params.setdefault(voice, {})[key] = float(value)
        if params:
            overrides["drum_params"] = params
    result = presets.resolve(kind, args.preset, overrides)
    if kind == "drum" and (args.pattern is not None or args.voice is not None) and not args.drum_pattern:
        result.pop("drum_patterns", None)
    # Validate preset/project values using the exact same CLI validators.
    for action in parser({"drum": "groovdrm", "bass": "groovbss", "lead": "groovld"}[kind])._actions:
        if action.dest in result and action.type is not None:
            try:
                result[action.dest] = action.type(str(result[action.dest]))
            except (ValueError, argparse.ArgumentTypeError) as error:
                raise ValueError(f"Invalid {action.dest}: {error}") from error
        if action.dest in result and action.choices is not None and result[action.dest] not in action.choices:
            raise ValueError(f"Invalid {action.dest}: expected one of {action.choices}")
    # Approximate explicit acoustic tail; effects perform their own precise tail handling.
    result["tail"] = (
        max(float(result.get("release", 0.12)), float(result.get("decay", 0.35)) * 8 if kind == "drum" else 0)
        if args.tail in ("full", "wrap")
        else 0
    )
    return result


def device_id(value):
    return int(value) if value and value.isdigit() else value


def playback(args, data, sr):
    from . import devices

    if args.system_volume is not None or args.system_unmute:
        devices.set_system_volume(args.system_volume, args.system_unmute)
    devices.play(
        data,
        sr,
        device=device_id(args.device),
        volume=args.volume,
        mute=args.mute,
        repeat=getattr(args, "repeat", 1),
        visualize=args.visualizer,
        visualizer_height=args.visualizer_height,
    )


def execute(tool, args, logger):
    from . import audio, effects

    kind = TOOLS[tool]
    if (
        kind not in ("play", "info")
        and (args.system_volume is not None or args.system_unmute)
        and not (args.play or args.play_only)
    ):
        raise ValueError("System volume flags require --play or --play-only")
    if kind not in ("play", "info") and args.visualizer and not (args.play or args.play_only):
        raise ValueError("--visualizer requires --play or --play-only")
    if kind == "info":
        path = Path(args.input)
        if path.suffix.lower() == ".json":
            item = json_data(path)
            if isinstance(item, dict) and "tracks" in item:
                from .projects import validate_project

                validate_project(item)
            elif isinstance(item, dict) and item.get("instrument") in ("drum", "bass", "lead"):
                item = presets.load(item["instrument"], str(path))
            elif (
                isinstance(item, dict) and item.get("version") == 1 and isinstance(item.get("effects"), list)
            ):
                effects.validate(item["effects"])
            else:
                raise ValueError("Expected a valid version 1 preset or project")
        else:
            item = audio.info(path)
        emit(item, args.json)
        return
    if kind == "play":
        from . import devices

        if (args.devices or args.diagnose) and (args.system_volume is not None or args.system_unmute):
            raise ValueError("System volume changes cannot be combined with --devices or --diagnose")
        if (args.devices or args.diagnose) and args.visualizer:
            raise ValueError("--visualizer cannot be combined with --devices or --diagnose")
        if args.devices:
            emit(devices.list_devices(), args.json)
        elif args.diagnose:
            emit(
                devices.diagnose(
                    args.sample_rate or 44100, device_id(args.device), channels=args.channels or 2
                ),
                args.json,
            )
        elif args.test_tone:
            if args.volume > 0.2:
                logger.info("Test tone uses conservative application volume 0.1")
            if args.system_volume is not None or args.system_unmute:
                devices.set_system_volume(args.system_volume, args.system_unmute)
            devices.test_tone(
                args.sample_rate or 44100,
                device_id(args.device),
                volume=0 if args.mute else min(args.volume, 0.1),
                repeat=args.repeat,
                channels=args.channels or 1,
                visualize=args.visualizer,
            )
        elif args.input:
            data, sr = audio.read(args.input)
            if (args.sample_rate and args.sample_rate != sr) or (
                args.channels and args.channels != data.shape[1]
            ):
                target = args.sample_rate or sr
                data, _ = audio.mix(
                    [{"data": data, "sample_rate": sr}], target, args.channels or data.shape[1]
                )
                sr = target
            playback(args, data, sr)
        elif args.system_volume is not None or args.system_unmute:
            emit(devices.set_system_volume(args.system_volume, args.system_unmute), args.json)
        else:
            raise ValueError("Supply an audio file, --devices, --diagnose, --test-tone or system volume flag")
        return
    fx_chain = [json.loads(item) for item in args.effect]
    stems = {}
    if kind in ("drum", "bass", "lead"):
        from .synth import render

        if args.list_presets:
            emit(presets.names(kind), args.json)
            return
        if args.inspect_preset:
            if not args.preset:
                raise ValueError("--inspect-preset requires --preset")
            emit(presets.load(kind, args.preset), args.json)
            return
        options = render_options(args, kind)
        logger.debug("Resolved configuration: %s", json.dumps(options, ensure_ascii=False))
        if args.save_preset:
            saved = dict(options)
            saved.pop("tail", None)
            presets.save(args.save_preset, kind, saved, args.overwrite)
        data = render(kind, options)
        sr = options["sample_rate"]
        if args.tail == "wrap":
            from .music import beat_frame

            frames = beat_frame(options["bars"] * options["beats"], options["bpm"], sr)
            wrapped = np.array(data[:frames], copy=True)
            for start in range(frames, len(data), frames):
                part = data[start : start + frames]
                wrapped[: len(part)] += part
            data = wrapped
    elif kind == "seq":
        from .projects import render_project
        from .synth import render

        project = json_data(args.project)
        for key in ("bpm", "bars", "beats", "subdivision", "swing", "seed", "humanize", "velocity_humanize"):
            if getattr(args, key, None) is not None:
                project[key] = getattr(args, key)
        if args.sample_rate is not None:
            project["sample_rate"] = args.sample_rate
        if args.channels is not None:
            project["channels"] = args.channels
        data, sr, stems = render_project(project, render, tail=args.tail)
    elif kind == "mix":
        sr = args.sample_rate or 44100
        tracks = []
        for flag in ["track_gain", "track_pan", "track_offset", "trim"]:
            if len(getattr(args, flag)) > len(args.inputs):
                raise ValueError("Too many --" + flag.replace("_", "-") + " values")
        for i, path in enumerate(args.inputs):
            track = {"path": path, "mute": i + 1 in args.track_mute, "solo": i + 1 in args.track_solo}
            if any(n > len(args.inputs) for n in args.track_mute + args.track_solo):
                raise ValueError("Track indices are 1-based and must reference an input file")
            for key, flag, default in [
                ("gain", "track_gain", 1),
                ("pan", "track_pan", 0),
                ("offset_seconds", "track_offset", 0),
                ("trim_seconds", "trim", None),
            ]:
                values = getattr(args, flag)
                track[key] = values[i] if i < len(values) else default
            tracks.append(track)
        data, report = audio.mix(tracks, sr, args.channels or 2, normalize=args.normalize, limit=args.limit)
        logger.info("Mix report %s", report)
        solo = any(t.get("solo") and not t.get("mute") for t in tracks)
        for i, track in enumerate(tracks):
            padded = np.zeros((len(data), data.shape[1]))
            if not track["mute"] and (not solo or track["solo"]):
                stem, _ = audio.mix([track], sr, args.channels or 2)
                padded[: min(len(stem), len(padded))] = stem[: len(padded)]
            stems[f"track_{i + 1}"] = padded
    else:
        data, sr = audio.read(args.input)
        if args.preset:
            preset = json_data(args.preset)
            if (
                not isinstance(preset, dict)
                or preset.get("version") != 1
                or not isinstance(preset.get("effects"), list)
            ):
                raise ValueError("Effect preset requires version 1 and effects array")
            fx_chain = preset["effects"] + fx_chain
        if args.save_preset:
            with Path(args.save_preset).open("w" if args.overwrite else "x", encoding="utf-8") as stream:
                json.dump({"version": 1, "effects": fx_chain}, stream, indent=2)
        if args.sample_rate and args.sample_rate != sr:
            data, _ = audio.mix(
                [{"data": data, "sample_rate": sr}], args.sample_rate, args.channels or data.shape[1]
            )
            sr = args.sample_rate
        elif args.channels and args.channels != data.shape[1]:
            data, _ = audio.mix([{"data": data, "sample_rate": sr}], sr, args.channels)
    if fx_chain:
        data = effects.apply(data, sr, fx_chain, tail=args.tail)
    if args.normalize and kind != "mix":
        peak = float(np.max(np.abs(data))) if data.size else 0
        if peak:
            data = data * 0.95 / peak
    if args.limit and kind != "mix":
        data = np.clip(data, -0.98, 0.98)
    if not np.isfinite(data).all():
        raise RuntimeError("Non-finite output rejected")
    peak = float(np.max(np.abs(data))) if data.size else 0
    clipping = int(np.count_nonzero(np.abs(data) > 1))
    logger.info(
        "Rendered frames=%d channels=%d sample_rate=%d peak=%.6f clipping=%d",
        len(data),
        data.shape[1],
        sr,
        peak,
        clipping,
    )
    if clipping:
        print(
            f"Output exceeds digital full scale ({clipping} samples); integer exports clip. Use --limit or --normalize.",
            file=sys.stderr,
        )
    output = args.output or tool + ".wav"
    fmt = args.format or ("flac" if Path(output).suffix.lower() == ".flac" else "wav")
    if fmt == "flac" and args.subtype == "FLOAT":
        raise ValueError("FLAC does not support FLOAT; select PCM_16 or PCM_24")
    if not args.play_only:
        audio.write(output, data, sr, overwrite=args.overwrite, format=fmt, subtype=args.subtype)
    if getattr(args, "stems", None):
        directory = Path(args.stems)
        directory.mkdir(parents=True, exist_ok=True)
        for name, stem in stems.items():
            safe = "".join(char if char.isalnum() or char in "_-" else "_" for char in name)
            audio.write(directory / (safe + ".wav"), stem, sr, overwrite=args.overwrite)
    if args.play or args.play_only:
        playback(args, data, sr)
    elif args.system_volume is not None or args.system_unmute:
        raise ValueError("System volume flags require --play or --play-only for rendering commands")
    emit(
        {
            "output": None if args.play_only else output,
            "frames": len(data),
            "sample_rate": sr,
            "channels": data.shape[1],
            "peak": peak,
            "clipping": clipping,
        },
        args.json,
    )


def run(tool, argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    logger = handler = None
    started = time.perf_counter()
    try:
        logger, handler = early_logs(argv)
        logger.info("Starting %s", tool)
        args = parser(tool).parse_args(argv)
        logger.debug("Parsed arguments: %s", vars(args))
        execute(tool, args, logger)
        logger.info("Completed %s elapsed_seconds=%.6f", tool, time.perf_counter() - started)
        return 0
    except KeyboardInterrupt:
        if logger:
            logger.warning("Interrupted %s", tool)
        return 130
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        if logger:
            logger.exception("Invalid input: %s", error)
        print(f"{tool}: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ImportError) as error:
        if logger:
            logger.exception("Operation failed: %s", error)
        print(f"{tool}: {error}", file=sys.stderr)
        return 1
    finally:
        if logger and handler:
            diagnostics.close(logger, handler)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: python -m groovescripting TOOL [flags]\nTools: " + ", ".join(TOOLS))
        return 0
    if argv[0] == "--version":
        print(__version__)
        return 0
    tool = argv.pop(0)
    if tool == "groovmidi":
        from .midi import cli as midi_cli

        return midi_cli(argv)
    if tool not in TOOLS:
        print("Unknown tool: " + tool, file=sys.stderr)
        return 2
    return run(tool, argv)


if __name__ == "__main__":
    raise SystemExit(main())


def drm():
    return run("groovdrm")


def bss():
    return run("groovbss")


def ld():
    return run("groovld")


def mix():
    return run("groovmix")


def seq():
    return run("groovseq")


def fx():
    return run("groovfx")


def play():
    return run("groovplay")


def info():
    return run("groovinfo")
