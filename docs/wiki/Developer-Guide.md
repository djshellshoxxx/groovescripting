# Developer Guide

```sh
python -m pip install '.[dev]'
python -m pytest
python -m build
python scripts/package_downloads.py
```

CI tests Python on Linux, Windows and macOS (`.github/workflows/ci.yml`). The Pages workflow packages the downloads and publishes `docs/`. Offline render and hardware validation are documented in `docs/verification.md`.
