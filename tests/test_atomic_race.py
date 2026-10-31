"""No-overwrite publication must preserve files created concurrently."""

import errno
import os
from pathlib import Path

import pytest

from groovescripting import atomic, trace


def publish(destination, kind, overwrite=False):
    if kind == "trace":
        return trace.write_jsonl(destination, {"kind": "header"}, [], overwrite=overwrite)
    return atomic.write_atomic(destination, lambda path: path.write_bytes(b"NEW"), overwrite=overwrite)


@pytest.mark.parametrize("kind", ["atomic", "trace"])
def test_concurrent_destination_is_preserved(tmp_path, monkeypatch, kind):
    destination = tmp_path / "output"
    original_link = os.link
    original_replace = os.replace

    def race_link(source, target, *args, **kwargs):
        Path(target).write_bytes(b"CONCURRENT")
        return original_link(source, target, *args, **kwargs)

    def race_replace(source, target, *args, **kwargs):
        Path(target).write_bytes(b"CONCURRENT")
        return original_replace(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "link", race_link)
    monkeypatch.setattr(os, "replace", race_replace)
    with pytest.raises(FileExistsError):
        publish(destination, kind)
    assert destination.read_bytes() == b"CONCURRENT"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("kind", ["atomic", "trace"])
def test_broken_symlink_destination_is_preserved(tmp_path, kind):
    destination = tmp_path / "output"
    try:
        destination.symlink_to("missing-target")
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    with pytest.raises(FileExistsError):
        publish(destination, kind)
    assert destination.is_symlink()
    assert os.readlink(destination) == "missing-target"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("kind", ["atomic", "trace"])
def test_overwrite_replaces_existing_destination(tmp_path, kind):
    destination = tmp_path / "output"
    destination.write_bytes(b"OLD")
    assert publish(destination, kind, overwrite=True) == destination
    assert destination.read_bytes() != b"OLD"
    assert list(tmp_path.iterdir()) == [destination]


def test_link_failure_has_no_unsafe_fallback(tmp_path, monkeypatch):
    destination = tmp_path / "output"

    def unsupported(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, "hard links unsupported")

    monkeypatch.setattr(os, "link", unsupported)
    with pytest.raises(OSError, match="hard links unsupported"):
        publish(destination, "atomic")
    assert not list(tmp_path.iterdir())
