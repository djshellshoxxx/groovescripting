"""Atomic output replacement shared by project and MIDI exporters.

Writer receives a temporary path in the destination directory. On failure the temporary
file is removed and any existing destination remains unchanged. Writers must close the
output before return, as required for Windows replacement.
"""

import os
import tempfile
from pathlib import Path


def write_atomic(destination, writer, *, overwrite=False):
    """Write a temporary file, then atomically publish it at destination.

    On any failure leave the previous destination unchanged and clean up temporary files.
    Exclusive publication requires hard-link support on the destination filesystem;
    unsupported filesystems fail safely rather than risking an existing output.
    """
    destination = Path(destination)
    if os.path.lexists(destination) and not overwrite:
        raise FileExistsError(str(destination))
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary)
    try:
        writer(temporary)
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
