"""プリフライトチェック: Judgment設定検証"""

from pathlib import Path

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.schema import JudgmentSettings


def _validate_judgment(
    settings: OrchestratorSettings, workspace: Path
) -> tuple[CategoryResult, JudgmentSettings | None]:
    """Judgment設定を検証する。

    ConfigurationManager.get_judgment_settings() と同じパスで検証。
    """
    checks: list[CheckResult] = []
    config_manager = ConfigurationManager(workspace=workspace)
    try:
        judg_settings = config_manager.get_judgment_settings(settings.judgment_config)
        source = settings.judgment_config
        msg = "Judgment設定を読み込みました" if source else "デフォルトのJudgment設定を使用します"
        checks.append(
            CheckResult(
                name="judgment_config",
                status=CheckStatus.OK,
                message=msg,
                source_file=str(source) if source else None,
            )
        )
        return CategoryResult(category="Judgment", checks=checks), judg_settings
    except Exception as e:
        checks.append(
            CheckResult(
                name="judgment_config",
                status=CheckStatus.ERROR,
                message=f"Judgment設定の読み込みに失敗: {e}",
                source_file=str(settings.judgment_config) if settings.judgment_config else None,
            )
        )
        return CategoryResult(category="Judgment", checks=checks), None
