"""プリフライトチェック: オーケストレータ設定検証"""

from pathlib import Path

from mixseek.config import OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.orchestrator import load_orchestrator_settings


def _validate_orchestrator(
    config_path: Path, workspace: Path | None
) -> tuple[CategoryResult, OrchestratorSettings | None]:
    """オーケストレータ設定を検証する。

    exec.py の _load_and_validate_config と同じ load_orchestrator_settings() を使用。
    """
    checks: list[CheckResult] = []
    try:
        settings = load_orchestrator_settings(config_path, workspace=workspace)
        checks.append(
            CheckResult(
                name="orchestrator_config",
                status=CheckStatus.OK,
                message="オーケストレータ設定を読み込みました",
                source_file=str(config_path),
            )
        )
        return CategoryResult(category="オーケストレータ", checks=checks), settings
    except Exception as e:
        checks.append(
            CheckResult(
                name="orchestrator_config",
                status=CheckStatus.ERROR,
                message=f"オーケストレータ設定の読み込みに失敗: {e}",
                source_file=str(config_path),
            )
        )
        return CategoryResult(category="オーケストレータ", checks=checks), None
