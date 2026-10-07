"""groovdebug: read-only deterministic debugger over a project's traced event schedule."""

import argparse
import json
import sys

from . import __version__, diagnostics, trace
from .expr import ExpressionError, compile_expression
from .projects import load

HELP = """Commands:
  continue | c        continue to the next breakpoint or the end
  step | s            advance to the next event
  bar [N]             summarize the current or requested bar
  events [A[-B]]      list events in the current bar or bars A..B
  inspect EVENT_ID    show one event with its recorded inputs and decisions
  why EVENT_ID        explain captured decisions and list unavailable causes
  seed                show the root and derived per-track/per-section seeds
  fingerprint         show the run fingerprint
  help                show this help
  quit | q            exit without modifications"""


def positive(text):
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if value < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def seed_type(text):
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from error
    if value < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return value


def breakpoint_type(text):
    bar, _, beat = text.partition(":")
    try:
        bar_value = int(bar)
        beat_value = float(beat) if beat else None
    except ValueError as error:
        raise argparse.ArgumentTypeError("use BAR or BAR:BEAT, for example 17 or 17:3") from error
    if bar_value < 1 or (beat_value is not None and not 1 <= beat_value < 1000):
        raise argparse.ArgumentTypeError("bar must be >=1 and beat >=1")
    return (bar_value, beat_value)


def parser():
    p = argparse.ArgumentParser(
        prog="groovdebug", description="Deterministic, read-only debugger for GrooveScripting projects"
    )
    p.add_argument("project", help="version 1 JSON arrangement")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--seed", type=seed_type, help="override the project seed")
    p.add_argument(
        "--break", dest="breaks", action="append", type=breakpoint_type, default=[], metavar="BAR[:BEAT]"
    )
    p.add_argument("--track", dest="tracks", action="append", default=[], help="break on events of a track")
    p.add_argument("--event", dest="events", action="append", default=[], help="break on an event ID")
    p.add_argument(
        "--where", dest="where", action="append", default=[], help="break on a predicate expression"
    )
    p.add_argument("--commands", metavar="FILE", help="run debugger commands from a file (one per line)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--trace-out", metavar="PATH", help="write the full JSON Lines trace")
    p.add_argument("--overwrite", action="store_true", help="allow replacing --trace-out")
    p.add_argument("--max-events", type=positive, default=trace.DEFAULT_MAX_EVENTS)
    diagnostics.add_arguments(p)
    return p


def build_breakpoints(args):
    checks = []
    for bar, beat in args.breaks:
        label = f"bar {bar}" + (f":{beat:g}" if beat is not None else "")
        checks.append(
            (
                label,
                lambda r, bar=bar, beat=beat: (
                    r["bar"] == bar and (beat is None or beat <= r["beat"] < beat + 1)
                ),
            )
        )
    for name in args.tracks:
        checks.append((f"track {name}", lambda r, name=name: r["track"] == name))
    for event_id in args.events:
        checks.append((f"event {event_id}", lambda r, event_id=event_id: r["event_id"] == event_id))
    for text in args.where:
        checks.append((f"where {text}", compile_expression(text)))
    return checks


def stop_reason(record, checks):
    return next((label for label, check in checks if check(record)), None)


def row(record):
    frame = record["timing"]["frame"]
    notes = "+".join(f"{n:g}" for n in record["notes"]) or "-"
    state = (
        "yes"
        if record["accepted"]
        else "no:"
        + next((d["kind"] for d in record["decisions"] if d.get("result") in ("fail", "dropped")), "dropped")
    )
    return (
        f"{record['event_id']}  bar {record['bar']:>3} beat {record['beat']:<7.4g} "
        f"frame {'-' if frame is None else frame:>9}  {record['track']}/{record['voice']:<10} "
        f"notes {notes:<9} vel {record['velocity']:.3f} accepted {state}"
    )


def explain(record, header):
    lines = [f"Event {record['event_id']} ({record['track']}/{record['voice']})"]
    source = record["source"]
    lines.append(
        f"  source {source['pointer']} section {source['section']!r} repeat {source['repetition'] + 1}"
        f" origin {source['origin']}"
        + ("" if source["source_index"] is None else f" expanded index {source['source_index']}")
    )
    for decision in record["decisions"]:
        kind = decision["kind"]
        if kind == "probability":
            lines.append(
                f"  probability roll {decision['roll']:.6f} vs threshold {decision['threshold']:g}: "
                + decision["result"]
            )
        elif kind == "velocity_humanize":
            lines.append(f"  velocity humanized {decision['before']:.4f} -> {decision['after']:.4f}")
        elif kind == "variation_shift":
            lines.append(f"  variation moved the event by {decision['beats']:+.6f} beats")
        elif kind == "variation_insert":
            lines.append("  inserted by the variation engine (ghost note or fill); no source token")
        elif kind == "swing":
            lines.append(f"  swing delayed the event by {decision['beats']:g} beats")
        elif kind == "humanize":
            lines.append(f"  timing humanize shifted the event by {decision['frames']} frames")
        elif kind == "note_resolution":
            lines.append(
                f"  notes {decision['requested']} resolved to {decision['resolved']} (scale/arpeggio)"
            )
        elif kind == "voice_limit":
            lines.append(f"  voice limit truncated the note at frame {decision['truncated_at_frame']}")
        elif kind == "window":
            lines.append("  dropped: the resolved start falls outside the section render window")
    lines.append("  not captured by this engine: " + ", ".join(header["unavailable"]))
    return "\n".join(lines)


class Session:
    def __init__(self, header, records, checks, fmt, out):
        self.header, self.records, self.checks, self.fmt, self.out = header, records, checks, fmt, out
        self.cursor = -1
        self.by_id = {r["event_id"]: r for r in records}

    def emit(self, text, data):
        if self.fmt == "json":
            self.out.write(json.dumps(data, sort_keys=True) + "\n")
        else:
            self.out.write(text + "\n")

    def current_bar(self):
        return self.records[self.cursor]["bar"] if 0 <= self.cursor < len(self.records) else 1

    def show_stop(self, reason):
        if self.cursor >= len(self.records):
            self.emit("End of schedule.", dict(command="stop", status="end"))
            return
        record = self.records[self.cursor]
        self.emit(
            f"Stopped ({reason}) at bar {record['bar']} beat {record['beat']:g}\n  " + row(record),
            dict(command="stop", reason=reason, record=record),
        )

    def run(self, line):
        parts = line.strip().split()
        if not parts or parts[0].startswith("#"):
            return True
        command, rest = parts[0].lower(), parts[1:]
        if command in ("quit", "q"):
            self.emit("Bye.", dict(command="quit"))
            return False
        if command in ("continue", "c"):
            self.cursor += 1
            while self.cursor < len(self.records):
                reason = stop_reason(self.records[self.cursor], self.checks) if self.checks else None
                if reason:
                    self.show_stop(reason)
                    return True
                self.cursor += 1
            self.show_stop("end")
        elif command in ("step", "s"):
            self.cursor = min(self.cursor + 1, len(self.records))
            self.show_stop("step")
        elif command == "bar":
            bar = int(rest[0]) if rest else self.current_bar()
            items = [r for r in self.records if r["bar"] == bar]
            tracks = sorted({r["track"] for r in items})
            accepted = sum(r["accepted"] for r in items)
            self.emit(
                f"Bar {bar}: {len(items)} events, {accepted} accepted, tracks {', '.join(tracks) or '-'}",
                dict(command="bar", bar=bar, events=len(items), accepted=accepted, tracks=tracks),
            )
        elif command == "events":
            if rest:
                low, _, high = rest[0].partition("-")
                low, high = int(low), int(high or low)
            else:
                low = high = self.current_bar()
            items = [r for r in self.records if low <= r["bar"] <= high]
            self.emit("\n".join(map(row, items)) or "No events.", dict(command="events", records=items))
        elif command in ("inspect", "why"):
            if not rest or rest[0] not in self.by_id:
                raise ValueError(f"unknown event ID {rest[0] if rest else ''!r}")
            record = self.by_id[rest[0]]
            if command == "inspect":
                self.emit(
                    json.dumps(record, indent=2, sort_keys=True), dict(command="inspect", record=record)
                )
            else:
                self.emit(
                    explain(record, self.header),
                    dict(command="why", record=record, unavailable=self.header["unavailable"]),
                )
        elif command == "seed":
            seeds = self.header["derived_seeds"]
            text = f"Root seed {self.header['seed']}\n" + "\n".join(
                f"  section {s['section_index'] + 1} repeat {s['repetition'] + 1} {s['track']}: {s['seed']}"
                for s in seeds
            )
            self.emit(text, dict(command="seed", seed=self.header["seed"], derived=seeds))
        elif command == "fingerprint":
            self.emit(
                self.header["run_fingerprint"],
                dict(command="fingerprint", value=self.header["run_fingerprint"]),
            )
        elif command == "help":
            self.emit(HELP, dict(command="help", text=HELP))
        else:
            raise ValueError(f"unknown command {command!r}; type help")
        return True


def cli(argv=None, stdin=None, stdout=None):
    args = parser().parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    logger = handler = None
    try:
        if not args.log_file and (args.log_level != "info" or args.log_format != "text"):
            raise ValueError("--log-level and --log-format require --log-file")
        logger, handler = diagnostics.configure(args.log_file, args.log_level, args.log_format)
        checks = build_breakpoints(args)
        interactive = args.commands is None and args.format == "text"
        if interactive and not stdin.isatty():
            raise ValueError("non-interactive use requires --commands FILE or --format json")
        commands = None
        if args.commands:
            with open(args.commands, encoding="utf-8") as handle:
                commands = handle.read().splitlines()
        project = load(args.project)
        header, records = trace.collect(project, seed=args.seed, max_events=args.max_events)
        logger.info("groovdebug traced %d events fingerprint=%s", len(records), header["run_fingerprint"])
        if args.trace_out:
            trace.write_jsonl(args.trace_out, header, records, overwrite=args.overwrite)
        if commands is None and args.format == "json":
            stops = [
                dict(index=i, event_id=r["event_id"], reason=reason)
                for i, r in enumerate(records)
                if checks and (reason := stop_reason(r, checks))
            ]
            envelope = dict(
                schema_version=trace.TRACE_SCHEMA_VERSION,
                tool="groovdebug",
                status="completed",
                run_fingerprint=header["run_fingerprint"],
                header=header,
                breakpoints=[label for label, _ in checks],
                stops=stops,
                records=[records[s["index"]] for s in stops] if checks else records,
            )
            stdout.write(json.dumps(envelope, sort_keys=True) + "\n")
            return 0
        session = Session(header, records, checks, args.format, stdout)
        if args.format == "text":
            stdout.write(
                f"groovdebug {__version__}: {len(records)} events, fingerprint {header['run_fingerprint']}, "
                f"{len(checks)} breakpoint(s). Type help.\n"
            )
        if commands is not None:
            for line in commands:
                if not session.run(line):
                    break
            return 0
        while True:
            stdout.write("(groovdebug) ")
            stdout.flush()
            line = stdin.readline()
            if not line:
                return 0
            try:
                if not session.run(line):
                    return 0
            except ValueError as error:
                stdout.write(f"error: {error}\n")
    except KeyboardInterrupt:
        return 130
    except (ValueError, ExpressionError, TypeError, KeyError, json.JSONDecodeError, FileExistsError) as error:
        if logger:
            logger.exception("Invalid input: %s", error)
        print(f"groovdebug: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as error:
        if logger:
            logger.exception("Operation failed: %s", error)
        print(f"groovdebug: {error}", file=sys.stderr)
        return 1
    finally:
        if logger and handler:
            diagnostics.close(logger, handler)


def main():
    return cli()
