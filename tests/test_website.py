import re
from pathlib import Path

from groovescripting import __version__
from groovescripting.cli import TOOLS

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")


def test_every_tool_has_a_site_card_and_launchers():
    for tool in TOOLS:
        assert f'<article class="tool" id="{tool}"' in INDEX, tool
        assert (ROOT / "scripts" / f"{tool}.sh").is_file(), tool
        assert (ROOT / "scripts" / f"{tool}.ps1").is_file(), tool


def test_distribution_links_match_package_version():
    versions = set(re.findall(r"downloads/groovescripting-([0-9.]+?)(?:-py3-none-any\.whl|\.tar\.gz)", INDEX))
    assert versions == {__version__}


def test_local_site_links_resolve():
    links = re.findall(r'(?:href|src)="([^"#:]+)(?:#[^"]*)?"', INDEX)
    missing = [
        link
        for link in links
        if not link.startswith("downloads/groovescripting-" + __version__) and not (ROOT / "docs" / link).exists()
    ]
    assert not missing
