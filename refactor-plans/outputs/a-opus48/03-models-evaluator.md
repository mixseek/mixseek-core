# 03. models / evaluator：設定モデルの新旧二重化

## R6 — 設定モデルの新旧二系統を統合（最重要・最高リスク）

- **対象**:
  - `src/mixseek/models/evaluation_config.py`（875行・`MetricConfig` / `LLMDefaultConfig` /
    `EvaluationConfig` ＋ 移行ブリッジ `evaluator_settings_to_evaluation_config`）
  - `src/mixseek/config/schema.py` の `EvaluatorSettings`（pydantic-settings 側の同等定義）
- **問題**（DRY違反 / 密結合 / 古いパターン）:
  - 同じ「Evaluator の設定」を **2つの型階層で二重に表現**している：
    - 「新」：`EvaluatorSettings`（`BaseSettings`、TOML/env から読む設定入口）
    - 「旧」：`EvaluationConfig` / `LLMDefaultConfig`（`BaseModel`、Evaluator 実行時 API が要求する形）
  - 両者を `evaluator_settings_to_evaluation_config()` が橋渡しし、`temperature`・`max_tokens`・
    `max_retries`・`timeout_seconds`・`stop_sequences`・`top_p`・`seed`・`model_settings`・
    `google_model_settings` といった**フィールド定義・バリデーションが二重管理**になっている。
  - ブリッジ関数の docstring 自体が「（新）を（旧）に変換」「既存APIとの互換性のため」と
    明言しており、**過渡期の負債が固定化**している状態。フィールドを足すたびに両方を触る必要があり、
    ズレ（デフォルト値・検証規則の不一致）の温床。
- **影響度**: 高（evaluator は40テストファイルが参照する中核機能。設定追加のたびに二重作業）
- **リスク**: **高**（公開 API（`EvaluationConfig`）に依存するコードが多く、統合は外部契約に波及。
  慎重な段階移行が必須）
- **推奨アプローチ**（段階的に、安全網を確認しながら）:
  1. まず両モデルのフィールド対応表を作り、**差分（デフォルト・検証規則の食い違い）を洗い出す**。
  2. 単一の信頼できる型（SSOT）を決める。現実的には **`EvaluatorSettings` を入口に保ちつつ、
     `LLMDefaultConfig` 相当を `EvaluatorSettings` から導出するプロパティ/メソッド**に寄せ、
     `EvaluationConfig` は「実行時ビュー」として薄く保つ（または逆向きに統一）。
  3. ブリッジ関数は残しつつ内部実装を「フィールドの素直な写像」に縮小し、**重複バリデーションを
     どちらか一方に集約**（`validate_model_format` など共通バリデータの一本化）。
  4. 最終的に二重定義を解消するか、少なくとも「片方が他方から自動生成される」関係に整理。
  5. `Evaluator.evaluate` / `_get_metric` / `_calculate_overall_score` など利用箇所の型を段階移行。
- **関連テスト**: `tests/evaluator/`（unit/integration/e2e/performance）＋ `tests/unit/models/`。
  evaluator参照40・evaluation_config参照6ファイル。統合は**契約テスト（`tests/contract`）の
  整備状況を確認してから**着手するのが安全。
- **工数**: L（設計合意＋段階移行で最大級）

## R12 — `models/member_agent.py` の責務分離

- **対象**: `src/mixseek/models/member_agent.py`（487行）
- **問題**（肥大化 / 責務混在）:
  - 1ファイルに `AgentType`・`ResultStatus`・`MemberAgentResult`・各種ツール設定
    （`WebSearchToolConfig`・`WebFetchToolConfig`・`CodeExecutionToolConfig`・`ToolSettings`）・
    `PluginMetadata`・`MemberAgentConfig`、さらに **`EnvironmentConfig(BaseSettings)`** が同居。
  - 「データモデル（BaseModel）」と「環境設定（BaseSettings）」という性質の違うものが混在。
    300行超ルール違反。
- **影響度**: 低〜中（member_agent はテスト35ファイルが参照する中核モデルだが、変更は import 整理が中心）
- **リスク**: 低（純粋なモデル分割。再エクスポートで互換維持可能）
- **推奨アプローチ**:
  - `models/member_agent/`（パッケージ化）へ：`result.py`（結果・enum）、`tools.py`
    （各ツール設定＋`ToolSettings`）、`config.py`（`MemberAgentConfig`・`PluginMetadata`）、
    `environment.py`（`EnvironmentConfig`）に分割。
  - `__init__.py` で従来 import を再エクスポート。
- **関連テスト**: `tests/unit/models/`・`tests/agents/`（member_agent参照35ファイル）＝厚い安全網。
- **工数**: S

## 補足：`models/` のその他

- `evaluation_result.py`（194行）・`evaluation_request.py`（163行）・`leader_agent.py`（222行）は
  300行未満で当面問題なし。R6 統合時に `LLMDefaultConfig` 周りと併せて見直すと整合が取りやすい。
