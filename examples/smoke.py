"""Run documented offline examples, producing audio and troubleshooting evidence.

Usage: python examples/smoke.py --output-dir DIR
Playback is optional and must be exercised on a machine with an audio device.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, default=Path("example-output"))
a = p.parse_args()
a.output_dir.mkdir(parents=True, exist_ok=True)
DEST = a.output_dir.resolve()


def run(tool, *args):
    subprocess.run([sys.executable, "-m", "groovescripting", tool, *map(str, args)], cwd=ROOT, check=True)


run(
    "groovdrm",
    "--bpm",
    140,
    "--bars",
    2,
    "--voice",
    "kick",
    "--pattern",
    "x...x...x...x...",
    "--output",
    DEST / "kick.wav",
    "--overwrite",
)
run(
    "groovbss",
    "--bpm",
    140,
    "--bars",
    2,
    "--pattern",
    "C2 . G1 . C2 . Bb1 .",
    "--waveform",
    "saw",
    "--output",
    DEST / "bass.wav",
    "--overwrite",
)
run(
    "groovld",
    "--bpm",
    140,
    "--bars",
    2,
    "--pattern",
    "C4 . Eb4 . G4 . Bb4 .",
    "--waveform",
    "saw",
    "--output",
    DEST / "lead.wav",
    "--overwrite",
)
run(
    "groovmix",
    DEST / "kick.wav",
    DEST / "bass.wav",
    DEST / "lead.wav",
    "--normalize",
    "--output",
    DEST / "groove.wav",
    "--overwrite",
)
run(
    "groovseq",
    ROOT / "examples/first-groove.json",
    "--output",
    DEST / "project.wav",
    "--stems",
    DEST / "stems",
    "--overwrite",
)
run("groovseq", ROOT / "examples/arrangement.json", "--output", DEST / "arrangement.wav", "--overwrite")
run(
    "groovfx",
    DEST / "groove.wav",
    "--effect",
    '{"type":"gain","db":-2}',
    "--output",
    DEST / "quieter.wav",
    "--overwrite",
)
run(
    "groovseq",
    ROOT / "examples/first-groove.json",
    "--output",
    DEST / "debug.wav",
    "--log-file",
    DEST / "render.log",
    "--log-level",
    "debug",
    "--log-format",
    "text",
    "--overwrite",
)
run(
    "groovplay",
    "--diagnose",
    "--log-file",
    DEST / "playback.jsonl",
    "--log-level",
    "debug",
    "--log-format",
    "json",
)
run("groovinfo", DEST / "groove.wav", "--json")
run(
    "groovdrm",
    "--voice",
    "snare",
    "--pattern",
    "x...............",
    "--bars",
    1,
    "--output",
    DEST / "single-hit.wav",
    "--overwrite",
)
run(
    "groovbss",
    "--pattern",
    "C2:0.5:1 ~ G2! .",
    "--glide",
    0.08,
    "--legato",
    "--output",
    DEST / "glide.wav",
    "--overwrite",
)
run(
    "groovld",
    "--pattern",
    "C4+Eb4+G4:1 . . .",
    "--arp",
    "up",
    "--arp-rate",
    0.25,
    "--normalize",
    "--output",
    DEST / "arp.wav",
    "--overwrite",
)
run(
    "groovfx",
    DEST / "groove.wav",
    "--effect",
    '{"type":"delay","seconds":0.214,"mix":0.2,"feedback":0.35}',
    "--tail",
    "wrap",
    "--output",
    DEST / "delay-loop.wav",
    "--overwrite",
)
print("Offline documented examples completed:", DEST)
