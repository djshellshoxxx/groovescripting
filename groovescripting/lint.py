"""groovlint: deterministic structural and signal-integrity checks for projects, presets and audio.

Findings are measurable facts with stable rule IDs. The linter never modifies inputs, never opens a
playback device and makes no judgment about musical quality.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from . import __version__, diagnostics, presets, projects
from .music import beat_frame
from .validation import RANGES

SCHEMA_VERSION = 1
MAX_JSON_BYTES = 5_000_000
RENDER_FRAME_BUDGET = 10_000_000
ANALYSIS_BLOCK = 65_536
SEVERITIES = ("note", "warning", "error")
CATEGORY_ORDER = {"project": 0, "render": 1, "audio": 2}
FULL_SCALE = 1.0 - 2.0**-15

RULES = {
    "PRJ001": ("error", "project", "Project or preset parsing or schema validation fails."),
    "PRJ002": ("warning", "render", "A render request exceeds the per-render frame budget."),
    "PRJ003": ("note", "project", "A configured option has no audible effect in this path."),
    "PRJ004": ("warning", "project", "A value sits at a documented cost boundary."),
    "AUD001": ("warning", "audio", "Decoded samples reach digital full scale."),
    "AUD002": ("note", "audio", "Peak is below the near-silence threshold."),
    "AUD003": ("note", "audio", "Mean (DC) offset exceeds the threshold."),
    "AUD004": ("warning", "audio", "First or last sample jumps from or to silence."),
    "AUD005": ("warning", "audio", "A channel is silent or far lower than the other."),
    "AUD006": ("note", "audio", "Sample rate, channels or duration fall outside the target profile."),
}

DEFAULT_THRESHOLDS = {
    "version": 1,
    "audio": {
        "near_silence_dbfs": -90.0,
        "dc_offset_peak": 0.01,
        "boundary_jump_peak": 0.25,
        "channel_rms_ratio_db": -45.0,
        "channel_rms_floor_dbfs": -90.0,
    },
    "targets": {"sample_rate_hz": None, "channels": None, "duration_seconds": None},
}
THRESHOLD_RANGES = {
    "near_silence_dbfs": (-200.0, 0.0),
    "dc_offset_peak": (0.0, 1.0),
    "boundary_jump_peak": (0.0, 2.0),
    "channel_rms_ratio_db": (-200.0, 0.0),
    "channel_rms_floor_dbfs": (-200.0, 0.0),
}
TARGET_RANGES = {"sample_rate_hz": (8000, 384000), "channels": (1, 2), "duration_seconds": (0.0, 86400.0)}
COST_BOUNDARIES = ("voices", "unison", "bars", "subdivision", "bpm", "beats")


class LintInputError(ValueError):
    """Malformed or unreadable input: exit code 2."""


def dbfs(value):
    return -math.inf if value <= 0 else round(20 * math.log10(value), 4)


def _json_number(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def finding(rule_id, message, evidence, location=None, suggestion=None, confidence="high"):
    severity, category, _ = RULES[rule_id]
    return dict(
        rule_id=rule_id,
        severity=severity,
        category=category,
        message=message,
        location=location,
        evidence={k: _json_number(v) for k, v in evidence.items()},
        suggestion=suggestion,
        confidence=confidence,
    )


def load_thresholds(path=None):
    profile = json.loads(json.dumps(DEFAULT_THRESHOLDS))
    if path is None:
        return profile
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise LintInputError("thresholds profile requires version 1")
    unknown = set(data) - {"version", "audio", "targets"}
    if unknown:
        raise LintInputError("unknown thresholds keys: " + ", ".join(sorted(unknown)))
    for group, ranges, nullable in (("audio", THRESHOLD_RANGES, False), ("targets", TARGET_RANGES, True)):
        values = data.get(group, {})
        if not isinstance(values, dict):
            raise LintInputError(f"thresholds {group} must be an object")
        unknown = set(values) - set(ranges)
        if unknown:
            raise LintInputError(f"unknown thresholds {group} keys: " + ", ".join(sorted(unknown)))
        for key, value in values.items():
            if value is None and nullable:
                profile[group][key] = None
                continue
            low, high = ranges[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise LintInputError(f"thresholds {group}.{key} must be a finite number")
            if not low <= value <= high:
                raise LintInputError(f"thresholds {group}.{key} must be within [{low}, {high}]")
            if key == "channels" and int(value) != value:
                raise LintInputError("thresholds targets.channels must be an integer")
            profile[group][key] = value
    return profile


def _read_json(path):
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as error:
        raise LintInputError(f"cannot read {path}: {error.strerror or error}") from error
    if size > MAX_JSON_BYTES:
        raise LintInputError(f"{path} is {size} bytes; the project size limit is {MAX_JSON_BYTES} bytes")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LintInputError(f"invalid JSON: {error}") from error


def _ineffective(params, instrument, pointer):
    """PRJ003 checks derived from the renderer contract in synth.render."""
    out = []

    def add(key, why):
        out.append(
            finding(
                "PRJ003",
                f"{key} has no audible effect: {why}.",
                {"option": key, "value": params[key]},
                location=f"{pointer}/{key}",
                suggestion=f"Remove {key} or enable the feature it modulates.",
            )
        )

    if instrument == "drum":
        if "resonance" in params and "cutoff" not in params:
            add("resonance", "drum resonance only applies when cutoff is set")
        return out
    if "pulse_width" in params and params.get("waveform", "saw") not in ("pulse", "square"):
        add("pulse_width", "only pulse and square waveforms use pulse width")
    if "lfo_rate" in params and not params.get("lfo_depth", 0):
        add("lfo_rate", "lfo_depth is 0")
    if "vibrato_rate" in params and not params.get("vibrato_depth", 0):
        add("vibrato_rate", "vibrato_depth is 0")
    for key in ("filter_attack", "filter_decay", "filter_sustain", "filter_release"):
        if key in params and not params.get("filter_amount", 0):
            add(key, "filter_amount is 0")
    if instrument == "lead":
        if "arp_rate" in params and params.get("arp", "off") == "off":
            add("arp_rate", "arp is off")
        if "unison_detune" in params and params.get("unison", 1) == 1:
            add("unison_detune", "unison is 1")
        if "glide" in params and params.get("glide") and params.get("mode", "poly") != "mono":
            add("glide", "glide applies only to monophonic voices")
    return out


def _boundaries(values, pointer):
    out = []
    for key in COST_BOUNDARIES:
        if key in values and key in RANGES and values[key] == RANGES[key][1]:
            out.append(
                finding(
                    "PRJ004",
                    f"{key} is at its supported maximum.",
                    {"option": key, "value": values[key], "maximum": RANGES[key][1]},
                    location=f"{pointer}/{key}" if pointer else f"/{key}",
                    suggestion="Expect the highest render cost for this setting.",
                )
            )
    return out


def lint_preset(data):
    if not isinstance(data, dict) or data.get("instrument") not in ("drum", "bass", "lead"):
        raise LintInputError("preset requires an instrument of drum, bass or lead")
    try:
        if data.get("version") != 1 or not isinstance(data.get("params"), dict):
            raise ValueError("preset requires version 1 and a params object")
        presets.validate_instrument_params(data["instrument"], data["params"])
    except ValueError as error:
        raise LintInputError(str(error)) from error
    params = data["params"]
    return _ineffective(params, data["instrument"], "/params") + _boundaries(params, "/params"), {
        "instrument": data["instrument"]
    }


def lint_project(data):
    try:
        projects.validate(data)
    except (ValueError, TypeError, KeyError) as error:
        raise LintInputError(str(error)) from error
    out = _boundaries(data, "")
    sr = data.get("sample_rate", 44100)
    bpm = data.get("bpm", 120)
    total_frames = 0
    for i, track in enumerate(data["tracks"]):
        params = presets.resolve(track["instrument"], track.get("preset"), track.get("params", {}))
        explicit = dict(track.get("params", {}))
        out += _ineffective(explicit, track["instrument"], f"/tracks/{i}/params")
        out += _boundaries(params, f"/tracks/{i}/params")
        if track.get("mute"):
            out.append(
                finding(
                    "PRJ003",
                    f"Track {track['name']!r} is muted and renders silence.",
                    {"track": track["name"], "mute": True},
                    location=f"/tracks/{i}/mute",
                )
            )
    flagged = set()
    for step in projects.expand(data):
        total_frames += step["target"]
        frames = beat_frame(step["bars"] * data.get("beats", 4), bpm, sr)
        if frames > RENDER_FRAME_BUDGET and step["section_index"] not in flagged:
            flagged.add(step["section_index"])
            out.append(
                finding(
                    "PRJ002",
                    "A section render exceeds the per-render frame budget and will be rejected.",
                    {
                        "frames": frames,
                        "budget_frames": RENDER_FRAME_BUDGET,
                        "section_index": step["section_index"],
                    },
                    location=f"/sections/{step['section_index']}" if data.get("sections") else "/bars",
                    suggestion="Split the section into shorter sections or lower the sample rate.",
                )
            )
    metrics = dict(
        tracks=len(data["tracks"]),
        sections=len(data.get("sections") or [None]),
        sample_rate_hz=sr,
        estimated_frames=total_frames,
        estimated_duration_seconds=round(total_frames / sr, 6),
    )
    return out, metrics


def audio_metrics(path, block=ANALYSIS_BLOCK):
    """Bounded-memory statistics read through fixed-size blocks."""
    try:
        meta = sf.info(str(path))
    except (RuntimeError, sf.LibsndfileError) as error:
        raise LintInputError(f"unreadable audio {path}: {error}") from error
    channels = meta.channels
    peak = np.zeros(channels)
    total = np.zeros(channels)
    squares = np.zeros(channels)
    clipped = 0
    frames = 0
    first = last = None
    for chunk in sf.blocks(str(path), blocksize=block, dtype="float64", always_2d=True):
        if not np.isfinite(chunk).all():
            raise LintInputError("audio contains non-finite samples")
        if first is None and len(chunk):
            first = chunk[0].copy()
        if len(chunk):
            last = chunk[-1].copy()
        peak = np.maximum(peak, np.max(np.abs(chunk), axis=0))
        total += chunk.sum(axis=0)
        squares += (chunk * chunk).sum(axis=0)
        clipped += int(np.count_nonzero(np.abs(chunk) >= FULL_SCALE))
        frames += len(chunk)
    zeros = np.zeros(channels)
    return dict(
        sample_rate_hz=meta.samplerate,
        channels=channels,
        frames=frames,
        duration_seconds=round(frames / meta.samplerate, 6),
        subtype=meta.subtype,
        peak=peak.tolist(),
        mean=(total / frames if frames else zeros).tolist(),
        rms=(np.sqrt(squares / frames) if frames else zeros).tolist(),
        clipped_sample_count=clipped,
        first=(first if first is not None else zeros).tolist(),
        last=(last if last is not None else zeros).tolist(),
        window_frames=block,
    )


def lint_audio(path, thresholds):
    m = audio_metrics(path)
    a, targets = thresholds["audio"], thresholds["targets"]
    out = []
    peak = max(m["peak"]) if m["peak"] else 0.0
    scope = "all channels"
    if m["clipped_sample_count"]:
        out.append(
            finding(
                "AUD001",
                "Samples reach the digital full-scale boundary.",
                dict(
                    peak_dbfs=dbfs(peak),
                    clipped_sample_count=m["clipped_sample_count"],
                    threshold_dbfs=dbfs(FULL_SCALE),
                    channel_scope=scope,
                ),
                suggestion="Inspect the source mix and export headroom.",
            )
        )
    if m["frames"] and dbfs(peak) < a["near_silence_dbfs"]:
        out.append(
            finding(
                "AUD002",
                "The file peak is below the near-silence threshold.",
                dict(peak_dbfs=dbfs(peak), threshold_dbfs=a["near_silence_dbfs"], channel_scope=scope),
                suggestion="Check muted tracks, gain staging or the render length.",
            )
        )
    for channel, mean in enumerate(m["mean"]):
        if abs(mean) > a["dc_offset_peak"]:
            out.append(
                finding(
                    "AUD003",
                    f"Channel {channel + 1} has a mean (DC) offset above the threshold.",
                    dict(mean=round(mean, 9), threshold=a["dc_offset_peak"], channel=channel + 1),
                    suggestion="Apply a high-pass filter or inspect the source for offsets.",
                )
            )
    for boundary, values in (("start", m["first"]), ("end", m["last"])):
        jump = max(abs(v) for v in values) if values else 0.0
        if jump > a["boundary_jump_peak"]:
            out.append(
                finding(
                    "AUD004",
                    f"The {boundary} sample jumps {jump:.4f} from or to silence.",
                    dict(
                        boundary=boundary,
                        jump_peak=round(jump, 9),
                        threshold=a["boundary_jump_peak"],
                        window_frames=1,
                        channel_scope=scope,
                    ),
                    suggestion="Add a short fade at the boundary if it is not an intended loop point.",
                    confidence="medium",
                )
            )
    if m["channels"] == 2 and m["frames"]:
        levels = [dbfs(r) for r in m["rms"]]
        loud, quiet = max(levels), min(levels)
        ratio = quiet - loud if math.isfinite(loud) and math.isfinite(quiet) else -math.inf
        if loud >= a["channel_rms_floor_dbfs"] and (
            quiet < a["channel_rms_floor_dbfs"] or ratio < a["channel_rms_ratio_db"]
        ):
            out.append(
                finding(
                    "AUD005",
                    f"Channel {levels.index(quiet) + 1} is silent or far quieter than the other.",
                    dict(
                        rms_dbfs_left=levels[0],
                        rms_dbfs_right=levels[1],
                        ratio_db=ratio,
                        ratio_threshold_db=a["channel_rms_ratio_db"],
                        floor_dbfs=a["channel_rms_floor_dbfs"],
                    ),
                    suggestion="Check pan settings and stereo routing.",
                )
            )
    for key, observed in (
        ("sample_rate_hz", m["sample_rate_hz"]),
        ("channels", m["channels"]),
        ("duration_seconds", m["duration_seconds"]),
    ):
        expected = targets.get(key)
        if expected is not None and not math.isclose(observed, expected, rel_tol=0, abs_tol=1e-6):
            out.append(
                finding(
                    "AUD006",
                    f"{key} differs from the target profile.",
                    dict(target=key, observed=observed, expected=expected),
                )
            )
    metrics = dict(
        sample_rate_hz=m["sample_rate_hz"],
        channels=m["channels"],
        frames=m["frames"],
        duration_seconds=m["duration_seconds"],
        peak_dbfs=dbfs(peak),
        rms_dbfs=[dbfs(r) for r in m["rms"]],
        analysis_window_frames=m["window_frames"],
    )
    return out, {
        k: _json_number(v) if not isinstance(v, list) else [_json_number(x) for x in v]
        for k, v in metrics.items()
    }


def _sort_key(item):
    return (CATEGORY_ORDER[item["category"]], item["location"] or "", item["rule_id"], item["message"])


def select(findings, only=None, ignore=None):
    if only:
        findings = [f for f in findings if f["rule_id"] in only]
    if ignore:
        findings = [f for f in findings if f["rule_id"] not in ignore]
    return sorted(findings, key=_sort_key)


def is_audio(path):
    return Path(path).suffix.lower() in (".wav", ".flac")


def analyze(input_path, audio_path=None, thresholds=None, only=None, ignore=None):
    """Return (report, has_input_error). Malformed inputs produce a PRJ001 finding."""
    thresholds = thresholds or load_thresholds()
    findings, metrics, kind, error = [], {}, None, False
    if is_audio(input_path):
        if audio_path:
            raise LintInputError("--audio cannot be combined with an audio INPUT")
        kind = "audio"
        found, metrics = lint_audio(input_path, thresholds)
        findings += found
    else:
        try:
            data = _read_json(input_path)
            if isinstance(data, dict) and "tracks" not in data and "instrument" in data:
                kind = "preset"
                found, metrics = lint_preset(data)
            else:
                kind = "project"
                found, metrics = lint_project(data)
            findings += found
        except LintInputError as problem:
            error = True
            kind = kind or "project"
            findings.append(
                finding(
                    "PRJ001",
                    "Parsing or schema validation failed.",
                    {"validator_message": str(problem), "path": Path(input_path).as_posix()},
                    location="",
                    suggestion="Fix the reported field and lint again.",
                )
            )
        if audio_path and not error:
            found, audio_metric = lint_audio(audio_path, thresholds)
            findings += found
            metrics = dict(metrics, audio=audio_metric)
    findings = select(findings, only, ignore)
    summary = {
        "errors": sum(f["severity"] == "error" for f in findings),
        "warnings": sum(f["severity"] == "warning" for f in findings),
        "notes": sum(f["severity"] == "note" for f in findings),
    }
    inputs = {"path": Path(input_path).as_posix(), "kind": kind}
    if audio_path:
        inputs["audio"] = Path(audio_path).as_posix()
    return (
        dict(
            schema_version=SCHEMA_VERSION,
            tool="groovlint",
            input=inputs,
            summary=summary,
            metrics=metrics,
            findings=findings,
        ),
        error,
    )


def text_report(report):
    lines = [f"groovlint: {report['input']['path']} ({report['input']['kind']})"]
    for f in report["findings"]:
        where = f" at {f['location']}" if f["location"] else ""
        evidence = ", ".join(f"{k}={v}" for k, v in f["evidence"].items())
        lines.append(f"{f['severity'].upper():7} {f['rule_id']}{where}: {f['message']}")
        lines.append(f"        evidence: {evidence}")
        if f["suggestion"]:
            lines.append(f"        suggestion: {f['suggestion']}")
    s = report["summary"]
    lines.append(f"{s['errors']} error(s), {s['warnings']} warning(s), {s['notes']} note(s)")
    return "\n".join(lines)


def rule_list(text):
    values = [part.strip().upper() for part in text.split(",") if part.strip()]
    unknown = [v for v in values if v not in RULES]
    if unknown:
        raise argparse.ArgumentTypeError("unknown rule ID: " + ", ".join(unknown))
    return values


def parser():
    p = argparse.ArgumentParser(
        prog="groovlint", description="Deterministic structural and signal checks for GrooveScripting files"
    )
    p.add_argument("input", help="project/preset JSON or WAV/FLAC file")
    p.add_argument("--version", action="version", version=__version__)
    diagnostics.add_arguments(p)
    p.add_argument("--audio", metavar="RENDERED_AUDIO", help="also inspect a rendered WAV/FLAC")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--fail-on", choices=["off", "note", "warning", "error"], default=None)
    p.add_argument("--only", action="append", type=rule_list, default=[], metavar="RULE_ID")
    p.add_argument("--ignore", action="append", type=rule_list, default=[], metavar="RULE_ID")
    p.add_argument("--thresholds", metavar="FILE", help="version 1 JSON threshold profile")
    p.add_argument("--strict", action="store_true", help="fail on warnings unless --fail-on is given")
    p.add_argument("--list-rules", action="store_true", help="print the rule catalog and exit")
    return p


def cli(argv=None):
    args = parser().parse_args(argv)
    try:
        logger, handler = diagnostics.start(args, "groovlint")
    except (ValueError, OSError) as error:
        print(f"groovlint: {error}", file=sys.stderr)
        return 2
    try:
        status = _run(args)
        logger.info("Completed groovlint status=%s", status)
        return status
    finally:
        diagnostics.close(logger, handler)


def _run(args):
    if args.list_rules:
        for rule_id, (severity, category, text) in RULES.items():
            print(f"{rule_id}  {severity:7} {category:7} {text}")
        return 0
    only = {r for group in args.only for r in group}
    ignore = {r for group in args.ignore for r in group}
    if only and ignore:
        print("groovlint: --only and --ignore cannot be combined", file=sys.stderr)
        return 2
    fail_on = args.fail_on or ("warning" if args.strict else "error")
    try:
        thresholds = load_thresholds(args.thresholds)
        report, input_error = analyze(args.input, args.audio, thresholds, only, ignore)
        output = (
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False)
            if args.format == "json"
            else text_report(report)
        )
        print(output)
    except KeyboardInterrupt:
        return 130
    except (LintInputError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"groovlint: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"groovlint: {error}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError, TypeError) as error:
        print(f"groovlint: analysis failed: {error}", file=sys.stderr)
        return 3
    if input_error:
        return 2
    if fail_on == "off":
        return 0
    floor = SEVERITIES.index(fail_on)
    return 1 if any(SEVERITIES.index(f["severity"]) >= floor for f in report["findings"]) else 0


def main():
    return cli()
