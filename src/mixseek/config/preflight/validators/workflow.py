"""プリフライトチェック: ワークフロー設定検証"""

from pathlib import Path

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.preflight.validators.util import _detect_unit_kinds
from mixseek.config.schema import WorkflowSettings


def _validate_workflows(
    settings: OrchestratorSettings,
    workspace: Path,
) -> tuple[CategoryResult, list[WorkflowSettings]]:
    """workflow kind の entry を `load_workflow_settings` で検証する。

    `kind != "workflow"` の entry は skip し CheckResult を積まない。
    `unknown` の最終 ERROR 報告は team validator 側で行うため、
    本 validator は「該当 entry のみ報告」に統一する（重複報告を避ける）。

    Args:
        settings: orchestrator 設定
        workspace: 解決済みワークスペース
    """
    checks: list[CheckResult] = []
    workflow_settings_list: list[WorkflowSettings] = []
    config_manager = ConfigurationManager(workspace=workspace)

    unit_kinds = _detect_unit_kinds(settings, workspace)

    for i, (entry, kind) in enumerate(zip(settings.teams, unit_kinds, strict=True)):
        wf_config_path = entry.get("config", "")
        if kind != "workflow":
            continue
        try:
            wf_settings = config_manager.load_workflow_settings(Path(wf_config_path))
            workflow_settings_list.append(wf_settings)
            checks.append(
                CheckResult(
                    name=f"workflow_{i}",
                    status=CheckStatus.OK,
                    message="ワークフロー設定を読み込みました",
                    source_file=wf_config_path,
                )
            )
        except Exception as e:
            checks.append(
                CheckResult(
                    name=f"workflow_{i}",
                    status=CheckStatus.ERROR,
                    message=f"ワークフロー設定の読み込みに失敗: {e}",
                    source_file=wf_config_path,
                )
            )

    return CategoryResult(category="ワークフロー", checks=checks), workflow_settings_list
