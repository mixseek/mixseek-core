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

# Get the directory of the current script to reliably call detect-python.sh
SCRIPT_DIR=$(dirname "$0")

# Detect the python command by calling the detection script.
# The error from detect-python.sh will be propagated to stderr.
PYTHON_CMD=$("$SCRIPT_DIR/detect-python.sh") || exit 1

# Execute the script with the detected python command.
# The command might contain spaces (e.g., "uv run python").
# Using an array is a safe way to handle this.
read -ra cmd_array <<< "$PYTHON_CMD"
exec "${cmd_array[@]}" "$SCRIPT" "$@"
