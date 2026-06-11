# リファクタリング計画: framework / core サブシステム

## 概要（責務と依存の現状）

担当範囲は `src/mixseek/framework/`（1ファイル）と `src/mixseek/core/`（2ファイル）。行数は wc -l 実測値。

| ファイル | 行数 | 責務 |
|---|---|---|
| `framework/integration_hooks.py` | 576 | エージェントライフサイクルのイベント発行・フック配信基盤 |
| `core/auth.py` | 570 | モデルID→プロバイダ判定、認証情報検証、pydantic-ai モデル生成、HTTPクライアント管理 |
| `core/model_settings.py` | 107 | TOML pass-through dict と個別フィールドを合成し ModelSettings を構築 |

依存関係:

- `core/auth.py` は `pydantic_ai` と `httpx` に依存し、`mixseek` 内部には依存しない（最下層モジュール）。
  利用側は広く、`agents/member/*`（plain/web_search/web_fetch/code_execution）、`agents/leader/agent.py`、
  `evaluator/llm_client.py`、`round_controller/judgment_client.py`、`cli/commands/*`（`close_all_auth_clients`）、
  `ui/services/execution_service.py`（`clear_auth_caches`）、`orchestrator/orchestrator.py`（`get_auth_info`）、
  `config/preflight/validators/auth.py` から参照される事実上のコアインフラ。
- `core/model_settings.py` は `core/auth.py` の `detect_auth_provider` に依存。利用側は
  `agents/member/base.py`、`agents/leader/agent.py`、`evaluator/llm_client.py`、`round_controller/judgment_client.py`。
- `framework/integration_hooks.py` は `models/member_agent` のみに依存。**本番コードからの利用は
  `agents/member/factory.py:16,152` の `emit_agent_created_event` 1箇所のみ**で、公開 API の大半が未使用。

なお `core/` と `framework/` には `__init__.py` が存在しない（他パッケージ `config`/`utils`/`observability` には
ある）。暗黙の名前空間パッケージとなっており、パッケージ構成の一貫性として軽微な不整合。

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存

- `auth.py` が「プロバイダ判定」「認証情報検証」「モデル生成」「HTTPクライアントのキャッシュ／クローズ管理」
  という4責務を1ファイルに抱える。特にライフサイクル管理（`_managed_http_clients`、
  `close_all_auth_clients`、`clear_auth_caches`）は認証検証とは独立した関心事。
- `integration_hooks.py` も「イベント型定義」「4種のフック実装」「キュー処理マネージャ」「8本の emit
  ヘルパ」「4本の setup ヘルパ」を1ファイルに同居させている。
- `model_settings.py` は責務が単一で健全。リファクタ不要。

### 観点2: 設計上の臭い

- **DRY違反（auth.py）**: `validate_google_ai_credentials`（109-137行）/ `validate_anthropic_credentials`
  （252-280行）/ `validate_openai_credentials`（283-311行）/ `validate_grok_credentials`（314-342行）は
  「envvar 取得→未設定→空→形式チェック」の同一構造。さらに `create_authenticated_model`（345-426行）と
  `get_auth_info`（429-503行）が同じプロバイダ分岐 if/elif を二重に持ち、プロバイダ知識（prefix・環境変数名・
  キー形式）が3箇所以上に分散している。
- **DRY違反（integration_hooks.py）**: `emit_*` 8関数（408-523行）はイベント構築＋emit の同型コードの繰り返し。
  `MetricsIntegrationHook.reset_metrics`（162-174行）は `__init__`（111-120行）の初期 dict を丸ごと複製。
- **デッドコード/YAGNI**: `emit_agent_initialized_event` 以下7本の emit 関数、`setup_*` 4関数、
  `WebhookIntegrationHook`、`CustomIntegrationHook` は src 配下で未使用（テストからのみ参照）。
  `pyproject.toml:66` の `aiohttp>=3.13.0` は「WebhookIntegrationHook 用」とコメントされており、
  未使用機能のためだけに依存が増えている。HTTP クライアントもプロジェクト標準の httpx と不統一
  （`integration_hooks.py:193` で `import aiohttp` をインライン import）。
- **グローバル可変状態**: `integration_hooks.py:397` の `_integration_manager` シングルトンと
  `auth.py:27` の `_managed_http_clients` リスト。`_ensure_queue`（271-312行）はイベントループ切替を
  検知して内部状態を作り直す防御的コードで、Streamlit 等でのループ再生成問題への対症療法になっている
  （`clear_auth_caches` も同根の対症療法。564-570行で pydantic_ai の私有 API
  `_cached_async_http_client` に触れており、バージョンアップで静かに壊れるリスクあり）。
- **隠れた制御フロー**: `auth.py:96-106,366-367` で `PYTEST_CURRENT_TEST` 検出時に無条件で `TestModel`
  を返す。モジュール自身が掲げる「NO implicit fallbacks」方針と矛盾する暗黙フォールバック。

### 観点3: AGENTS.md 自己ルール違反

- **300行制限超過**: `integration_hooks.py` 576行、`auth.py` 570行（いずれも約1.9倍）。
- **`os.getenv` 直接呼び出し**: `auth.py` に12箇所（106, 115, 146, 258, 289, 320, 407, 450, 459, 469,
  478, 487行）。規約では共通 config モジュール経由が必須。`config/env_mappers.py` 等の既存機構があるのに
  迂回している。
- **構造化JSONログ**: ロガー名は `__name__` ベースで `mixseek.*` 階層に乗るため共通ロガー
  （`observability/logging_setup.py` の JsonFormatter）には流れるが、`LoggingIntegrationHook.handle_event`
  （85-99行）はメッセージ文字列に metadata を連結しており `extra` フィールド化されていない。
  `auth.py` はロガー自体を持たず、認証失敗等のログが一切出ない。
- 関数200行超過は両ファイルとも該当なし（最長は `create_authenticated_model` の約82行）。

### 観点4: エラー処理・型

- `AuthenticationError`（provider + suggestion 付き）は良い設計で一貫している。ただし
  `auth.py:197-208` の `except json.JSONDecodeError` / `except PermissionError` からの再 raise に
  `from e` がなく、原因例外チェーンが切れる。`auth.py:408` は `assert` で None 排除しており、
  `-O` 実行時に消える（検証関数とモデル生成の距離が遠いことが原因。レジストリ化で解消可能）。
- `integration_hooks.py` は `except Exception` で握りつぶしてログのみ（212-213, 250-251, 372-373行）。
  イベント基盤としては妥当だが、`CustomIntegrationHook` の `async_handler` フラグ＋
  `type: ignore[misc]`（247行）は `inspect.iscoroutinefunction` 判定で除去できる古いパターン。
- 型注釈は全体に付与済みだが、`IntegrationEvent.metadata/payload` や `MetricsIntegrationHook.metrics` が
  `dict[str, Any]` で、Python 3.13 なら TypedDict / dataclass で絞れる。

### 観点5: テスト被覆

- `tests/unit/test_auth.py` 547行、`tests/unit/test_integration_hooks.py` 650行、
  `tests/unit/test_model_settings.py` 195行、加えて `tests/integration/test_member_agent_integration.py`。
  ソース行数比でテストが同等以上あり、**安全網は厚い**。分割・レジストリ化は既存テストを公開 API 経由に
  保ったまま進めやすい。ただし候補5（TestModel 暗黙置換）はテスト前提そのものを変えるため別格の注意が必要。

## リファクタリング候補

### 候補1: auth.py のプロバイダ定義レジストリ化とモジュール分割

- **対象**: `src/mixseek/core/auth.py`（570行）
- **問題**: 観点2（validate_* 4関数と if/elif 2連鎖の DRY 違反、プロバイダ知識の分散）、観点3（300行超過）、
  観点4（`assert` による None 排除、`from e` 欠落）
- **影響度**: 高（全エージェント・evaluator・round_controller が依存する最下層。プロバイダ追加コストが激減）
- **リスク**: 中（利用箇所が広いが、公開関数のシグネチャを維持すれば既存テストがそのまま安全網になる）
- **推奨アプローチ**:
  1. `ProviderSpec`（frozen dataclass: prefix / 環境変数名 / キー形式チェック / suggestion / モデル生成関数）を
     定義し、`AuthProvider` ごとのレジストリ dict に集約。
  2. `detect_auth_provider` / `validate_*` / `create_authenticated_model` / `get_auth_info` をレジストリ参照の
     汎用実装に置換（validate_* は後方互換のため薄いラッパとして残す）。
  3. `core/auth/` パッケージ化: `providers.py`（レジストリ）/ `validation.py` / `factory.py` /
     `lifecycle.py`（HTTPクライアント管理）に分割し、`core/auth/__init__.py` で現行 API を再エクスポート。
  4. 再 raise に `from e` を付与し、`assert` をレジストリ経由の検証済み値取得に置換。
- **関連テスト**: `tests/unit/test_auth.py`（547行）、`tests/integration/test_member_agent_integration.py`。十分厚い。
- **工数感**: M

### 候補2: auth.py の os.getenv 直接使用の解消

- **対象**: `src/mixseek/core/auth.py` の12箇所（106, 115, 146, 258, 289, 320, 407, 450, 459, 469, 478, 487行）
- **問題**: 観点3（規約「直接 os.getenv せず共通設定モジュール経由」への明確な違反）
- **影響度**: 中（規約準拠とテスト時の環境変数モック容易化）
- **リスク**: 低（読み取り箇所の置換のみ。挙動変更なし）
- **推奨アプローチ**: 候補1の `ProviderSpec` に環境変数名を持たせ、取得は config サブシステム
  （`config/env_mappers.py` 等の既存機構、なければ薄い `get_secret(name)` アクセサを config に追加）経由に
  一本化する。`PYTEST_CURRENT_TEST` 参照も同アクセサに寄せる。候補1と同一PRで実施するのが効率的。
- **関連テスト**: `tests/unit/test_auth.py` が monkeypatch で環境変数を操作しており回帰検知可能。
- **工数感**: S

### 候補3: integration_hooks.py の未使用機能削減とモジュール分割

- **対象**: `src/mixseek/framework/integration_hooks.py`（576行）、`pyproject.toml:66`（aiohttp）
- **問題**: 観点2（デッドコード: 本番利用は `factory.py:152` の `emit_agent_created_event` のみ。
  emit_* 7本・setup_* 4本・Webhook/Custom フック未使用。aiohttp の依存不統一。emit_* と
  reset_metrics の DRY 違反）、観点3（300行超過、LoggingIntegrationHook の非構造化ログ）
- **影響度**: 中（依存削減・コード量削減・規約準拠。機能追加はない）
- **リスク**: 低（削除対象は src で未参照。対応する単体テストの削除/移設のみ。将来必要なら git 履歴から復元）
- **推奨アプローチ**:
  1. 未使用の emit_* 7本・setup_* 4本・`WebhookIntegrationHook`・`CustomIntegrationHook` を削除し、
     `pyproject.toml` から aiohttp を除去（将来 webhook が必要になれば httpx で再実装）。
  2. 残部を `framework/events.py`（EventType/Event/emit ヘルパ）と `framework/hooks.py`
     （ABC・Logging・Metrics・Manager）に分割、`__init__.py` を追加して公開 API を明示。
  3. emit はイベント構築を1つの汎用ヘルパに集約。`reset_metrics` は初期 dict 生成関数を共有して重複排除。
  4. `LoggingIntegrationHook` は metadata を `extra` で渡し JsonFormatter のフィールドに乗せる。
- **関連テスト**: `tests/unit/test_integration_hooks.py`（650行）。削除分のテストは同時に削除、残存分は import
  パス変更のみで流用可能。
- **工数感**: M

### 候補4: IntegrationManager のシングルトン・イベントループ管理の再設計

- **対象**: `integration_hooks.py` の `IntegrationManager`（260-405行）と `agents/member/factory.py:150-159`
- **問題**: 観点2（グローバル可変シングルトン、`_ensure_queue` 271-312行のイベントループ切替検知という
  対症療法、fire-and-forget タスクで配信保証なし・`stop_processing` を呼ぶ責任者が不在）、
  観点4（`is_processing` フラグとタスク生成の競合余地）
- **影響度**: 中（UI/CLI のループ再生成起因の潜在バグ温床を除去し、テスト容易性を改善）
- **リスク**: 中（emit 経路のタイミング挙動が変わる。候補3でコード量を減らした後に着手すべき）
- **推奨アプローチ**: フック数が少なくハンドラも軽量（ログ・メトリクス）である現状を踏まえ、
  キュー＋常駐タスク方式を廃止して emit 時に interested なフックを直接 `await`（または
  `asyncio.TaskGroup` で並行実行）する同期 dispatch に簡素化する。マネージャはシングルトンをやめ、
  factory 等の利用側へ DI で渡す（互換用に `get_integration_manager()` は残してデフォルト
  インスタンスを返す）。これにより `_ensure_queue` のループ検知コードが丸ごと不要になる。
- **関連テスト**: `tests/unit/test_integration_hooks.py` にマネージャのキュー処理テストあり。dispatch 方式の
  変更に合わせた書き換えが必要（イベントが届くことの検証自体は流用可能）。
- **工数感**: M

### 候補5: TestModel 暗黙置換の明示オプトイン化

- **対象**: `src/mixseek/core/auth.py` の `validate_test_environment`（96-106行）と
  `create_authenticated_model`（365-367行）
- **問題**: 観点2（`PYTEST_CURRENT_TEST` という環境変数による隠れた制御フロー。自モジュールが掲げる
  「NO implicit fallbacks」方針との自己矛盾。pytest 配下では実モデル生成経路・認証検証経路を一切
  通せず、integration テストの表現力を制限）
- **影響度**: 中（テスト設計の健全化。本番挙動への影響はなし）
- **リスク**: 高（多数の既存テストがこの暗黙置換に依存している可能性が高く、一斉移行が必要）
- **推奨アプローチ**: `create_authenticated_model(model_id, *, use_test_model: bool = False)` の明示引数
  または conftest の共通 fixture（`create_authenticated_model` を TestModel 返却にモンキーパッチ）へ移行し、
  環境変数判定を撤廃する。移行は「fixture 追加→既存テストを段階的に切替→環境変数判定削除」の3段階で行い、
  candidates 1〜2 の完了後に着手する。優先度は低め。
- **関連テスト**: ほぼ全 unit/integration テストが間接的に影響。`tests/unit/test_auth.py` に
  `validate_test_environment` の直接テストあり。
- **工数感**: M

### 補足（候補化しなかった事項）

- `core/model_settings.py`（107行）は責務単一・テストあり（195行）で健全。リファクタ不要。
- `core/` と `framework/` への `__init__.py` 追加は候補1・3の分割作業に含めて対応する。
- `clear_auth_caches` の pydantic_ai 私有 API 依存（`auth.py:564-570`）は候補1の `lifecycle.py` 切り出し時に
  バージョン互換テストを追加して監視する。
