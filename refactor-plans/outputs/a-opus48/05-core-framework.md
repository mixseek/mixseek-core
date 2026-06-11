# 05. core / framework / オーケストレーション中核

## R8 — `core/auth.py` をプロバイダ別に分割

- **対象**: `src/mixseek/core/auth.py`（570行）
- **問題**（肥大化 / DRY違反 / 規約違反）:
  - 1ファイルにプロバイダ別の検証・生成が並ぶ：`validate_google_ai_credentials` /
    `validate_vertex_ai_credentials` / `validate_anthropic_credentials` /
    `validate_openai_credentials` / `validate_grok_credentials`、`_create_google_model_cached`、
    `create_authenticated_model`、`get_auth_info`、`detect_auth_provider`、`clear_auth_caches`。
  - 各 `validate_*_credentials` は「対応する `os.getenv(...)` を読む→無ければ例外」という
    同型処理の繰り返し（115・146・258・289・320行など）。`get_auth_info` 内（450〜487行）でも
    同じ env キーを再度直読みしており、認証情報のキー定義が散在＝DRY違反。
  - `os.getenv` 直呼びが多数（R14 対象。ただし秘密情報の取得は config モジュール経由に寄せるべき箇所）。
- **影響度**: 中（全モデル生成の入口。agents/evaluator が依存。auth参照テスト10ファイル）
- **リスク**: 中（資格情報・キャッシュ周りは壊すと実行時にしか出ない。テストで保護）
- **推奨アプローチ**:
  - `core/auth/`（パッケージ化）：`providers/google.py`・`anthropic.py`・`openai.py`・`grok.py` に
    検証＋生成を分離し、共通の「env キー定義 → 検証 → 例外」ロジックを
    `providers/base.py` のプロバイダ記述（必要な env キー一覧）＋汎用バリデータに集約。
  - `detect_auth_provider` / `create_authenticated_model` はディスパッチャとして残す
    （プロバイダ表を引く形に）。env キーの定義を1箇所へ寄せ、`get_auth_info` の重複読取を解消。
- **関連テスト**: `tests/agents/`・auth参照10ファイル。
- **工数**: M

## R9 — `framework/integration_hooks.py` の分割とグローバル singleton 解消

- **対象**: `src/mixseek/framework/integration_hooks.py`（576行）
- **問題**（肥大化 / 古いパターン / テスト網の薄さ）:
  - 1ファイルにイベント定義（`IntegrationEventType`・`IntegrationEvent`）、フック基底＋4実装
    （`Logging` / `Metrics` / `Webhook` / `Custom`）、`IntegrationManager`、
    そして多数のモジュール関数（`get_integration_manager`・`setup_basic_logging_integration`・
    `setup_metrics_collection`・`setup_webhook_integration`・`setup_custom_integration`・
    `emit_agent_created_event` ほか）が同居。
  - `get_integration_manager()` が **モジュールグローバル `_integration_manager` の遅延 singleton**
    （400〜406行）で、テスト時の状態リークやDI困難の原因になりやすい古いパターン。
  - integration_hooks 参照テストは1ファイルと薄い。
- **影響度**: 低（拡張ポイント。中核フローへの結合は限定的）
- **リスク**: 低（利用箇所が少なく独立して整理できる）
- **推奨アプローチ**:
  - `framework/integration/`：`events.py`（型定義）、`hooks.py`（基底＋各実装）、
    `manager.py`（`IntegrationManager`）、`setup.py`（`setup_*` ヘルパー）に分割。
  - グローバル singleton は、明示的な `IntegrationManager` 注入か、アプリ起動時に1度組み立てる
    コンテナへ寄せる。最低限 `clear`/`reset` をテスト用に用意。
  - **テストが薄い**ため、分割前にイベント発火・各フックの基本動作テストを補強。
- **関連テスト**: `tests/`（integration_hooks参照1ファイル）→ 補強推奨。
- **工数**: M

## R10 — `round_controller/controller.py` の長大メソッド抽出

- **対象**: `src/mixseek/round_controller/controller.py`（567行・`RoundController`）
- **問題**（肥大化 / 関数長違反）:
  - `_execute_single_round`（281〜420行＝約140行）、`_should_continue_round`（420〜513行＝約90行）、
    `_finalize_and_return_best`（513行〜）など、1メソッドが長くラウンドのライフサイクル
    （プロンプト整形→単一ラウンド実行→継続判定→最良結果確定）が密に詰まっている。
- **影響度**: 中（ラウンド進行の中核。controller参照テスト15ファイル）
- **リスク**: 中（実行フローの順序依存。ただしテスト網は厚め）
- **推奨アプローチ**:
  - `_execute_single_round` を「メンバー実行」「集約」「評価」「永続化（progress file 書き込み）」の
    private ステップに分解し、各200行以内に。`_write_progress_file` 等の I/O は協調オブジェクトへ寄せる余地。
  - 継続判定（`_should_continue_round`）はポリシーオブジェクトに切り出すと orchestrator との
    重複（後述）も見やすくなる。
- **関連テスト**: `tests/unit/round_controller/`（controller参照15ファイル）。
- **工数**: M

## R11 — `orchestrator/orchestrator.py` の長大メソッド抽出

- **対象**: `src/mixseek/orchestrator/orchestrator.py`（530行・`Orchestrator`）
- **問題**（肥大化 / 関数長違反）:
  - `_execute_impl`（177〜381行＝約200行）が肥大。`execute`・`_try_recover_partial_failure`・
    `_run_team`・`_write_error_to_progress_file` と並び、複数チームの並列起動・部分失敗回復・
    進捗ファイル書込が1メソッドに凝縮。
  - `_write_error_to_progress_file`（orchestrator）と controller 側の `_write_progress_file` で
    progress ファイル書込ロジックが分散しており、共通化の余地（DRY）。
- **影響度**: 中（複数チーム実行の中枢。orchestrator参照テスト33ファイル＝厚い）
- **リスク**: 中（並列実行・例外回復はタイミング依存だが、テスト網が最も厚い領域の一つ）
- **推奨アプローチ**:
  - `_execute_impl` をフェーズ単位（設定ロード→チーム構築→並列実行→集計/回復）に private 抽出し200行以内に。
  - progress ファイル書込を `storage` か専用モジュールへ集約し、orchestrator/controller の重複を統一。
- **関連テスト**: `tests/unit/orchestrator/`・`tests/integration/`（orchestrator参照33ファイル）。
- **工数**: M

## 補足：`core/model_settings.py`

- `model_settings.py`（107行・`build_model_settings` 単一関数）は小さく当面問題なし。
  R6（設定モデル統合）で `model_settings` フィールドの扱いを整理する際に併せて確認するとよい。
