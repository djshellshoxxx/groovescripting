# Developer Guide

```sh
python -m pip install '.[dev]'
python -m pytest          # 179 pass on this snapshot (Linux, Python 3.13)
python -m build
python scripts/package_downloads.py
```

CI tests Python on Linux, Windows and macOS (`.github/workflows/ci.yml`). The Pages workflow packages the downloads and publishes `docs/`. Offline render and hardware validation are documented in `docs/verification.md`.
