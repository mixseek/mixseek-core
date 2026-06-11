# 横断課題のリファクタリング計画（X1〜X4）

サブシステム単位ではなくリポジトリ全体に薄く広がる課題。いずれも個別には小粒だが、
規約（AGENTS.md）との乖離や将来の保守コストに直結する。

---

## X1: `framework/integration_hooks.py`（576行）のデッドコード削除

- **対象**: `src/mixseek/framework/`（`integration_hooks.py` 576行）、
  `agents/member/factory.py:16,152`、`tests/unit/test_integration_hooks.py`
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: 責務・デッドコード）

イベントフック基盤（8種のイベント型、Logging/Metrics/Webhook/Custom の4フック実装、
非同期キュー処理の `IntegrationManager`、emit 関数12個、setup 関数4個）を持つが、
**本番コードからの呼び出しは `factory.py` の `emit_agent_created_event` 1箇所のみ**。
Webhook フックに至っては登録手段が setup 関数経由でしか存在せず、その setup 関数を
呼ぶコードがない。576行＋テスト一式が、実質1イベントのデバッグログ相当の機能を支えている。

### 推奨アプローチ

プロダクト判断を1つ挟む（拡張ポイントとして外部公開する計画があるか）:

- **計画がない場合（推奨）**: モジュールごと削除。`factory.py` の emit は
  `logger.debug` 1行で置換。テスト `test_integration_hooks.py` も削除。
  約700行（テスト込み）の純減で、observability 系（logfire）と役割が紛らわしい
  「もう1つのイベント機構」が消える。
- **計画がある場合**: 最低限、未使用の Webhook/Custom フックと setup 関数群を落として
  Logging/Metrics のみに縮小し、orchestrator/round_controller の主要イベント
  （round 完了・評価完了など）を実際に emit するところまで実装して「使われる機構」にする。
  中途半端な現状維持が最悪手。

### 関連テスト（安全網）

削除対象自身のテストのみが依存。他テストへの影響なし（grep で確認済み）。

---

## X2: `os.getenv` / `os.environ` 直接呼び出しの集約

- **対象**: 約20ファイル（主要: `core/auth.py` 13箇所、`cli/utils.py`・`cli/commands/ui.py`、
  `ui/app.py`・`ui/services/execution_service.py`・`ui/utils/db_utils.py`、
  `prompt_builder/formatters.py`、`utils/env.py`）
- **影響度: 中 / リスク: 中 / 工数: M**

### 問題（分析観点: 自己ルール違反）

AGENTS.md は「直接 `os.getenv` せず、共通設定モジュールを介して型安全にアクセス」と定める。
準拠しているのは `config/logging.py`・`config/logfire.py`・`config/env_mappers.py`・
`config/schema.py`（pydantic-settings 経由）など config パッケージ内のみで、
それ以外に直接参照が残る。特に:

1. **`core/auth.py`**: `GOOGLE_API_KEY`/`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GROK_API_KEY`/
   `GOOGLE_APPLICATION_CREDENTIALS` を13箇所で直接参照。さらに provider 別
   `validate_*_credentials` 3関数（auth.py:252-342）は「環境変数名・プレフィックス・
   ヒント文言」だけが異なる完全同型
2. **UI/CLI の logfire 系**: [05](05-ui-cli-observability.md) U2 で扱う3重複
3. `prompt_builder/formatters.py:39` の `TZ` 参照、`ui/utils/db_utils.py` の
   `MIXSEEK_WORKSPACE` 参照（`utils/env.py` に同等関数があるのに独自実装）

### 推奨アプローチ

1. **auth 系**: `config/credentials.py`（仮）に provider レジストリを定義する:

   ```python
   PROVIDER_SPECS = {
       AuthProvider.ANTHROPIC: ProviderSpec(env_var="ANTHROPIC_API_KEY", prefixes=("sk-ant-",), hint="..."),
       AuthProvider.OPENAI: ProviderSpec(env_var="OPENAI_API_KEY", prefixes=("sk-", "sk-proj-"), hint="..."),
       AuthProvider.GROK: ProviderSpec(env_var="GROK_API_KEY", prefixes=("xai-",), hint="..."),
   }
   ```

   `validate_*_credentials` 3関数は `validate_api_key(provider)` 1つに畳まれ、
   環境変数アクセスはレジストリ内に集約される。`get_auth_info`（75行）の provider 分岐も
   同レジストリ参照で縮む。`core/auth.py` 570行 → 350行前後を見込む
2. **workspace 系**: `MIXSEEK_WORKSPACE` の読み取りを `utils/env.py:get_workspace_path` に
   一本化し、`db_utils.py`・`env_mappers.py` の独自参照を委譲に変える
3. **logfire/logging 系**: U2 に委譲（本候補のスコープ外とし、二重作業を避ける）
4. ruff の `flake8-tidy-imports` banned-api 等で `os.getenv` を config パッケージ外で
   禁止するリント設定を追加し、再発を機械的に防ぐ（段階導入: まず警告、移行完了後にエラー）

### 関連テスト（安全網）

`tests/unit/test_auth.py` が provider 検出・検証を被覆。レジストリ化は
パラメタライズドテストへの書き換えと相性がよい。`monkeypatch.setenv` を使う既存テストは
環境変数名が変わらない限り無修正で通る。

---

## X3: 例外階層の統一（共通基底 `MixseekError` の導入）

- **対象**: `src/mixseek/exceptions.py`（62行）、`evaluator/exceptions.py`（107行）、
  `round_controller/exceptions.py`、`workflow/exceptions.py`、
  `storage/aggregation_store.py:41-46`（インライン定義）、`core/auth.py:42-51`
- **影響度: 中 / リスク: 低 / 工数: S**

### 問題（分析観点: エラー処理・型の一貫性）

例外が5箇所に分散し、共通基底がない。継承元もまちまち
（`WorkspacePathNotSpecifiedError(ValueError)`・`AuthenticationError(Exception)`・
`DatabaseWriteError(Exception)` 等）。このため「mixseek 起因の失敗をまとめて捕捉する」
ことができず、orchestrator の部分失敗処理や CLI の `exit_with_error` が
`except Exception` に頼る一因になっている。

### 推奨アプローチ

1. `exceptions.py` に `class MixseekError(Exception)` を定義し、サブシステム別例外は
   各モジュールに置いたまま基底だけ差し替える（`ValueError` 互換が必要なものは
   `class XxxError(MixseekError, ValueError)` の多重継承で互換維持）
2. `aggregation_store.py` のインライン2例外は `storage/exceptions.py` へ移動
   （S1/S2 と同時実施が効率的）
3. CLI / orchestrator のハンドリングを `except MixseekError`（想定内・整形して表示）と
   `except Exception`（想定外・スタックトレース付き）の2段に整理する

### 関連テスト（安全網）

例外型を `pytest.raises` で固定しているテストが多数あるため、**型の置換ではなく
基底の追加**に徹すれば既存テストは全て通る。ハンドリング2段化のみ CLI テストで確認。

---

## X4: Pydantic v1 残滓と軽微なモダナイズ

- **対象**: `ui/models/config.py:40,155`・`ui/models/execution.py:55,91`・
  `ui/models/history.py:37`
- **影響度: 低 / リスク: 低 / 工数: S**

### 問題（分析観点: 古いパターン）

UI モデル5箇所が pydantic v1 スタイルの `class Config:` を使用（v2 では非推奨、
将来バージョンで削除予定）。リポジトリの他の全モデルは `model_config = ConfigDict(...)` /
`SettingsConfigDict` に統一済みで、ここだけ取り残されている。

なお全体としてのモダナイズ状況は良好（`Optional[...]`/`Union[...]` は実質0、
`X | None` 記法に統一済み、`.dict()`/`parse_obj` 等の v1 API もなし）。
Python 3.13 固有の簡潔化（PEP 695 type 文など）は採用してもよいが、効果が小さいため
本計画では候補に挙げない。

### 推奨アプローチ

5箇所を `model_config = ConfigDict(...)` へ機械的に置換。あわせて ruff の
pydantic 系ルール（または pre-commit での grep チェック）で再発防止する。
30分仕事のため、UI を触る最初の PR（U1 等）に同梱してよい。

### 関連テスト（安全網）

`tests/ui/` のモデル利用テストで十分。挙動変更なし。
