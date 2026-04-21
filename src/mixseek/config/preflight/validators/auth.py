"""プリフライトチェック: 認証情報検証"""

from collections.abc import Callable

from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.schema import (
    EvaluatorSettings,
    JudgmentSettings,
    LeaderAgentSettings,
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
    validate_qwen_credentials,
    validate_vertex_ai_credentials,
)

# プロバイダ→バリデータ関数マッピング
_AUTH_VALIDATORS: dict[AuthProvider, Callable[[], None]] = {
    AuthProvider.GOOGLE_AI: validate_google_ai_credentials,
    AuthProvider.VERTEX_AI: validate_vertex_ai_credentials,
    AuthProvider.OPENAI: validate_openai_credentials,
    AuthProvider.ANTHROPIC: validate_anthropic_credentials,
    AuthProvider.GROK: validate_grok_credentials,
    AuthProvider.GROK_RESPONSES: validate_grok_credentials,
    AuthProvider.QWEN: validate_qwen_credentials,
}

# テスト専用モデルIDフィルタ（detect_auth_provider()で解決不可）
_TEST_MODEL_IDS = {"test_model", "test"}


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
        if "model" in team.leader:
            leader_model = team.leader["model"]
        else:
            leader_model = LeaderAgentSettings.model_fields["model"].default
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
