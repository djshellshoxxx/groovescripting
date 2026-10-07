"""Entry point for the PyInstaller standalone executable.

Runs `groovescripting TOOL ...`; when the executable itself is renamed to a tool name
(for example groovseq.exe), that tool runs directly.
"""

import multiprocessing
import sys
from pathlib import Path

from groovescripting.cli import TOOLS, main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    name = Path(sys.argv[0]).stem.lower()
    argv = sys.argv[1:]
    if name in TOOLS:
        argv = [name, *argv]
    raise SystemExit(main(argv))
