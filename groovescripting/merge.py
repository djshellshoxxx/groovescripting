"""groovmerge: semantic three-way merge of project files by musical dimension.

Instead of merging JSON text, each project is split into named dimensions (tempo, global settings,
each track's pattern, sound, mix, automation and every individual parameter, and the section
list). Each dimension is merged independently using base/ours/theirs rules, so a drum pattern
change on one branch and a bass filter change on another combine without a textual conflict.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

from . import __version__, diagnostics
from .projects import save, validate

TEMPO = ("bpm", "beats", "subdivision", "swing")
GLOBAL = ("bars", "sample_rate", "channels", "seed", "humanize", "velocity_humanize")
MIX = ("gain", "pan", "mute", "solo", "offset", "trim")
SOUND = ("instrument", "preset")
MISSING = object()


def dimensions(project):
    """Flatten a project into {dimension: value} with MISSING for absent keys."""
    out = {
        "tempo": {k: project[k] for k in TEMPO if k in project},
        "global": {k: project[k] for k in GLOBAL if k in project},
        "sections": project.get("sections", MISSING),
    }
    for track in project.get("tracks", []):
        base = f"track:{track['name']}"
        out[base] = True
        out[base + ".sound"] = {k: track[k] for k in SOUND if k in track}
        out[base + ".pattern"] = track.get("pattern", MISSING)
        out[base + ".mix"] = {k: track[k] for k in MIX if k in track}
        out[base + ".automation"] = track.get("automation", MISSING)
        for key, value in track.get("params", {}).items():
            out[f"{base}.params.{key}"] = value
    return out


def _choice(name, takes, prefer):
    best = None
    for pattern, side in takes:
        if name == pattern or name.startswith(pattern + "."):
            if best is None or len(pattern) > len(best[0]):
                best = (pattern, side)
    return best[1] if best else prefer


def merge(base, ours, theirs, takes=(), prefer=None):
    """Return (project or None, report). Unresolved conflicts leave the project as None."""
    for label, project in (("base", base), ("ours", ours), ("theirs", theirs)):
        try:
            validate(copy.deepcopy(project))
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from error
    b, o, t = dimensions(base), dimensions(ours), dimensions(theirs)
    merged, conflicts, decisions = {}, [], []

    def edited(flat, track):
        prefix = track + "."
        keys = {k for k in set(flat) | set(b) if k.startswith(prefix)}
        return any(flat.get(k, MISSING) != b.get(k, MISSING) for k in keys)

    for name in sorted(set(b) | set(o) | set(t)):
        bv, ov, tv = b.get(name, MISSING), o.get(name, MISSING), t.get(name, MISSING)
        presence = name.startswith("track:") and "." not in name
        deleted_vs_edited = (
            presence
            and bv is not MISSING
            and (
                (ov is MISSING and tv is not MISSING and edited(t, name))
                or (tv is MISSING and ov is not MISSING and edited(o, name))
            )
        )
        if ov == tv and not deleted_vs_edited:
            value, source = ov, "both"
        elif ov == bv and not deleted_vs_edited:
            value, source = tv, "theirs"
        elif tv == bv and not deleted_vs_edited:
            value, source = ov, "ours"
        else:
            side = _choice(name, takes, prefer)
            if side is None:
                conflict = dict(dimension=name, base=_show(bv), ours=_show(ov), theirs=_show(tv))
                if deleted_vs_edited:
                    conflict["detail"] = "track deleted on one side and edited on the other"
                conflicts.append(conflict)
                continue
            value, source = (ov if side == "ours" else tv), f"{side} (resolved)"
        merged[name] = value
        if source != "both":
            decisions.append(dict(dimension=name, source=source))
    report = dict(tool="groovmerge", conflicts=conflicts, decisions=decisions)
    if conflicts:
        return None, report
    project = {"version": 1}
    for key, value in list(merged.get("tempo", {}).items()) + list(merged.get("global", {}).items()):
        project[key] = value
    order = [tr["name"] for tr in ours.get("tracks", [])]
    order += [tr["name"] for tr in theirs.get("tracks", []) if tr["name"] not in order]
    tracks = []
    for name in order:
        base_key = f"track:{name}"
        if merged.get(base_key, MISSING) is MISSING:
            continue
        track = {"name": name}
        track.update(merged.get(base_key + ".sound", {}))
        if merged.get(base_key + ".pattern", MISSING) is not MISSING:
            track["pattern"] = merged[base_key + ".pattern"]
        prefix = base_key + ".params."
        params = {k[len(prefix) :]: v for k, v in merged.items() if k.startswith(prefix) and v is not MISSING}
        if params:
            track["params"] = dict(sorted(params.items()))
        track.update(merged.get(base_key + ".mix", {}))
        if merged.get(base_key + ".automation", MISSING) is not MISSING:
            track["automation"] = merged[base_key + ".automation"]
        tracks.append(track)
    project["tracks"] = tracks
    if merged.get("sections", MISSING) is not MISSING:
        project["sections"] = merged["sections"]
    try:
        validate(copy.deepcopy(project))
    except ValueError as error:
        report["conflicts"].append(dict(dimension="project", detail=f"merged result is invalid: {error}"))
        return None, report
    return project, report


def _show(value):
    return "absent" if value is MISSING else value


def take_type(text):
    dimension, _, side = text.rpartition("=")
    if not dimension or side not in ("ours", "theirs"):
        raise argparse.ArgumentTypeError(
            "use DIMENSION=ours or DIMENSION=theirs, e.g. track:Bass.pattern=theirs"
        )
    return (dimension, side)


def parser():
    p = argparse.ArgumentParser(
        prog="groovmerge", description="Semantic three-way merge of GrooveScripting projects"
    )
    p.add_argument("base", help="common ancestor project")
    p.add_argument("ours", help="our project version")
    p.add_argument("theirs", help="their project version")
    p.add_argument("--version", action="version", version=__version__)
    diagnostics.add_arguments(p)
    p.add_argument("--output", "-o", help="merged project path (omit for --dry-run style report)")
    p.add_argument("--take", action="append", type=take_type, default=[], metavar="DIMENSION=SIDE")
    p.add_argument(
        "--prefer", choices=["ours", "theirs"], help="resolve every remaining conflict to one side"
    )
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    return p


def cli(argv=None):
    args = parser().parse_args(argv)
    try:
        logger, handler = diagnostics.start(args, "groovmerge")
    except (ValueError, OSError) as error:
        print(f"groovmerge: {error}", file=sys.stderr)
        return 2
    try:
        status = _run(args)
        logger.info("Completed groovmerge status=%s", status)
        return status
    finally:
        diagnostics.close(logger, handler)


def _run(args):
    try:
        loaded = [
            json.loads(Path(path).read_text(encoding="utf-8")) for path in (args.base, args.ours, args.theirs)
        ]
        project, report = merge(*loaded, takes=args.take, prefer=args.prefer)
        if project is not None and args.output:
            save(args.output, project, overwrite=args.overwrite)
            report["output"] = Path(args.output).as_posix()
        if args.format == "json":
            print(json.dumps(dict(report, merged=project), indent=2, sort_keys=True, default=str))
        else:
            for d in report["decisions"]:
                print(f"took {d['source']:<17} {d['dimension']}")
            for c in report["conflicts"]:
                detail = c.get("detail") or f"ours={c['ours']!r} theirs={c['theirs']!r} base={c['base']!r}"
                print(f"CONFLICT {c['dimension']}: {detail}")
            if project is not None and not args.output:
                print(json.dumps(project, indent=2))
            print(
                f"{len(report['decisions'])} merged change(s), {len(report['conflicts'])} conflict(s)"
                + (f"; wrote {args.output}" if project is not None and args.output else "")
            )
        return 1 if report["conflicts"] else 0
    except KeyboardInterrupt:
        return 130
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, FileExistsError) as error:
        print(f"groovmerge: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"groovmerge: {error}", file=sys.stderr)
        return 1


def main():
    return cli()
