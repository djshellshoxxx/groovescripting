"""Build deterministic source, launcher and example downloads for the Pages site."""

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "downloads"
DEST.mkdir(parents=True, exist_ok=True)


def archive(name, paths):
    with zipfile.ZipFile(DEST / name, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for path in sorted(set(paths)):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                info = zipfile.ZipInfo(
                    "groovescripting/" + path.relative_to(ROOT).as_posix(), (2026, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                out.writestr(info, path.read_bytes())


source = []
for folder in ("groovescripting", "spec", "tests", "examples", "scripts", "tasks", ".github"):
    source.extend((ROOT / folder).rglob("*"))
source.extend(ROOT / name for name in ("README.md", "LICENSE", "pyproject.toml", "MANIFEST.in"))
source.extend(
    path for path in (ROOT / "docs").rglob("*") if "downloads" not in path.relative_to(ROOT / "docs").parts
)
archive("groovescripting-source.zip", source)
archive(
    "groovescripting-launchers.zip",
    list((ROOT / "scripts").glob("*.sh")) + list((ROOT / "scripts").glob("*.ps1")),
)
archive("groovescripting-examples.zip", (ROOT / "examples").rglob("*"))
for distribution in (ROOT / "dist").glob("*"):
    if distribution.is_file():
        shutil.copyfile(distribution, DEST / distribution.name)
print("Created three website download bundles and copied distributions")
