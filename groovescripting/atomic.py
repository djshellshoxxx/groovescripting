"""Atomic output replacement shared by project and MIDI exporters.

Writer receives a temporary path in the destination directory. On failure the temporary
file is removed and any existing destination remains unchanged. Writers must close the
output before return, as required for Windows replacement.
"""

import os
import tempfile
from pathlib import Path


def write_atomic(destination, writer, *, overwrite=False):
    """Run writer once on a same-directory temporary path, then replace destination.

    On any failure leave the previous destination unchanged and clean up temporary files.
    """
    destination = Path(destination)
    if destination.exists() and not overwrite:
        raise FileExistsError(str(destination))
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary)
    try:
        writer(temporary)
        if destination.exists() and not overwrite:
            raise FileExistsError(str(destination))
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
