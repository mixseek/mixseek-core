"""Workspace utility functions for Mixseek UI."""

from pathlib import Path

from mixseek.utils.env import get_workspace_path as _get_workspace_path_common


def get_workspace_path() -> Path:
    """環境変数MIXSEEK_WORKSPACEからワークスペースパスを取得.

    Returns:
        Path: ワークスペースディレクトリの絶対パス

    Raises:
        WorkspacePathNotSpecifiedError: 環境変数が未設定の場合
    """
    return _get_workspace_path_common(cli_arg=None)


def get_configs_dir() -> Path:
    """configs/ディレクトリのパスを取得し、存在しない場合は作成.

    Returns:
        Path: configs/ディレクトリの絶対パス
    """
    configs_dir = get_workspace_path() / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    return configs_dir


def get_db_path() -> Path:
    """mixseek.dbのパスを取得.

    Returns:
        Path: mixseek.dbの絶対パス

    Note:
        ファイルが存在しない場合でもパスを返す（空状態として扱う）
    """
    return get_workspace_path() / "mixseek.db"
