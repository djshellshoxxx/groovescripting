"""groovtest: reusable musical assertions evaluated over a project's deterministic event trace."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, diagnostics, trace
from .expr import ExpressionError, compile_expression
from .projects import load, validate

SCHEMA_VERSION = 1
COUNT_KEYS = {"min", "max", "eq"}
TEST_KEYS = {"name", "where", "count", "all", "none", "fingerprint", "seed"}


def _count_spec(value, name):
    if not isinstance(value, dict) or not value or set(value) - COUNT_KEYS:
        raise ValueError(f"test {name!r}: count requires min, max and/or eq")
    for key, number in value.items():
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError(f"test {name!r}: count.{key} must be a nonnegative integer")
    return value


def load_suite(path):
    path = Path(path)
    suite = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(suite, dict) or suite.get("version") != 1:
        raise ValueError("test suite requires version 1")
    unknown = set(suite) - {"version", "project", "seed", "tests"}
    if unknown:
        raise ValueError("unknown suite keys: " + ", ".join(sorted(unknown)))
    if not isinstance(suite.get("project"), str):
        raise ValueError("suite project must be a path relative to the suite file")
    tests = suite.get("tests")
    if not isinstance(tests, list) or not tests:
        raise ValueError("suite requires a nonempty tests list")
    names = set()
    compiled = []
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("each test must be an object")
        name = test.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("test names must be unique nonempty strings")
        names.add(name)
        unknown = set(test) - TEST_KEYS
        if unknown:
            raise ValueError(f"test {name!r}: unknown keys " + ", ".join(sorted(unknown)))
        checks = [k for k in ("count", "all", "none", "fingerprint") if k in test]
        if len(checks) != 1:
            raise ValueError(f"test {name!r}: use exactly one of count, all, none or fingerprint")
        item = dict(name=name, kind=checks[0], spec=test[checks[0]])
        try:
            item["where"] = compile_expression(test["where"]) if "where" in test else (lambda r: True)
            if item["kind"] in ("all", "none"):
                item["check"] = compile_expression(test[item["kind"]])
        except ExpressionError as error:
            raise ValueError(f"test {name!r}: {error}") from error
        if item["kind"] == "count":
            _count_spec(item["spec"], name)
        if item["kind"] == "fingerprint" and not isinstance(item["spec"], str):
            raise ValueError(f"test {name!r}: fingerprint must be a string")
        item["source"] = test
        compiled.append(item)
    project_path = (path.parent / suite["project"]).resolve()
    return dict(suite=suite, tests=compiled, project_path=project_path)


def evaluate(loaded, project=None, seed=None):
    project = validate(project) if project is not None else load(loaded["project_path"])
    seed = seed if seed is not None else loaded["suite"].get("seed")
    header, records = trace.collect(project, seed=seed)
    results = []
    for test in loaded["tests"]:
        matched = [r for r in records if test["where"](r)]
        outcome = dict(name=test["name"], kind=test["kind"], matched=len(matched))
        if test["kind"] == "count":
            spec = test["spec"]
            passed = (
                ("min" not in spec or len(matched) >= spec["min"])
                and ("max" not in spec or len(matched) <= spec["max"])
                and ("eq" not in spec or len(matched) == spec["eq"])
            )
            outcome.update(expected=spec, observed=len(matched))
        elif test["kind"] == "fingerprint":
            passed = header["run_fingerprint"] == test["spec"]
            outcome.update(expected=test["spec"], observed=header["run_fingerprint"])
        else:
            hits = [r for r in matched if test["check"](r)]
            offenders = [r for r in matched if r not in hits] if test["kind"] == "all" else hits
            passed = not offenders
            outcome.update(
                expected=test["source"][test["kind"]],
                failing_events=[
                    dict(event_id=r["event_id"], track=r["track"], bar=r["bar"], beat=r["beat"])
                    for r in offenders[:20]
                ],
                failing_count=len(offenders),
            )
        outcome["passed"] = passed
        results.append(outcome)
    return dict(
        schema_version=SCHEMA_VERSION,
        tool="groovtest",
        run_fingerprint=header["run_fingerprint"],
        events=len(records),
        passed=sum(r["passed"] for r in results),
        failed=sum(not r["passed"] for r in results),
        results=results,
    )


def text_report(report, suite_path):
    lines = [f"groovtest: {suite_path} ({report['events']} events, fingerprint {report['run_fingerprint']})"]
    for r in report["results"]:
        detail = ""
        if r["kind"] in ("count", "fingerprint"):
            detail = f" expected {r['expected']} observed {r['observed']}"
        elif not r["passed"]:
            first = r["failing_events"][0]
            detail = (
                f" {r['failing_count']} event(s) violate {r['kind']} {r['expected']!r};"
                f" first {first['event_id']} {first['track']} bar {first['bar']} beat {first['beat']:g}"
            )
        lines.append(f"{'PASS' if r['passed'] else 'FAIL'}  {r['name']}{detail if not r['passed'] else ''}")
    lines.append(f"{report['passed']} passed, {report['failed']} failed")
    return "\n".join(lines)


def parser():
    p = argparse.ArgumentParser(
        prog="groovtest", description="Musical assertions over deterministic event traces"
    )
    p.add_argument("suites", nargs="+", help="version 1 JSON test suite files")
    p.add_argument("--version", action="version", version=__version__)
    diagnostics.add_arguments(p)
    p.add_argument("--seed", type=int, help="override every suite's seed")
    p.add_argument("--format", choices=["text", "json"], default="text")
    return p


def cli(argv=None):
    args = parser().parse_args(argv)
    try:
        logger, handler = diagnostics.start(args, "groovtest")
    except (ValueError, OSError) as error:
        print(f"groovtest: {error}", file=sys.stderr)
        return 2
    try:
        status = _run(args)
        logger.info("Completed groovtest status=%s", status)
        return status
    finally:
        diagnostics.close(logger, handler)


def _run(args):
    if args.seed is not None and args.seed < 0:
        print("groovtest: --seed must be nonnegative", file=sys.stderr)
        return 2
    reports = []
    try:
        for path in args.suites:
            loaded = load_suite(path)
            report = evaluate(loaded, seed=args.seed)
            report["suite"] = Path(path).as_posix()
            reports.append(report)
    except KeyboardInterrupt:
        return 130
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError) as error:
        print(f"groovtest: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(reports if len(reports) > 1 else reports[0], sort_keys=True, indent=2))
    else:
        print("\n".join(text_report(r, r["suite"]) for r in reports))
    return 1 if any(r["failed"] for r in reports) else 0


def main():
    return cli()
