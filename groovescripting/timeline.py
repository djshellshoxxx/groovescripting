"""groovtime: deterministic inspection, rendering and event diffs of prior composition states.

History comes from Git: every committed revision of a project file is a composition state. Each
state is identified by its revision and its run fingerprint, and is traced or rendered with exactly
the engine path used for the current file. Nothing in the repository or working tree is modified.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__, diagnostics, trace
from .projects import validate

WORKTREE = "WORKTREE"
COMPARED = ("notes", "velocity", "accepted", "duration", "probability", "bar", "beat")


def _git(directory, *args):
    if shutil.which("git") is None:
        raise RuntimeError("git is required for groovtime")
    result = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def state(path, revision=WORKTREE):
    """Return the project dictionary for a revision of a file (WORKTREE = current file)."""
    path = Path(path)
    if revision == WORKTREE:
        return validate(json.loads(path.read_text(encoding="utf-8")))
    if revision.startswith("-"):
        raise ValueError("revision must not start with '-'")
    text = _git(path.parent, "show", f"{revision}:./{path.name}")
    return validate(json.loads(text))


def history(path, limit=50):
    path = Path(path)
    raw = _git(path.parent, "log", f"-n{int(limit)}", "--format=%H%x09%cI%x09%s", "--", path.name)
    entries = []
    for line in raw.splitlines():
        commit, date, subject = line.split("\t", 2)
        entry = dict(revision=commit[:12], date=date, subject=subject)
        try:
            project = state(path, commit)
            entry.update(valid=True, run_fingerprint=trace.fingerprint(project))
        except (ValueError, json.JSONDecodeError) as error:
            entry.update(valid=False, error=str(error).splitlines()[0])
        entries.append(entry)
    return entries


def diff(old_project, new_project, seed=None):
    _, before = trace.collect(old_project, seed=seed)
    _, after = trace.collect(new_project, seed=seed)
    old = {r["event_id"]: r for r in before}
    new = {r["event_id"]: r for r in after}
    added = [new[k] for k in new if k not in old]
    removed = [old[k] for k in old if k not in new]
    changed = []
    for key in old.keys() & new.keys():
        fields = {
            f: dict(before=old[key][f], after=new[key][f]) for f in COMPARED if old[key][f] != new[key][f]
        }
        if old[key]["timing"]["frame"] != new[key]["timing"]["frame"]:
            fields["frame"] = dict(before=old[key]["timing"]["frame"], after=new[key]["timing"]["frame"])
        if fields:
            changed.append(dict(event_id=key, track=new[key]["track"], bar=new[key]["bar"], fields=fields))

    def brief(r):
        return dict(
            event_id=r["event_id"],
            track=r["track"],
            voice=r["voice"],
            bar=r["bar"],
            beat=r["beat"],
            notes=r["notes"],
            accepted=r["accepted"],
        )

    order = lambda r: (r["bar"], r["beat"] if "beat" in r else 0, r["track"], r["event_id"])  # noqa: E731
    return dict(
        added=sorted(map(brief, added), key=order),
        removed=sorted(map(brief, removed), key=order),
        changed=sorted(changed, key=lambda r: (r["bar"], r["track"], r["event_id"])),
    )


def parser():
    p = argparse.ArgumentParser(
        prog="groovtime", description="Inspect, render and diff prior committed states of a project"
    )
    p.add_argument("--version", action="version", version=__version__)
    diagnostics.add_arguments(p)
    sub = p.add_subparsers(dest="action", required=True)
    log = sub.add_parser("log", help="list committed states with run fingerprints")
    log.add_argument("project")
    log.add_argument("--limit", type=int, default=50)
    log.add_argument("--format", choices=["text", "json"], default="text")
    show = sub.add_parser("show", help="print a prior project state as JSON")
    show.add_argument("project")
    show.add_argument("--at", default=WORKTREE, help="Git revision or WORKTREE")
    render = sub.add_parser("render", help="render a prior state with groovseq")
    render.add_argument("project")
    render.add_argument("--at", default=WORKTREE, help="Git revision or WORKTREE")
    render.add_argument("--output", "-o", required=True)
    render.add_argument("--overwrite", action="store_true")
    render.add_argument("--seed", type=int)
    compare = sub.add_parser("diff", help="event-level diff between two states")
    compare.add_argument("project")
    compare.add_argument("--from", dest="old", default="HEAD", help="Git revision or WORKTREE")
    compare.add_argument("--to", dest="new", default=WORKTREE, help="Git revision or WORKTREE")
    compare.add_argument("--seed", type=int)
    compare.add_argument("--format", choices=["text", "json"], default="text")
    return p


def cli(argv=None):
    args = parser().parse_args(argv)
    try:
        logger, handler = diagnostics.start(args, "groovtime")
    except (ValueError, OSError) as error:
        print(f"groovtime: {error}", file=sys.stderr)
        return 2
    try:
        status = _run(args)
        logger.info("Completed groovtime status=%s", status)
        return status
    finally:
        diagnostics.close(logger, handler)


def _run(args):
    try:
        if getattr(args, "seed", None) is not None and args.seed < 0:
            raise ValueError("--seed must be nonnegative")
        if args.action == "log":
            if args.limit < 1:
                raise ValueError("--limit must be positive")
            entries = history(args.project, args.limit)
            if args.format == "json":
                print(json.dumps(entries, indent=2, sort_keys=True))
            else:
                for e in entries:
                    status = e["run_fingerprint"] if e["valid"] else "invalid: " + e["error"]
                    print(f"{e['revision']}  {e['date']}  {status}  {e['subject']}")
        elif args.action == "show":
            print(json.dumps(state(args.project, args.at), indent=2))
        elif args.action == "render":
            from .cli import run

            project = state(args.project, args.at)
            if args.seed is not None:
                project["seed"] = args.seed
            handle, temporary = tempfile.mkstemp(suffix=".json", prefix="groovtime-")
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as out:
                    json.dump(project, out)
                extra = ["--overwrite"] if args.overwrite else []
                return run("groovseq", [temporary, "--output", args.output, *extra])
            finally:
                Path(temporary).unlink(missing_ok=True)
        else:
            result = diff(state(args.project, args.old), state(args.project, args.new), args.seed)
            if args.format == "json":
                print(json.dumps(result, indent=2, sort_keys=True))
            else:
                for r in result["added"]:
                    print(
                        f"+ {r['event_id']} {r['track']}/{r['voice']} bar {r['bar']} beat {r['beat']:g} {r['notes']}"
                    )
                for r in result["removed"]:
                    print(
                        f"- {r['event_id']} {r['track']}/{r['voice']} bar {r['bar']} beat {r['beat']:g} {r['notes']}"
                    )
                for r in result["changed"]:
                    changes = ", ".join(f"{k} {v['before']}->{v['after']}" for k, v in r["fields"].items())
                    print(f"~ {r['event_id']} {r['track']} bar {r['bar']}: {changes}")
                print(
                    f"{len(result['added'])} added, {len(result['removed'])} removed, {len(result['changed'])} changed"
                )
        return 0
    except KeyboardInterrupt:
        return 130
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"groovtime: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as error:
        print(f"groovtime: {error}", file=sys.stderr)
        return 1


def main():
    return cli()
