# リファクタリング計画: evaluator サブシステム

## 概要（責務と依存の現状）

evaluator サブシステムは LLM-as-a-Judge による Submission 評価を担う。実測行数（wc -l）:

| ファイル | 行数 | 備考 |
|---|---|---|
| `src/mixseek/evaluator/evaluator.py` | 531 | **300行ルール違反** |
| `src/mixseek/evaluator/metrics/base.py` | 305 | **300行ルール違反（僅差）** |
| `src/mixseek/evaluator/llm_client.py` | 140 | |
| `src/mixseek/evaluator/exceptions.py` | 107 | |
| `metrics/clarity_coherence.py` ほか3メトリクス | 63〜68 | プロンプト定義のみで健全 |

- **責務**: `Evaluator` がメトリクスの解決（組み込み/カスタム/動的ロード）・逐次評価・重み付き総合スコア計算を担当。
  `LLMJudgeMetric`（metrics/base.py）が共通評価フロー、`llm_client.evaluate_with_llm` が pydantic-ai Agent 呼び出し。
- **依存（内向き）**: `config.schema`（EvaluatorSettings）、`models.evaluation_config/request/result`、
  `core.auth.create_authenticated_model`、`core.model_settings.build_model_settings`、`prompt_builder`。
- **依存（外向きの利用者）**: `round_controller/controller.py:22`、`cli/commands/evaluate_helper.py:13`、
  `config/preflight/validators/evaluator.py:10`。
- **循環依存の兆候**: `metrics/base.py:187-189` で「evaluator → prompt_builder → round_controller → evaluator」の
  循環回避のため関数内 import を行っており、レイヤ構造の歪みが明示的にコメントされている。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
公開 API（`evaluator/__init__.py`）は `Evaluator` と models 3クラスのみで明快。一方 `Evaluator` クラス自体は
「メトリクスレジストリ管理」「動的ロード」「評価実行」「スコア集計」の4責務を抱え単一責任から逸脱気味。

### 観点2: 設計上の臭い
- **データの引き回し（tramp data）**: `evaluator.py:177-186` で `get_model_for_metric` 等のゲッターを11回呼び、
  11個の引数を `LLMJudgeMetric.evaluate`（base.py:198-217、引数17個）→ `evaluate_with_llm`
  （llm_client.py:16-30、引数13個）→ `build_model_settings` へとバケツリレーしている。
  `models/evaluation_config.py:578-796` の `get_*_for_metric` 11メソッドはフォールバック処理がほぼ同一の重複。
- **動的ロード処理の重複（DRY違反）**: `_load_custom_metrics_from_config`（evaluator.py:350-409）と
  `_load_metric_from_directory`（evaluator.py:411-471）が「import → getattr → インスタンス化 →
  BaseMetric 継承検証」をそれぞれ重複実装している。
- **デッドコード**: `evaluator.py:116` の `self._metrics_dir` は代入のみで未使用。
  `llm_client.py:13` の `logger` も未使用。`base.py:294-298` は同一の `assert isinstance` が2回連続。
- **冗長な検証**: `evaluator.py:271` の `hasattr(metric, "evaluate")` チェックは、直前の
  `isinstance(metric, BaseMetric)` 検証（ABC で evaluate は抽象メソッド）と重複し常に True。
- **モデル形式検証の重複**: `llm_client.py:77-94` の "provider:model" 検証は
  `core.auth.detect_auth_provider` 側の解決と役割が重なる。

### 観点3: AGENTS.md 自己ルール違反
- 300行超: `evaluator.py`（531行）、`metrics/base.py`（305行）の2ファイル。
- `evaluator.py:474-532` の `if __name__ == "__main__":` ブロック（59行）は
  `cli/commands/evaluate_helper.py` と機能重複しており、行数超過の一因。
- `os.getenv` 直接呼び出しは無し（`utils.env.get_workspace_path` 経由で規約準拠）。
- ロギングは `logging.getLogger(__name__)` + `extra`（evaluator.py:402-409）で JsonFormatter 前提の
  構造化ログとなっておりプロジェクト慣行に準拠。1関数200行超は無し（最長でも docstring 込み113行程度）。

### 観点4: エラー処理・型
- **未使用例外**: `exceptions.py` の `EvaluatorConfigError` / `WeightValidationError` / `ModelFormatError` は
  src 内のどこからも raise されていない（grep で定義箇所のみヒット）。`llm_client.py:79` は
  `ModelFormatError` があるにもかかわらず素の `ValueError` を投げており例外設計が不整合。
- **広すぎる捕捉**: `evaluator.py:316,399`、`llm_client.py:99,134` で `except Exception` を多用。
  特に evaluator.py:399 はカスタムメトリクスのロード失敗を warning で握り潰すため、設定ミスが実行時の
  `_get_metric` 失敗まで顕在化しない。
- **型の歪み**: `base.py:198` の `async def evaluate(  # type: ignore[override]` は親 `BaseMetric.evaluate`
  （base.py:67-75）とシグネチャ非互換なオーバーライド（LSP違反）。その帰結として `evaluator.py:175` で
  `isinstance(metric, LLMJudgeMetric)` による分岐ディスパッチが必要になっている。
  `evaluator.py:377-378` の mypy 向け `assert` も dict[str, dict[str, Any]] という弱い型付けの代償。

### 観点5: テスト被覆
テスト資産は厚く、リファクタの安全網として十分:
- `tests/evaluator/` 配下に unit / integration / e2e / performance の4層、計約6,200行。
  主要: `unit/test_base_metric.py`（600行）、`integration/test_custom_metrics.py`（591行）、
  `e2e/test_evaluator_e2e.py`（499行）、`integration/test_evaluator_us1.py`/`us2.py`（413/497行）。
- 動的ロードは `unit/test_metric_dynamic_load.py`（53行）でカバー。
- 相対的に薄いのは `unit/test_llm_client.py`（87行）。候補1の着手前に補強推奨。

## リファクタリング候補

### 候補1: LLM呼び出しパラメータのパラメータオブジェクト化
- **対象**: `evaluator.py:176-207`、`metrics/base.py:198-292`、`llm_client.py:16-30`、
  `models/evaluation_config.py:578-796`
- **問題**（観点2: tramp data・DRY違反 / 観点4: 型）: 11個のゲッター呼び出し→17引数→13引数の
  3層バケツリレー。パラメータ追加のたびに4ファイルの修正が必要で、現に `model_settings` /
  `google_model_settings` 追加時に全層へ波及した形跡がある。
- **影響度**: 高（evaluation_config.py 875行の縮減にも波及） / **リスク**: 中（カスタムメトリクスの
  evaluate シグネチャ互換性に注意。`**kwargs` 経由のため移行措置は可能）
- **推奨アプローチ**: `LLMCallParams`（frozen な pydantic モデル）を新設し、
  `EvaluationConfig.get_llm_params_for_metric(name) -> LLMCallParams` に11ゲッターを統合
  （フォールバックは `MetricConfig` と `llm_default` のフィールド走査で一般化）。
  `LLMJudgeMetric.evaluate` / `evaluate_with_llm` は `params: LLMCallParams` を受け取る形に変更。
- **関連テスト**: `tests/evaluator/unit/test_evaluation_config.py`（438行）、`test_base_metric.py`、
  `integration/test_evaluator_us1.py`/`us2.py`。`test_llm_client.py` は事前補強を推奨。
- **工数感**: M

### 候補2: evaluator.py の分割とデッドコード除去（300行ルール対応）
- **対象**: `src/mixseek/evaluator/evaluator.py`（531行）
- **問題**（観点3: 300行超 / 観点2: 重複・デッドコード）: `__main__` ブロック（474-532行）が
  `cli/commands/evaluate_helper.py` と機能重複。動的ロード2関数（350-471行）が検証ロジックを重複実装。
  `_metrics_dir`（116行）未使用、`register_custom_metric` の callable チェック（271行）冗長。
- **影響度**: 高 / **リスク**: 低（公開 API は不変。移動とデッドコード削除が中心）
- **推奨アプローチ**: (1) `__main__` ブロックを削除し CLI（`mixseek evaluate` 系）へ誘導、
  (2) `_get_metric` / `_load_custom_metrics_from_config` / `_load_metric_from_directory` を
  `evaluator/metric_registry.py` として抽出し「import→検証→登録」の共通ヘルパーに統合、
  (3) デッドコード削除。結果として evaluator.py は evaluate / スコア集計のみの200行弱になる見込み。
- **関連テスト**: `unit/test_metric_dynamic_load.py`、`integration/test_custom_metrics.py`（591行）が
  動的ロードを直接カバーしており安全網は十分。
- **工数感**: M

### 候補3: メトリクス基底クラスの継承設計改善（LSP違反解消とbase.py分割）
- **対象**: `src/mixseek/evaluator/metrics/base.py`（305行）、`evaluator.py:175-217`
- **問題**（観点4: 型 / 観点2: 密結合 / 観点3: 300行超）: `base.py:198` の
  `# type: ignore[override]` によるシグネチャ非互換オーバーライドと、それに起因する
  `evaluator.py:175` の isinstance 分岐。`base.py:294-298` の重複 assert。
  `base.py:187-189` の循環 import 回避用の関数内 import。
- **影響度**: 中 / **リスク**: 中（カスタムメトリクス作者向けの公開インターフェース変更を含む）
- **推奨アプローチ**: 候補1の `LLMCallParams` 導入とセットで、`evaluate(user_query, submission,
  context: EvaluationContext)` のように共通シグネチャへ統一し type: ignore を撤廃。
  併せて `BaseLLMEvaluation` + `BaseMetric` を `base.py`、`LLMJudgeMetric` を `llm_judge.py` に分割して
  300行制限を解消。重複 assert は1つに削減。
- **関連テスト**: `unit/test_base_metric.py`（600行）が基底クラス契約を厚くカバー。
  各メトリクス単体テスト（test_clarity_coherence.py 等4本、計約1,200行）も回帰検知に有効。
- **工数感**: M

### 候補4: 例外設計の一貫化（未使用例外の活用または削除）
- **対象**: `src/mixseek/evaluator/exceptions.py`、`src/mixseek/evaluator/llm_client.py`
- **問題**（観点4: 例外設計の不整合 / 観点2: デッドコード）: `EvaluatorConfigError` /
  `WeightValidationError` / `ModelFormatError` が一度も raise されない。`llm_client.py:79,89` は
  `ModelFormatError` の代わりに素の `ValueError` を使用。`llm_client.py:13` の logger 未使用。
  `except Exception` の広すぎる捕捉（llm_client.py:99,134、evaluator.py:316,399）。
- **影響度**: 低 / **リスク**: 低（例外クラスの差し替えは `ModelFormatError(EvaluatorConfigError(ValueError))`
  の継承により ValueError を期待する既存ハンドラと後方互換）
- **推奨アプローチ**: llm_client のモデル形式エラーを `ModelFormatError` に置換。重み検証
  （`_calculate_overall_score` の ValueError）を `WeightValidationError` に置換。利用予定のない例外は削除。
  `except Exception` は捕捉対象を具体化するか、最低限ログに exc_info を残す。未使用 logger を削除。
- **関連テスト**: `unit/test_exceptions.py`（211行）、`unit/test_llm_client.py`（87行）。
  例外型を assert しているテストの更新が少量必要。
- **工数感**: S

### 推奨着手順
候補4（S・低リスクで即効）→ 候補2（行数ルール解消・低リスク）→ 候補1 → 候補3（1と3は連続実施が効率的）。
