"""プリフライトチェック: PromptBuilder設定検証"""

from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus


def _validate_prompt_builder(settings: OrchestratorSettings | Any, workspace: Path) -> CategoryResult:
    """PromptBuilder設定を検証する。

    ConfigurationManager.get_prompt_builder_settings() と同じパスで検証。
    """
    checks: list[CheckResult] = []
    config_manager = ConfigurationManager(workspace=workspace)
    try:
        config_manager.get_prompt_builder_settings(settings.prompt_builder_config)
        source = settings.prompt_builder_config
        msg = "PromptBuilder設定を読み込みました" if source else "デフォルトのPromptBuilder設定を使用します"
        checks.append(
            CheckResult(
                name="prompt_builder_config",
                status=CheckStatus.OK,
                message=msg,
                source_file=str(source) if source else None,
            )
        )
    except Exception as e:
        checks.append(
            CheckResult(
                name="prompt_builder_config",
                status=CheckStatus.ERROR,
                message=f"PromptBuilder設定の読み込みに失敗: {e}",
                source_file=(str(settings.prompt_builder_config) if settings.prompt_builder_config else None),
            )
        )
    return CategoryResult(category="PromptBuilder", checks=checks)
