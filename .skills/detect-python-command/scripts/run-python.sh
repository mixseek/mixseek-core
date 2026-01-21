#!/usr/bin/env bash
# Run Python Script with Auto-detected Command
# Usage: run-python.sh <script.py> [args...]
#
# Detects the appropriate Python command and executes the given script.

set -euo pipefail

# Check if script argument is provided
if [[ $# -lt 1 ]]; then
    echo "Usage: run-python.sh <script.py> [args...]" >&2
    exit 1
fi

SCRIPT="$1"
shift

# Check if script exists
if [[ ! -f "$SCRIPT" ]]; then
    echo "Error: Script not found: $SCRIPT" >&2
    exit 1
fi

# Detection logic (same as detect-python.sh)
run_with_python() {
    # Priority 1: pyproject.toml exists and uv is installed
    if [[ -f "pyproject.toml" ]] && command -v uv &>/dev/null; then
        exec uv run python "$SCRIPT" "$@"
    fi

    # Priority 2: .venv/bin/python exists
    if [[ -x ".venv/bin/python" ]]; then
        exec .venv/bin/python "$SCRIPT" "$@"
    fi

    # Priority 3: python command exists
    if command -v python &>/dev/null; then
        exec python "$SCRIPT" "$@"
    fi

    # Priority 4: python3 command exists
    if command -v python3 &>/dev/null; then
        exec python3 "$SCRIPT" "$@"
    fi

    # No Python found
    echo "Error: No Python interpreter found" >&2
    exit 1
}

run_with_python "$@"
