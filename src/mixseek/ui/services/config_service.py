"""Config service for loading and parsing TOML configuration files."""

import tomllib
from datetime import datetime

from mixseek.ui.models.config import ConfigFile, OrchestrationOption
from mixseek.ui.utils.workspace import get_configs_dir


def list_config_files() -> list[ConfigFile]:
    """configs/配下のすべての.tomlファイルを取得.

    Returns:
        list[ConfigFile]: 設定ファイルのリスト（last_modified降順）
    """
    configs_dir = get_configs_dir()
    toml_files = sorted(configs_dir.glob("*.toml"), key=lambda p: p.stat().st_mtime, reverse=True)

    config_files = []
    for file_path in toml_files:
        try:
            content = file_path.read_text()
            config_files.append(
                ConfigFile(
                    file_path=file_path,
                    file_name=file_path.name,
                    last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    content=content,
                )
            )
        except Exception:
            # TOML構文エラーはスキップ（設定ページで表示）
            continue

    return config_files


def validate_orchestrator_config(content: str) -> bool:
    """オーケストレーター設定ファイルの妥当性を検証.

    Args:
        content: TOML文字列

    Returns:
        bool: 有効な設定ファイルの場合True
    """
    try:
        data = tomllib.loads(content)

        # [orchestrator]セクションの存在を確認
        if "orchestrator" not in data:
            return False

        orchestrator = data["orchestrator"]

        # [[orchestrator.teams]]配列の存在と非空を確認
        teams = orchestrator.get("teams", [])
        if not isinstance(teams, list) or len(teams) == 0:
            return False

        # 各teamに必須フィールド(config)が存在することを確認
        for team in teams:
            if not isinstance(team, dict) or "config" not in team:
                return False

        return True
    except tomllib.TOMLDecodeError:
        return False


def get_all_orchestration_options() -> list[OrchestrationOption]:
    """すべての設定ファイルからオーケストレーション選択肢を生成.

    Returns:
        list[OrchestrationOption]: 選択肢リスト（ファイル名ベース）

    Note:
        実際のmixseek-coreでは、1つの設定ファイル = 1つのオーケストレーション
    """
    config_files = list_config_files()
    options = []

    for config_file in config_files:
        if validate_orchestrator_config(config_file.content):
            # ファイル名（拡張子なし）をオーケストレーションIDとして使用
            orchestration_id = config_file.display_name
            option = OrchestrationOption(
                config_file_name=config_file.file_name,
                orchestration_id=orchestration_id,
                display_label=orchestration_id,
            )
            options.append(option)

    return options
