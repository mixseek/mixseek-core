"""プリフライトチェック ランナー

全カテゴリの検証を順次実行し、結果を集約する。

設計方針:
- 通常exec実行と同一のロードパスを使用（workspace解決等の挙動差異を防ぐ）
- カテゴリ単位でエラーを隔離（1カテゴリの失敗が他カテゴリの検証を阻害しない）
- Orchestratorロード失敗時のみ後続全スキップ（チームパス等が不明なため）
"""

from pathlib import Path

from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus, PreflightResult
from mixseek.config.preflight.validators import (
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

    # 2. チーム / ワークフロー
    # 各 validator は内部で entry の kind 判定を行い、自身が担当する種別のみを処理する。
    team_result, team_settings_list = _validate_teams(orch_settings, resolved_workspace)
    categories.append(team_result)

    wf_result, workflow_settings_list = _validate_workflows(orch_settings, resolved_workspace)
    categories.append(wf_result)

    # 3. Evaluator
    eval_result, evaluator_settings = _validate_evaluator(orch_settings, resolved_workspace)
    categories.append(eval_result)

    # 4. Judgment
    judg_result, judgment_settings = _validate_judgment(orch_settings, resolved_workspace)
    categories.append(judg_result)

    # 5. PromptBuilder
    pb_result = _validate_prompt_builder(orch_settings, resolved_workspace)
    categories.append(pb_result)

    # 6. 認証（収集できたモデルIDに基づいて検証、workflow 由来モデルも含む）
    auth_result = _validate_auth(
        team_settings_list,
        evaluator_settings,
        judgment_settings,
        workflow_settings_list,
    )
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

    return PreflightResult(categories=categories, orchestrator_settings=orch_settings)
