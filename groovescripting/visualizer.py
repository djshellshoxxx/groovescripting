"""Optional ASCII waveform display that follows playback in the terminal."""

import logging
import os
import shutil
import sys
import time

import numpy as np

log = logging.getLogger("groovescripting.visualizer")

DEFAULT_HEIGHT = 9
DEFAULT_SPAN = 2.0
FPS = 30


def _mono(samples):
    samples = np.asarray(samples, dtype=np.float32)
    return samples if samples.ndim == 1 else samples.mean(axis=1)


def _clock(seconds):
    minutes, rest = divmod(max(seconds, 0.0), 60)
    return f"{int(minutes):02d}:{rest:04.1f}"


def frame(samples, sample_rate, position, width=72, height=DEFAULT_HEIGHT, span=DEFAULT_SPAN):
    """Return ASCII rows of a scrolling waveform centred on ``position`` seconds.

    Each column shows the min..max envelope of its slice of audio; ``|`` marks the playhead
    and the final row reports elapsed time and peak level at the playhead.
    """
    if width < 8 or height < 3:
        raise ValueError("visualizer needs at least 8 columns and 3 rows")
    mono = _mono(samples)
    total = len(mono)
    centre = int(position * sample_rate)
    half = int(span * sample_rate / 2)
    edges = np.linspace(centre - half, centre + half, width + 1).astype(np.int64)
    middle = (height - 1) / 2
    centre_row = int(round(middle))
    grid = [[" "] * width for _ in range(height)]
    for row in grid:
        row[width // 2] = "|"
    for column in range(width):
        start, stop = max(edges[column], 0), min(edges[column + 1], total)
        if start >= stop:
            continue
        chunk = mono[start:stop]
        top = int(round(middle - float(np.clip(chunk.max(), -1, 1)) * middle))
        bottom = int(round(middle - float(np.clip(chunk.min(), -1, 1)) * middle))
        mark = "#" if column != width // 2 else "|"
        if top != bottom or top != centre_row:
            for line in range(min(top, bottom), max(top, bottom) + 1):
                grid[line][column] = mark
        if grid[centre_row][column] == " ":
            grid[centre_row][column] = "-"
    window = mono[max(centre - sample_rate // 20, 0) : min(centre + sample_rate // 20, total)]
    peak = float(np.max(np.abs(window))) if len(window) else 0.0
    meter_width = max(width - 34, 4)
    filled = int(round(min(peak, 1.0) * meter_width))
    decibels = f"{20 * np.log10(peak):6.1f} dB" if peak > 1e-5 else "  -inf dB"
    status = (
        f"{_clock(position)} / {_clock(total / sample_rate)}  "
        f"[{'=' * filled}{' ' * (meter_width - filled)}] {decibels}"
    )
    return ["".join(row) for row in grid] + [status[:width].ljust(width)]


def _enable_ansi(stream):
    """Turn on VT escape handling for classic Windows consoles; harmless elsewhere."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-12 if stream is sys.stderr else -11)
        mode = ctypes.c_uint32()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        log.debug("Could not enable ANSI escapes on this console", exc_info=True)


def available(stream=None):
    stream = sys.stderr if stream is None else stream
    return bool(getattr(stream, "isatty", lambda: False)())


class Display:
    """Redraws waveform frames in place while audio plays."""

    def __init__(
        self,
        samples,
        sample_rate,
        stream=None,
        height=DEFAULT_HEIGHT,
        width=None,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        self.samples = samples
        self.sample_rate = sample_rate
        self.duration = len(samples) / sample_rate
        self.stream = sys.stderr if stream is None else stream
        self.height = height
        columns = shutil.get_terminal_size((80, 24)).columns
        self.width = width or max(min(columns - 1, 120), 8)
        self.clock = clock
        self.sleep = sleep
        self.drawn = 0

    def draw(self, position):
        rows = frame(self.samples, self.sample_rate, position, self.width, self.height)
        prefix = f"\x1b[{self.drawn}F" if self.drawn else ""
        self.stream.write(prefix + "\n".join(rows) + "\n")
        self.stream.flush()
        self.drawn = len(rows)

    def run(self, finished=None):
        """Animate from 0 to the end of the audio, or until ``finished()`` returns True."""
        _enable_ansi(self.stream)
        self.stream.write("\x1b[?25l")
        try:
            started = self.clock()
            while True:
                elapsed = self.clock() - started
                if elapsed >= self.duration or (finished is not None and finished()):
                    break
                self.draw(elapsed)
                self.sleep(1 / FPS)
            self.draw(self.duration)
        finally:
            self.stream.write("\x1b[?25h")
            self.stream.flush()
