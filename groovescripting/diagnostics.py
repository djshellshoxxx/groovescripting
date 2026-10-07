"""Opt-in UTF-8 troubleshooting logging without contaminating stdout."""

import datetime
import json
import logging
import platform
import sys

from . import __version__


class Formatter(logging.Formatter):
    def __init__(self, json_format=False):
        super().__init__()
        self.json_format = json_format

    def format(self, record):
        stamp = datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat()
        item = {
            "timestamp": stamp,
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            item["exception"] = self.formatException(record.exc_info)
        if self.json_format:
            return json.dumps(item, ensure_ascii=False)
        result = f"{stamp} {record.levelname} {record.name}: {item['message']}"
        return result + ("\n" + item["exception"] if "exception" in item else "")


def configure(path=None, level="info", log_format="text"):
    logger = logging.getLogger("groovescripting")
    logger.propagate = False
    logger.setLevel(getattr(logging, level.upper()))
    handler = logging.FileHandler(path, encoding="utf-8") if path else logging.NullHandler()
    handler.setFormatter(Formatter(log_format == "json"))
    logger.addHandler(handler)
    logger.debug("version=%s Python=%s platform=%s", __version__, sys.version.split()[0], platform.platform())
    return logger, handler


def close(logger, handler):
    logger.removeHandler(handler)
    handler.close()


def add_arguments(parser):
    """Shared opt-in logging flags for every tool."""
    parser.add_argument("--log-file", metavar="PATH", help="append troubleshooting logs to a UTF-8 file")
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error"], default="info")
    parser.add_argument("--log-format", choices=["text", "json"], default="text")


def start(args, tool):
    """Validate logging flags and open the logger; callers must close() the handler."""
    if not args.log_file and (args.log_level != "info" or args.log_format != "text"):
        raise ValueError("--log-level and --log-format require --log-file")
    logger, handler = configure(args.log_file, args.log_level, args.log_format)
    logger.info("Starting %s", tool)
    return logger, handler
