#!/usr/bin/env bash
# MixSeek Workspace Initialization Script
# Usage: init-workspace.sh [workspace-path]
#
# Creates the standard MixSeek workspace directory structure.
# Existing directories are preserved (non-destructive).

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# Function to create directory if not exists
create_dir() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        print_warning "Already exists: $dir"
    else
        mkdir -p "$dir"
        print_success "Created: $dir"
    fi
}

# Main function
main() {
    # Determine workspace path
    local workspace_path="${1:-${MIXSEEK_WORKSPACE:-$(pwd)}}"

    # Resolve to absolute path
    workspace_path="$(cd "$workspace_path" 2>/dev/null && pwd || echo "$workspace_path")"

    echo "Initializing MixSeek workspace at: $workspace_path"
    echo ""

    # Check if parent directory exists
    local parent_dir
    parent_dir="$(dirname "$workspace_path")"
    if [[ ! -d "$parent_dir" ]]; then
        print_error "Parent directory does not exist: $parent_dir"
        exit 1
    fi

    # Check write permission
    if [[ -d "$workspace_path" ]]; then
        if [[ ! -w "$workspace_path" ]]; then
            print_error "No write permission for: $workspace_path"
            exit 1
        fi
    else
        if [[ ! -w "$parent_dir" ]]; then
            print_error "No write permission for parent directory: $parent_dir"
            exit 1
        fi
    fi

    # Create workspace root if needed
    if [[ ! -d "$workspace_path" ]]; then
        mkdir -p "$workspace_path"
        print_success "Created workspace root: $workspace_path"
    fi

    echo ""
    echo "Creating directory structure..."
    echo ""

    # Create standard directories
    create_dir "$workspace_path/configs/agents"
    create_dir "$workspace_path/configs/evaluators"
    create_dir "$workspace_path/configs/judgment"
    create_dir "$workspace_path/logs"
    create_dir "$workspace_path/templates"

    echo ""
    echo "Workspace initialization complete!"
    echo ""
    echo "Directory structure:"
    echo "  $workspace_path/"
    echo "  ├── configs/"
    echo "  │   ├── agents/       # Team configurations (team-*.toml)"
    echo "  │   ├── evaluators/   # Evaluator settings (evaluator.toml)"
    echo "  │   └── judgment/     # Judgment settings (judgment.toml)"
    echo "  ├── logs/             # Execution logs"
    echo "  └── templates/        # Configuration templates"
    echo ""
    echo "Recommended: Set environment variable"
    echo "  export MIXSEEK_WORKSPACE=\"$workspace_path\""
}

# Run main function
main "$@"
