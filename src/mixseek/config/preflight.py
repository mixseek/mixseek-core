"""プリフライトチェック: 設定検証ロジックとデータモデル

`mixseek exec --dry-run` によるプリフライト検証を提供する。
通常の exec 実行時にも同じ検証が自動実行され、エラーがあれば実行前に中断する。

設計方針:
- 通常exec実行と同一のロードパスを使用（workspace解決等の挙動差異を防ぐ）
- カテゴリ単位でエラーを隔離（1カテゴリの失敗が他カテゴリの検証を阻害しない）
- Orchestratorロード失敗時のみ後続全スキップ（チームパス等が不明なため）
"""

import importlib
import logging
import re
import tempfile
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.schema import (
    EvaluatorSettings,
    JudgmentSettings,
    MemberAgentSettings,
    TeamSettings,
)
from mixseek.core.auth import (
    AuthenticationError,
    AuthProvider,
    detect_auth_provider,
    validate_anthropic_credentials,
    validate_google_ai_credentials,
    validate_grok_credentials,
    validate_openai_credentials,
    validate_vertex_ai_credentials,
)
from mixseek.evaluator.metrics.base import BaseMetric
from mixseek.orchestrator import load_orchestrator_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# データモデル
# ---------------------------------------------------------------------------


class CheckStatus(str, Enum):
    """チェック結果ステータス"""

    OK = "ok"
    WARN = "warn"
    ERROR = "error"
    SKIPPED = "skipped"


class CheckResult(BaseModel):
    """個別チェック項目の結果"""

    name: str
    status: CheckStatus
    message: str = ""
    source_file: str | None = None


class CategoryResult(BaseModel):
    """カテゴリ単位の検証結果"""

    category: str
    checks: list[CheckResult] = []

    @property
    def has_errors(self) -> bool:
        """ERROR ステータスのチェックが含まれるか"""
        return any(c.status == CheckStatus.ERROR for c in self.checks)


class PreflightResult(BaseModel):
    """プリフライトチェック全体の結果"""

    categories: list[CategoryResult] = []

    @property
    def is_valid(self) -> bool:
        """全カテゴリにエラーがないか"""
        return not any(cat.has_errors for cat in self.categories)

    @property
    def error_count(self) -> int:
        """ERROR ステータスの総数"""
        return sum(1 for cat in self.categories for c in cat.checks if c.status == CheckStatus.ERROR)

    @property
    def warn_count(self) -> int:
        """WARN ステータスの総数"""
        return sum(1 for cat in self.categories for c in cat.checks if c.status == CheckStatus.WARN)


# ---------------------------------------------------------------------------
# プロバイダ→バリデータ関数マッピング
# ---------------------------------------------------------------------------

_AUTH_VALIDATORS: dict[AuthProvider, Callable[[], None]] = {
    AuthProvider.GOOGLE_AI: validate_google_ai_credentials,
    AuthProvider.VERTEX_AI: validate_vertex_ai_credentials,
    AuthProvider.OPENAI: validate_openai_credentials,
    AuthProvider.ANTHROPIC: validate_anthropic_credentials,
    AuthProvider.GROK: validate_grok_credentials,
    AuthProvider.GROK_RESPONSES: validate_grok_credentials,
}

# テスト専用モデルIDフィルタ（detect_auth_provider()で解決不可）
_TEST_MODEL_IDS = {"test_model", "test"}

# ビルトインメトリクス名
_BUILTIN_METRIC_NAMES = {"ClarityCoherence", "Coverage", "LLMPlain", "Relevance"}


# ---------------------------------------------------------------------------
# 個別検証関数
# ---------------------------------------------------------------------------


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
                status=CheckStatus.WARN,
                message="チーム設定が定義されていません",
            )
        )
        return CategoryResult(category="チーム", checks=checks), team_settings_list

    config_manager = ConfigurationManager(workspace=workspace)

    for i, team_entry in enumerate(teams):
        team_config_path = team_entry.get("config", "")
        try:
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


def _validate_evaluator(
    settings: OrchestratorSettings | Any, workspace: Path
) -> tuple[CategoryResult, EvaluatorSettings | None]:
    """Evaluator設定を検証する。

    ConfigurationManager.get_evaluator_settings() と同じパスで検証。
    """
    checks: list[CheckResult] = []
    config_manager = ConfigurationManager(workspace=workspace)
    try:
        eval_settings = config_manager.get_evaluator_settings(settings.evaluator_config)
        source = settings.evaluator_config
        msg = "Evaluator設定を読み込みました" if source else "デフォルトのEvaluator設定を使用します"
        checks.append(
            CheckResult(
                name="evaluator_config",
                status=CheckStatus.OK,
                message=msg,
                source_file=str(source) if source else None,
            )
        )
        return CategoryResult(category="Evaluator", checks=checks), eval_settings
    except Exception as e:
        checks.append(
            CheckResult(
                name="evaluator_config",
                status=CheckStatus.ERROR,
                message=f"Evaluator設定の読み込みに失敗: {e}",
                source_file=str(settings.evaluator_config) if settings.evaluator_config else None,
            )
        )
        return CategoryResult(category="Evaluator", checks=checks), None


def _validate_judgment(
    settings: OrchestratorSettings | Any, workspace: Path
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


def _collect_model_ids(
    team_settings_list: list[TeamSettings],
    evaluator_settings: EvaluatorSettings | None,
    judgment_settings: JudgmentSettings | None,
) -> set[str]:
    """全設定からモデルIDを収集する。

    テスト専用モデルはフィルタ除外する。
    """
    model_ids: set[str] = set()

    # チーム設定からモデルIDを収集
    for team in team_settings_list:
        # リーダーのモデル（未指定時はデフォルト値を使用）
        leader_model = team.leader.get("model", "google-gla:gemini-2.5-flash-lite")
        if leader_model:
            model_ids.add(leader_model)

        # メンバーのモデル
        for member in team.members:
            if isinstance(member, MemberAgentSettings):
                if member.model:
                    model_ids.add(member.model)
            elif isinstance(member, dict):
                m = member.get("model", "")
                if m:
                    model_ids.add(m)

    # Evaluator設定からモデルIDを収集
    if evaluator_settings is not None:
        if evaluator_settings.default_model:
            model_ids.add(evaluator_settings.default_model)
        for metric in evaluator_settings.metrics:
            metric_model = metric.get("model")
            if metric_model:
                model_ids.add(metric_model)

    # Judgment設定からモデルIDを収集
    if judgment_settings is not None:
        if judgment_settings.model:
            model_ids.add(judgment_settings.model)

    # テスト専用モデルをフィルタ除外
    model_ids -= _TEST_MODEL_IDS

    return model_ids


def _validate_auth(
    team_settings_list: list[TeamSettings],
    evaluator_settings: EvaluatorSettings | None,
    judgment_settings: JudgmentSettings | None,
) -> CategoryResult:
    """認証情報を検証する。

    全モデルIDを収集し、プロバイダごとにグループ化して検証する。
    """
    checks: list[CheckResult] = []

    model_ids = _collect_model_ids(team_settings_list, evaluator_settings, judgment_settings)

    if not model_ids:
        checks.append(
            CheckResult(
                name="auth",
                status=CheckStatus.SKIPPED,
                message="検証対象のモデルIDがありません",
            )
        )
        return CategoryResult(category="認証", checks=checks)

    # プロバイダごとにグループ化
    provider_models: dict[AuthProvider, list[str]] = {}
    for model_id in model_ids:
        try:
            provider = detect_auth_provider(model_id)
            provider_models.setdefault(provider, []).append(model_id)
        except AuthenticationError as e:
            checks.append(
                CheckResult(
                    name=f"auth_{model_id}",
                    status=CheckStatus.ERROR,
                    message=f"未知のモデルIDプレフィックス: {e}",
                )
            )

    # プロバイダごとにバリデータ実行
    for provider, models in provider_models.items():
        validator = _AUTH_VALIDATORS.get(provider)
        if validator is None:
            # TEST_MODEL等のプロバイダはスキップ
            continue

        try:
            validator()
            checks.append(
                CheckResult(
                    name=f"auth_{provider.value}",
                    status=CheckStatus.OK,
                    message=f"{provider.value} の認証情報を確認しました（モデル: {', '.join(models)}）",
                )
            )
        except AuthenticationError as e:
            checks.append(
                CheckResult(
                    name=f"auth_{provider.value}",
                    status=CheckStatus.ERROR,
                    message=f"{provider.value} の認証に失敗: {e}",
                )
            )

    return CategoryResult(category="認証", checks=checks)


def _validate_custom_metrics(evaluator_settings: EvaluatorSettings | Any) -> CategoryResult:
    """カスタムメトリクスを検証する。

    evaluator.py の _load_custom_metrics_from_config と同じパターンで検証。
    """
    checks: list[CheckResult] = []
    custom_metrics = evaluator_settings.custom_metrics

    if not custom_metrics:
        checks.append(
            CheckResult(
                name="custom_metrics",
                status=CheckStatus.SKIPPED,
                message="カスタムメトリクスは定義されていません",
            )
        )
        return CategoryResult(category="カスタムメトリクス", checks=checks)

    for metric_name, metric_config in custom_metrics.items():
        try:
            module_path = metric_config.get("module")
            class_name = metric_config.get("class")

            if not module_path or not class_name:
                raise ValueError(
                    f"カスタムメトリクス '{metric_name}' に 'module' と 'class' フィールドが必要です。"
                    f" 設定: {metric_config}"
                )

            # モジュールをインポート
            module = importlib.import_module(module_path)

            # クラスを取得
            if not hasattr(module, class_name):
                raise AttributeError(f"モジュール '{module_path}' にクラス '{class_name}' が見つかりません")
            metric_class = getattr(module, class_name)

            # インスタンス化
            metric_instance = metric_class()

            # BaseMetric を継承しているか検証
            if not isinstance(metric_instance, BaseMetric):
                raise TypeError(
                    f"クラス '{class_name}' は BaseMetric を継承していません。"
                    f" {module_path}.{class_name} が BaseMetric を継承していることを確認してください"
                )

            checks.append(
                CheckResult(
                    name=f"custom_metric_{metric_name}",
                    status=CheckStatus.OK,
                    message=f"カスタムメトリクス '{metric_name}' を検証しました",
                )
            )
        except Exception as e:
            checks.append(
                CheckResult(
                    name=f"custom_metric_{metric_name}",
                    status=CheckStatus.ERROR,
                    message=f"カスタムメトリクス '{metric_name}' の検証に失敗: {e}",
                )
            )

    return CategoryResult(category="カスタムメトリクス", checks=checks)


def _validate_metric_names(evaluator_settings: EvaluatorSettings | Any) -> CategoryResult:
    """メトリクス名が解決可能かを検証する。

    Evaluator._get_metric() と同等の3段階解決ロジック:
    1. カスタムメトリクスレジストリ
    2. ビルトインメトリクス
    3. メトリクスディレクトリからの動的ロード
    """
    checks: list[CheckResult] = []
    custom_metric_names = set(evaluator_settings.custom_metrics.keys())

    for metric in evaluator_settings.metrics:
        metric_name = metric.get("name", "")
        if not metric_name:
            checks.append(
                CheckResult(
                    name="metric_name_empty",
                    status=CheckStatus.ERROR,
                    message="メトリクス名が空です",
                )
            )
            continue

        # 1. カスタムメトリクスレジストリ
        if metric_name in custom_metric_names:
            checks.append(
                CheckResult(
                    name=f"metric_{metric_name}",
                    status=CheckStatus.OK,
                    message=f"カスタムメトリクス '{metric_name}' が登録されています",
                )
            )
            continue

        # 2. ビルトインメトリクス
        if metric_name in _BUILTIN_METRIC_NAMES:
            checks.append(
                CheckResult(
                    name=f"metric_{metric_name}",
                    status=CheckStatus.OK,
                    message=f"ビルトインメトリクス '{metric_name}'",
                )
            )
            continue

        # 3. メトリクスディレクトリからの動的ロード
        try:
            snake_case_name = re.sub(r"(?<!^)(?=[A-Z])", "_", metric_name).lower()
            module_path = f"mixseek.evaluator.metrics.{snake_case_name}"
            module = importlib.import_module(module_path)
            metric_class = getattr(module, metric_name)
            metric_instance = metric_class()
            if not isinstance(metric_instance, BaseMetric):
                raise TypeError(f"'{metric_name}' は BaseMetric を継承していません")
            checks.append(
                CheckResult(
                    name=f"metric_{metric_name}",
                    status=CheckStatus.OK,
                    message=f"メトリクス '{metric_name}' を動的にロードしました",
                )
            )
        except Exception as e:
            checks.append(
                CheckResult(
                    name=f"metric_{metric_name}",
                    status=CheckStatus.ERROR,
                    message=f"メトリクス '{metric_name}' が見つかりません: {e}",
                )
            )

    return CategoryResult(category="メトリクス名", checks=checks)


def _validate_workspace_writable(workspace: Path) -> CategoryResult:
    """ワークスペースディレクトリへの書き込み権限を検証する。"""
    checks: list[CheckResult] = []
    try:
        with tempfile.NamedTemporaryFile(dir=workspace, delete=True):
            pass
        checks.append(
            CheckResult(
                name="workspace_writable",
                status=CheckStatus.OK,
                message=f"ワークスペース '{workspace}' は書き込み可能です",
            )
        )
    except (PermissionError, OSError, FileNotFoundError) as e:
        checks.append(
            CheckResult(
                name="workspace_writable",
                status=CheckStatus.ERROR,
                message=f"ワークスペース '{workspace}' に書き込みできません: {e}",
            )
        )
    return CategoryResult(category="ワークスペース", checks=checks)


# ---------------------------------------------------------------------------
# 公開API
# ---------------------------------------------------------------------------


def run_preflight_check(config_path: Path, workspace: Path | None = None) -> PreflightResult:
    """プリフライトチェックを実行する。

    全設定ファイルの事前包括検証を行い、結果を返す。

    Args:
        config_path: オーケストレータ設定TOMLファイルパス
        workspace: ワークスペースパス（Noneの場合は環境変数から解決）

    Returns:
        PreflightResult: 検証結果
    """
    categories: list[CategoryResult] = []

    # 1. Orchestrator（失敗時は後続全スキップ）
    orch_result, orch_settings = _validate_orchestrator(config_path, workspace)
    categories.append(orch_result)
    if orch_settings is None:
        return PreflightResult(categories=categories)

    # 解決済みworkspaceを使用
    resolved_workspace = orch_settings.workspace_path

    # 2. チーム（個別に検証、1チームの失敗が他をブロックしない）
    team_result, team_settings_list = _validate_teams(orch_settings, resolved_workspace)
    categories.append(team_result)

    # 3. Evaluator
    eval_result, evaluator_settings = _validate_evaluator(orch_settings, resolved_workspace)
    categories.append(eval_result)

    # 4. Judgment
    judg_result, judgment_settings = _validate_judgment(orch_settings, resolved_workspace)
    categories.append(judg_result)

    # 5. PromptBuilder
    pb_result = _validate_prompt_builder(orch_settings, resolved_workspace)
    categories.append(pb_result)

    # 6. 認証（収集できたモデルIDに基づいて検証）
    auth_result = _validate_auth(team_settings_list, evaluator_settings, judgment_settings)
    categories.append(auth_result)

    # 7. カスタムメトリクス（evaluator設定が取得できた場合のみ）
    if evaluator_settings is not None:
        cm_result = _validate_custom_metrics(evaluator_settings)
        categories.append(cm_result)
    else:
        categories.append(
            CategoryResult(
                category="カスタムメトリクス",
                checks=[
                    CheckResult(
                        name="custom_metrics",
                        status=CheckStatus.SKIPPED,
                        message="Evaluator設定が読み込めないためスキップ",
                    )
                ],
            )
        )

    # 8. メトリクス名解決（evaluator設定が取得できた場合のみ）
    if evaluator_settings is not None:
        mn_result = _validate_metric_names(evaluator_settings)
        categories.append(mn_result)

    # 9. ワークスペース書き込み権限
    ws_result = _validate_workspace_writable(resolved_workspace)
    categories.append(ws_result)

    return PreflightResult(categories=categories)
