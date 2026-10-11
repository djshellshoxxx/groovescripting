"""groovmerge: semantic three-way merge of project files by musical dimension.

Instead of merging JSON text, each project is split into named dimensions (tempo, global settings,
each track's pattern, sound, mix, automation and every individual parameter, and the section
list). Each dimension is merged independently using base/ours/theirs rules, so a drum pattern
change on one branch and a bass filter change on another combine without a textual conflict.
"""

import argparse
import contextlib
import copy
import io
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


def _flatten(project):
    """Return ({dimension: value}, {dimension: track name}) for one project."""
    out = {
        "tempo": {k: project[k] for k in TEMPO if k in project},
        "global": {k: project[k] for k in GLOBAL if k in project},
        "sections": project.get("sections", MISSING),
    }
    owners = {}

    def put(key, value, track):
        if key in out:
            raise ValueError(f"track names produce an ambiguous merge dimension: {key}")
        out[key] = value
        owners[key] = track

    for track in project.get("tracks", []):
        name = track["name"]
        base = f"track:{name}"
        put(base, True, name)
        put(base + ".sound", {k: track[k] for k in SOUND if k in track}, name)
        put(base + ".pattern", track.get("pattern", MISSING), name)
        put(base + ".mix", {k: track[k] for k in MIX if k in track}, name)
        put(base + ".automation", track.get("automation", MISSING), name)
        for key, value in track.get("params", {}).items():
            put(f"{base}.params.{key}", value, name)
    return out, owners


def dimensions(project):
    """Flatten a project into {dimension: value} with MISSING for absent keys."""
    return _flatten(project)[0]


def _ancestors(name, owner):
    """Dimension names that a --take pattern may use to select NAME, outermost first.

    Track names may contain '.', so the track part is taken from the known owner rather than by
    splitting on the first '.'.
    """
    if owner is None:
        return [name]
    base = f"track:{owner}"
    if name == base:
        return [base]
    rest = name[len(base) + 1 :]
    head, _, _ = rest.partition(".")
    chain = [base, f"{base}.{head}"]
    if rest != head:
        chain.append(name)
    return chain


def _choice(name, takes, prefer, owner=None):
    ancestors = _ancestors(name, owner)
    best = None
    for pattern, side in takes:
        if pattern in ancestors:
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
    (b, bo), (o, oo), (t, to) = _flatten(base), _flatten(ours), _flatten(theirs)
    owners = {**bo, **oo, **to}
    by_track = {}
    for key, track in owners.items():
        by_track.setdefault(track, set()).add(key)
    merged, conflicts, decisions = {}, [], []

    def edited(flat, track):
        return any(flat.get(k, MISSING) != b.get(k, MISSING) for k in by_track[track])

    # A track deleted on one side and edited on the other is decided as a whole on track:NAME.
    whole = {}
    for track, keys in by_track.items():
        name = f"track:{track}"
        if b.get(name, MISSING) is MISSING:
            continue
        ov, tv = o.get(name, MISSING), t.get(name, MISSING)
        if (ov is MISSING and tv is not MISSING and edited(t, track)) or (
            tv is MISSING and ov is not MISSING and edited(o, track)
        ):
            whole[track] = keys

    for track, keys in sorted(whole.items()):
        name = f"track:{track}"
        side = _choice(name, takes, prefer, track)
        if side is None:
            conflicts.append(
                dict(
                    dimension=name,
                    base=_show(b.get(name, MISSING)),
                    ours=_show(o.get(name, MISSING)),
                    theirs=_show(t.get(name, MISSING)),
                    detail="track deleted on one side and edited on the other",
                )
            )
            continue
        source = o if side == "ours" else t
        for key in keys:
            merged[key] = source.get(key, MISSING)
        decisions.append(dict(dimension=name, source=f"{side} (resolved)"))

    handled = {key for keys in whole.values() for key in keys}
    for name in sorted((set(b) | set(o) | set(t)) - handled):
        bv, ov, tv = b.get(name, MISSING), o.get(name, MISSING), t.get(name, MISSING)
        if ov == tv:
            value, source = ov, "both"
        elif ov == bv:
            value, source = tv, "theirs"
        elif tv == bv:
            value, source = ov, "ours"
        else:
            side = _choice(name, takes, prefer, owners.get(name))
            if side is None:
                conflicts.append(dict(dimension=name, base=_show(bv), ours=_show(ov), theirs=_show(tv)))
                continue
            value, source = (ov if side == "ours" else tv), f"{side} (resolved)"
        merged[name] = value
        if source != "both":
            decisions.append(dict(dimension=name, source=source))
    decisions.sort(key=lambda d: d["dimension"])
    conflicts.sort(key=lambda c: c["dimension"])
    report = dict(tool="groovmerge", conflicts=conflicts, decisions=decisions)
    if conflicts:
        return None, report
    project = {"version": 1}
    for key, value in list(_mapping(merged.get("tempo")).items()) + list(_mapping(merged.get("global")).items()):
        project[key] = value
    order = [tr["name"] for tr in ours.get("tracks", [])]
    order += [tr["name"] for tr in theirs.get("tracks", []) if tr["name"] not in order]
    tracks = []
    for name in order:
        base_key = f"track:{name}"
        if merged.get(base_key, MISSING) is MISSING:
            continue
        track = {"name": name}
        track.update(_mapping(merged.get(base_key + ".sound")))
        if merged.get(base_key + ".pattern", MISSING) is not MISSING:
            track["pattern"] = merged[base_key + ".pattern"]
        prefix = base_key + ".params."
        params = {
            k[len(prefix) :]: v
            for k, v in merged.items()
            if owners.get(k) == name and k.startswith(prefix) and v is not MISSING
        }
        if params:
            track["params"] = dict(sorted(params.items()))
        track.update(_mapping(merged.get(base_key + ".mix")))
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


def _mapping(value):
    return value if isinstance(value, dict) else {}


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
    from .cli import early_logs

    argv = list(sys.argv[1:] if argv is None else argv)
    logger = handler = None
    try:
        try:
            logger, handler = early_logs(argv)
        except (ValueError, OSError) as error:
            print(f"groovmerge: {error}", file=sys.stderr)
            return 2
        logger.info("Starting groovmerge")
        args = _parse(parser(), argv, logger)
        status = _run(args)
        logger.info("Completed groovmerge status=%s", status)
        return status
    except KeyboardInterrupt:
        if logger:
            logger.warning("Interrupted groovmerge")
        return 130
    finally:
        if logger and handler:
            diagnostics.close(logger, handler)


def _parse(argument_parser, argv, logger):
    """parse_args, logging argparse errors before re-raising its SystemExit."""
    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            return argument_parser.parse_args(argv)
    except SystemExit as stop:
        if stop.code not in (0, None):
            logger.error("Invalid arguments: %s", captured.getvalue().strip())
        raise
    finally:
        sys.stderr.write(captured.getvalue())


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
            # The report goes to stderr so stdout carries only the merged project.
            for d in report["decisions"]:
                print(f"took {d['source']:<17} {d['dimension']}", file=sys.stderr)
            for c in report["conflicts"]:
                detail = c.get("detail") or f"ours={c['ours']!r} theirs={c['theirs']!r} base={c['base']!r}"
                print(f"CONFLICT {c['dimension']}: {detail}", file=sys.stderr)
            if project is not None and not args.output:
                print(json.dumps(project, indent=2))
            print(
                f"{len(report['decisions'])} merged change(s), {len(report['conflicts'])} conflict(s)"
                + (f"; wrote {args.output}" if project is not None and args.output else ""),
                file=sys.stderr,
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
