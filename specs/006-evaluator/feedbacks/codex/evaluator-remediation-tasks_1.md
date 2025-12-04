# Evaluator 修正タスクリスト

- [x] FR-008 対応: TOML で重みが省略された場合に各メトリクスへ均等重み付けを自動適用するロジックを `EvaluationConfig`／`Evaluator` に追加し、`MetricConfig.weight` の必須制約を見直す。
- [x] FR-010 対応: `EvaluationConfig.max_retries` を各メトリクス評価に反映させ、`evaluate_with_llm` 呼び出しでリトライ回数が設定値を使用するよう統一する。
- [x] EvaluationConfig スキーマ整備: 親仕様 (`specs/001-specs/spec.md`) と当該仕様 (`specs/006-evaluator/spec.md`) のエンティティ定義に完全準拠させる。具体的には以下を満たす。
    - TOML から `metric_weights`（メトリクス名→重みの辞書）、`enabled_metrics`（実行対象メトリクスのリスト）、`custom_metrics`（Python 実装とのマッピング情報）の 3 欄を読み取り、Pydantic モデルに保持する。
    - `metric_weights` と `enabled_metrics` の相互整合性（enabled に指定されたメトリクスにのみ重みが存在する、かつ合計 1.0）をバリデーションで保証する。
    - 既存の `metric` 配列を仕様に沿った構造へリファクタし、`Evaluator` がこれら新フィールドを用いてメトリクスの有効化・重み付け・カスタム実装呼び出しを行えるようロジックを再構成する。
- [x] カスタムメトリクス連携: `custom_metrics` 設定値を解釈してカスタム評価関数を登録・実行できるようにし、FR-007 のユースケースを満たす。
