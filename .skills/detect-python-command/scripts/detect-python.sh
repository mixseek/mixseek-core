#!/usr/bin/env bash
# Detect Python Command Script
# Usage: detect-python.sh [--verbose]
#
# Detects the appropriate Python command for the current environment.
# Returns the command string to stdout.

set -euo pipefail

VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Logging function (only outputs in verbose mode)
log() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "  $1" >&2
    fi
}

log_header() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$1" >&2
    fi
}

# Main detection logic
detect_python() {
    log_header "Detecting Python command..."

    # Priority 1: pyproject.toml exists and uv is installed
    if [[ -f "pyproject.toml" ]]; then
        log "pyproject.toml: found"
        if command -v uv &>/dev/null; then
            local uv_version
            uv_version=$(uv --version 2>/dev/null | head -1)
            log "uv: installed ($uv_version)"
            log "Result: uv run python"
            echo "uv run python"
            return 0
        else
            log "uv: not installed"
        fi
    else
        log "pyproject.toml: not found"
    fi

    # Priority 2: .venv/bin/python exists
    if [[ -x ".venv/bin/python" ]]; then
        log ".venv/bin/python: exists"
        log "Result: .venv/bin/python"
        echo ".venv/bin/python"
        return 0
    else
        log ".venv/bin/python: not found"
    fi

    # Priority 3: python command exists
    if command -v python &>/dev/null; then
        log "python: found"
        log "Result: python"
        echo "python"
        return 0
    else
        log "python: not found"
    fi

    # Priority 4: python3 command exists
    if command -v python3 &>/dev/null; then
        log "python3: found"
        log "Result: python3"
        echo "python3"
        return 0
    else
        log "python3: not found"
    fi

    # No Python found
    echo "Error: No Python interpreter found" >&2
    return 1
}

# Run detection
detect_python
