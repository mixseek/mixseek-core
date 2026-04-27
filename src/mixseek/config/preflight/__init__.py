"""プリフライトチェック: 設定検証ロジックとデータモデル

`mixseek exec --dry-run` によるプリフライト検証を提供する。
通常の exec 実行時にも同じ検証が自動実行され、エラーがあれば実行前に中断する。
"""

from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus, PreflightResult
from mixseek.config.preflight.runner import run_preflight_check
from mixseek.config.preflight.validators import (
    _detect_unit_kind,
    _validate_auth,
    _validate_custom_metrics,
    _validate_evaluator,
    _validate_judgment,
    _validate_metric_names,
    _validate_orchestrator,
    _validate_prompt_builder,
    _validate_teams,
    _validate_workflows,
    _validate_workspace_writable,
)

__all__ = [
    # データモデル
    "CheckStatus",
    "CheckResult",
    "CategoryResult",
    "PreflightResult",
    # 公開API
    "run_preflight_check",
    # 個別検証関数（テストから使用）
    "_detect_unit_kind",
    "_validate_orchestrator",
    "_validate_teams",
    "_validate_workflows",
    "_validate_evaluator",
    "_validate_judgment",
    "_validate_prompt_builder",
    "_validate_auth",
    "_validate_custom_metrics",
    "_validate_metric_names",
    "_validate_workspace_writable",
]
