#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
"${GROOVESCRIPTING_PYTHON:-python3}" -m groovescripting groovseq "$project_root/examples/first-groove.json" "$@"
