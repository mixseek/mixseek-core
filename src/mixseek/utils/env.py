"""Environment variable handling utilities."""

import logging
import os
from pathlib import Path

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.constants import WORKSPACE_ENV_VAR
from mixseek.exceptions import WorkspacePathNotSpecifiedError

logger = logging.getLogger(__name__)


def get_workspace_from_env() -> Path | None:
    """環境変数からワークスペースパスを取得します。

    Returns:
        環境変数から取得したワークスペースパス、または None
    """
    env_workspace = os.environ.get(WORKSPACE_ENV_VAR)
    if env_workspace:
        return Path(env_workspace)
    return None


def get_workspace_path(cli_arg: Path | None) -> Path:
    """
    Get workspace path with priority logic (Phase 12: ConfigurationManager).

    Priority:
    1. CLI argument (--workspace)
    2. Environment variables
    3. TOML config
    4. Error if none provided

    Args:
        cli_arg: Path provided via CLI option (if any)

    Returns:
        Resolved workspace path

    Raises:
        WorkspacePathNotSpecifiedError: If no workspace path is provided
    """
    if cli_arg:
        return cli_arg

    # Check environment variable directly first (for init command compatibility)
    if workspace := get_workspace_from_env():
        return workspace

    # Use ConfigurationManager for centralized workspace resolution (Article 9 compliance)
    try:
        config_manager = ConfigurationManager(workspace=None)
        orchestrator_settings: OrchestratorSettings = config_manager.load_settings(OrchestratorSettings)
        return orchestrator_settings.workspace_path
    except Exception:
        # Fallback: Raise error with clear message
        raise WorkspacePathNotSpecifiedError(WORKSPACE_ENV_VAR)


def get_workspace_for_config(cli_arg: Path | None = None) -> Path:
    """
    Get workspace path for config file resolution (Phase 12: ConfigurationManager).

    This function is used to resolve relative paths in configuration files.
    Article 9準拠: 暗黙的フォールバックを禁止し、明示的なエラーを発生させます。

    Priority:
    1. CLI argument (if provided)
    2. ConfigurationManager (ENV, .env, TOML)
    3. Error (Article 9: no implicit fallback)

    Args:
        cli_arg: Optional CLI-provided workspace path

    Returns:
        Workspace path for config file resolution

    Raises:
        WorkspacePathNotSpecifiedError: workspace未指定の場合
    """
    if cli_arg:
        return cli_arg

    # Check environment variable directly first (for init command compatibility)
    if workspace := get_workspace_from_env():
        return workspace

    # Article 9準拠: ConfigurationManager経由でworkspaceを取得、フォールバックなし
    try:
        config_manager = ConfigurationManager(workspace=None)
        orchestrator_settings: OrchestratorSettings = config_manager.load_settings(OrchestratorSettings)
        return orchestrator_settings.workspace_path
    except Exception:
        # Article 9準拠: 暗黙的フォールバック禁止、明示的エラー
        raise WorkspacePathNotSpecifiedError(WORKSPACE_ENV_VAR)
