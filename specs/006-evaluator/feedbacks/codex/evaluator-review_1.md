# Mixseek Core Evaluator レビュー

## サマリ
ステージ済みの Evaluator 変更は骨格を整えていますが、仕様上クリティカルな欠落が複数残っています。`specs/006-evaluator/spec.md` に記載された必須要件を満たしておらず、親仕様（`specs/001-specs/spec.md`）が求める重み付け設定とカスタムメトリクス拡張性とも整合していません。以下の課題を解消するまでは本ブランチを準拠と見なせません。

## 指摘事項
1. **FR-008 – 重み未指定時の均等割り当てフォールバックが未実装（重大）**  
   `specs/006-evaluator/spec.md` は、TOML で重みが指定されなかった場合に均等重み付けを提供することを要求しています。しかし `MetricConfig.weight` が必須フィールドとして定義されているため（`src/mixseek/models/evaluation_config.py:45-57`）、等分計算を行う代わりにバリデーションエラーが発生します。`Evaluator`／`EvaluationConfig` のいずれにもフォールバック実装が存在せず、要件未達です。

2. **FR-010 – メトリクス評価時に設定可能なリトライ回数が無視されている（重大）**  
   `EvaluationConfig` に `max_retries` が用意されているにもかかわらず、各組み込みメトリクスは `evaluate_with_llm(..., max_retries=3)` を直接呼び出しており、実行時のリトライ回数がハードコードされています（`src/mixseek/evaluator/metrics/clarity_coherence.py:70-77`、`src/mixseek/evaluator/metrics/coverage.py:70-77`、`src/mixseek/evaluator/metrics/relevance.py:70-76`）。設定でリトライ回数を調整できるようにするという仕様要件に反します。

3. **EvaluationConfig のスキーマが必須項目と不整合（重大）**  
   仕様のエンティティ定義では `default_model` に加えて `metric_weights`、`enabled_metrics`、`custom_metrics` を必須としており（`specs/006-evaluator/spec.md`「主要エンティティ」）、`Evaluator` もそれを前提にしています。現実装では `default_model`・`max_retries`・`metric` 配列のみを公開し、`Evaluator` もこの配列しか参照していません（`src/mixseek/models/evaluation_config.py:118-137`、`src/mixseek/evaluator/evaluator.py:57-90`）。その結果として以下の問題が生じます。
   - 仕様で求められる `enabled_metrics` リストが存在せず、メトリクスをオン／オフするシナリオを表現できません。
   - ドキュメント化された契約に一致する `metric_weights` 辞書が存在しません。
   - `custom_metrics` が欠落しており、TOML に宣言された Python 関数を検出できないため、両仕様で説明されている FR-007 のカスタム評価器統合経路が断たれています。

上記の修正を行い、再度ステージしてから再評価を依頼してください。
