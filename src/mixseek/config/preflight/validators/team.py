"""プリフライトチェック: チーム設定検証"""

from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.schema import TeamSettings


def _validate_teams(
    settings: OrchestratorSettings | Any, workspace: Path
) -> tuple[CategoryResult, list[TeamSettings]]:
    """各チーム設定を個別に検証する。

    1チームの失敗が他チームの検証をブロックしない。
    """
    checks: list[CheckResult] = []
    team_settings_list: list[TeamSettings] = []

    teams = settings.teams
    if not teams:
        checks.append(
            CheckResult(
                name="teams",
                status=CheckStatus.ERROR,
                message="チーム設定が定義されていません（1つ以上のチームが必要です）",
            )
        )
        return CategoryResult(category="チーム", checks=checks), team_settings_list

    config_manager = ConfigurationManager(workspace=workspace)

    for i, team_entry in enumerate(teams):
        team_config_path = team_entry.get("config", "")
        try:
            # load_team_settings は TeamSettings の Pydantic バリデータを通じて
            # メンバー設定も検証する（メンバー数上限、agent_name 重複、tool_name 重複、
            # 各 MemberAgentSettings の model 形式・tool_description 必須チェック）
            team_settings = config_manager.load_team_settings(Path(team_config_path))
            team_settings_list.append(team_settings)
            checks.append(
                CheckResult(
                    name=f"team_{i}",
                    status=CheckStatus.OK,
                    message="チーム設定を読み込みました",
                    source_file=team_config_path,
                )
            )
        except Exception as e:
            checks.append(
                CheckResult(
                    name=f"team_{i}",
                    status=CheckStatus.ERROR,
                    message=f"チーム設定の読み込みに失敗: {e}",
                    source_file=team_config_path,
                )
            )

    return CategoryResult(category="チーム", checks=checks), team_settings_list
