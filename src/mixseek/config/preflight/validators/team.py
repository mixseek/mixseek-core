"""プリフライトチェック: チーム設定検証"""

from pathlib import Path

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.preflight.validators.util import _detect_unit_kinds
from mixseek.config.schema import TeamSettings


def _validate_teams(
    settings: OrchestratorSettings,
    workspace: Path,
) -> tuple[CategoryResult, list[TeamSettings]]:
    """team kind と unknown kind の entry を `load_unit_settings` で検証する。

    1チームの失敗が他チームの検証をブロックしない。

    Dispatch 方針:
        - `kind == "workflow"` の entry は skip（`_validate_workflows` 側で処理）
        - `kind == "team"` の entry: `load_unit_settings` 経由で TeamSettings を取得
        - `kind == "unknown"` (TOML 解析失敗 / 両セクション同居 / どちらもなし /
          file not found) の entry: `load_unit_settings` が必ず例外を raise するため
          except で ERROR 化する。これにより「全 entry が必ずどこかの validator で
          ERROR 化される」設計 invariant を維持する。

    Args:
        settings: orchestrator 設定
        workspace: 解決済みワークスペース
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

    unit_kinds = _detect_unit_kinds(settings, workspace)
    config_manager = ConfigurationManager(workspace=workspace)

    for i, (team_entry, kind) in enumerate(zip(teams, unit_kinds, strict=True)):
        team_config_path = team_entry.get("config", "")
        if kind == "workflow":
            continue

        try:
            # load_unit_settings は TeamSettings の Pydantic バリデータを通じて
            # メンバー設定も検証する（メンバー数上限、agent_name 重複、tool_name 重複、
            # 各 MemberAgentSettings の model 形式・tool_description 必須チェック）。
            # kind == "unknown" の場合は ValueError / FileNotFoundError / TOMLDecodeError
            # を raise するため except で ERROR 化される。
            result = config_manager.load_unit_settings(Path(team_config_path))
            if not isinstance(result, TeamSettings):
                # _detect_unit_kind と load_unit_settings の解釈ずれを検出（想定外）。
                raise TypeError(
                    f"内部不整合: kind=team と判定された entry が "
                    f"{type(result).__name__} を返しました（TeamSettings を期待）"
                )
            team_settings_list.append(result)
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
