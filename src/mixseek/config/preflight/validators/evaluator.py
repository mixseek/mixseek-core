"""プリフライトチェック: Evaluator設定・メトリクス検証"""

import importlib
import re
from pathlib import Path
from typing import Any

from mixseek.config import ConfigurationManager, OrchestratorSettings
from mixseek.config.preflight.models import CategoryResult, CheckResult, CheckStatus
from mixseek.config.schema import EvaluatorSettings
from mixseek.evaluator.metrics.base import BaseMetric

# ビルトインメトリクス名
_BUILTIN_METRIC_NAMES = {"ClarityCoherence", "Coverage", "LLMPlain", "Relevance"}


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

        # 3. metricsディレクトリに直接配置されたカスタムメトリクスの動的ロード
        # ビルトインはステップ2で、TOML [custom_metrics] 経由はステップ1で解決される
        try:
            snake_case_name = re.sub(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))", r"_\1", metric_name).lower()
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
