#!/usr/bin/env bash
set -euo pipefail
exec "${GROOVESCRIPTING_PYTHON:-python3}" -m groovescripting groovbss "$@"
