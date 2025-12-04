"""Configuration file validation utilities (Phase 13 T103).

Provides validation functions for configuration files:
- Orchestrator TOML validation
- Section existence checks
- TOML syntax error handling

Article 9 Compliance:
- Explicit error messages with file paths
- No implicit defaults or assumptions
- Proper error propagation
"""

import tomllib
from pathlib import Path


def validate_orchestrator_toml(file_path: Path) -> None:
    """Validate that a TOML file is a valid orchestrator configuration file.

    Checks:
    1. File exists
    2. Valid TOML syntax
    3. Contains [orchestrator] section

    Args:
        file_path: Path to the TOML file to validate

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If TOML syntax is invalid or [orchestrator] section is missing

    Examples:
        >>> validate_orchestrator_toml(Path("orchestrator.toml"))  # Valid file
        >>> validate_orchestrator_toml(Path("invalid.toml"))  # Raises ValueError

    Phase 13 T103: FR-039
    """
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    # Validate TOML syntax
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML syntax in {file_path}: {e}\nPlease check the file for syntax errors.") from e
    except OSError as e:
        raise ValueError(f"Failed to read file {file_path}: {e}") from e

    # Check for [orchestrator] section
    if "orchestrator" not in data:
        raise ValueError(
            f"指定されたファイルは orchestrator 設定ファイルではありません: {file_path}\n"
            f"[orchestrator] セクションが見つかりません。\n"
            f"ファイル内のセクション: {list(data.keys())}"
        )
