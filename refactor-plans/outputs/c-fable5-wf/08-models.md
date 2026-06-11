# リファクタリング計画: models サブシステム

## 概要（責務と依存の現状）

`src/mixseek/models/` は Pydantic ベースのデータモデル層（計9ファイル・2,150行、wc -l 実測）。

| ファイル | 行数 | 主な内容 |
| --- | ---: | --- |
| evaluation_config.py | 875 | MetricConfig / LLMDefaultConfig / EvaluationConfig / 新旧変換関数 |
| member_agent.py | 487 | MemberAgentResult / Tool設定3種 / PluginMetadata / MemberAgentConfig / EnvironmentConfig |
| leader_agent.py | 222 | MemberSubmission / MemberSubmissionsRecord |
| evaluation_result.py | 194 | MetricScore / EvaluationResult |
| evaluation_request.py | 163 | EvaluationRequest |
| workspace.py | 116 | WorkspacePath / WorkspaceStructure |
| result.py | 56 | InitResult（CLI結果） |
| leaderboard.py | 31 | LeaderBoardEntry |
| __init__.py | 6 | InitResult / Workspace系のみ re-export |

依存の特徴（本来「最下層」であるべき models 層からの逆向き依存が複数ある）:

- `evaluation_config.py:8-9` が `config.schema.EvaluatorSettings` を TYPE_CHECKING import、
  `from_toml_file()`（540行目）が `config.manager.ConfigurationManager` を遅延 import → **models → config の逆依存**
- `result.py:5` が `import typer` → **モデルが CLI ライブラリに依存**（`print_result()` で表示まで担当）
- `workspace.py` は `utils.filesystem` / `exceptions` に依存し、バリデータ内で `os.access`・
  ディスク容量チェック等の I/O を実行（モデルと I/O 検証の責務混在）
- 利用側: evaluator / round_controller / config(member_agent_loader, schema) / cli / agents が広く参照

## 評価サマリ（観点1〜5）

### 観点1: 責務と依存
- 評価設定のスキーマが**二重定義**されている。`config/schema.py:647` の `EvaluatorSettings`（新）と
  `models/evaluation_config.py` の `EvaluationConfig`（旧）が同じ evaluator.toml を表現し、
  `evaluator_settings_to_evaluation_config()`（823-875行）が「後方互換性」目的で常時変換している。
  Evaluator は `evaluator.py:96-97` で settings を受け取った直後に旧形式へ変換しており、新旧が恒久併存。
- 同様に `MemberAgentConfig`（models）と `MemberAgentSettings`（config/schema.py:477）も二重定義で、
  `config/member_agent_loader.py:67` の `member_settings_to_config()` が変換層を担う。
- `EnvironmentConfig`（member_agent.py:435-487, BaseSettings + env_prefix="MIXSEEK_"）は
  環境変数読み込みであり、models ではなく config サブシステムの責務。

### 観点2: 設計上の臭い
- **コピペ重複（DRY違反）**: `MetricConfig`（73-157行）と `LLMDefaultConfig`（272-336行）は
  model/temperature/max_tokens/max_retries/timeout_seconds/stop_sequences/top_p/seed/
  model_settings/google_model_settings の10フィールドと `validate_model_format`（167-187行 vs
  338-357行、本文ほぼ同一）を重複定義している。
- **メソッドのコピペ増殖**: `get_model_for_metric` 〜 `get_google_model_settings_for_metric` の
  計11メソッド（578-796行、約220行）が「metric側 → llm_default フォールバック」の同一ロジックの繰り返し。
  呼び出し元は `evaluator/evaluator.py:177-187` の1箇所のみで、フィールド追加のたびに3箇所
  （MetricConfig / LLMDefaultConfig / getter）の修正が必要な構造。
- **順序依存の脆いバリデータ**: `member_agent.py:337-352` の `validate_model` は
  「'type' フィールドが 'model' より先に定義されていること」に依存（docstring 自身が警告）。
  プロバイダ接頭辞のホワイトリストは `core/auth.py:66` 付近の分岐とも重複。
- leader_agent.py の `successful_submissions` / `failed_submissions`（130-137行）は
  `all_submissions` から導出可能なデータをフィールドとして二重保持（computed_field 化で簡潔化可能）。

### 観点3: AGENTS.md 自己ルール違反
- **300行超**: evaluation_config.py（875行）、member_agent.py（487行）の2ファイルが違反。
  ただし evaluation_config.py は docstring が過半を占め、実コードは推定350行程度。
- `os.getenv` 直接呼び出し: なし（workspace.py の `os.access` は許容範囲）。
- ロガー/構造化ログ: models 層はログ出力を持たないため違反なし（妥当）。
- コメント言語: member_agent.py / workspace.py / result.py / leaderboard.py は docstring が英語で、
  「共通語は日本語」の方針と不整合（他ファイルは日本語）。

### 観点4: エラー処理・型
- 型注釈はほぼ網羅されており mypy + pydantic plugin 前提として良好。ただし
  `evaluation_config.py:486,497` に `# type: ignore` が残る（weight が None でないことを
  バリデータ通過後も型で表現できていない）。
- 例外は ValueError 中心で一貫しているが、workspace.py は `ParentDirectoryNotFoundError` /
  `WorkspacePermissionError`（独自例外）と ValueError / OSError が混在。
- `MemberAgentResult.error()` が `content=""` を必須フィールドに詰める設計はやや不自然だが許容範囲。

### 観点5: テスト被覆
安全網は厚い。担当範囲の主な対応テスト（wc -l 実測）:

- `tests/evaluator/unit/test_evaluation_config.py`（438行）… from_toml_file 含む
- `tests/unit/config/test_evaluation_settings.py` … 新旧変換の移行検証専用テストあり
- `tests/evaluator/unit/test_evaluation_request.py`（344行）/ `test_evaluation_result.py`（277行）
- `tests/unit/test_member_agent_config.py`（380行）/ `test_member_agent_result.py`（165行）
- `tests/unit/models/test_leader_agent.py`（181行）
- workspace.py / result.py / leaderboard.py は直接の単体テストが薄く、CLI・storage 経由の間接被覆が中心

## リファクタリング候補

### 候補1: 評価設定スキーマの一本化（EvaluationConfig と EvaluatorSettings の統合）
- **対象**: `src/mixseek/models/evaluation_config.py`、`src/mixseek/config/schema.py`(EvaluatorSettings)、
  `src/mixseek/evaluator/evaluator.py`
- **問題**（観点1・2）: 同一 TOML を表す新旧スキーマが併存し、`evaluator_settings_to_evaluation_config()`
  による恒久的な変換層が残存。models → config の逆依存（schema TYPE_CHECKING import、
  from_toml_file 内の ConfigurationManager 遅延 import）も発生。`from_toml_file()` の呼び出しは
  src 内ゼロ（テストのみ）で、後方互換 API の役割をほぼ終えている。
- **影響度**: 高 / **リスク**: 中
- **推奨アプローチ**: (1) Evaluator 内部のメトリクス設定解決を EvaluatorSettings 直結に書き換え、
  (2) `from_toml_file()` と変換関数を deprecate → 削除、(3) MetricConfig 等の純粋モデルだけを
  models 側に残し読み込みロジックは config 層へ寄せる。段階的に PR を分割する。
- **関連テスト**: test_evaluation_config.py（438行）、test_evaluation_settings.py の移行検証、
  tests/evaluator/integration・e2e。安全網は十分。
- **工数感**: L

### 候補2: get_*_for_metric 11メソッドの統合
- **対象**: `src/mixseek/models/evaluation_config.py:558-796`、`src/mixseek/evaluator/evaluator.py:177-187`
- **問題**（観点2）: 同一フォールバックロジックのコピペが11個（約220行）。利用箇所は evaluator.py の
  1箇所のみ。フィールド追加のたびに3箇所修正が必要。
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**: メトリクス名から「解決済み LLM 設定」をまとめて返す
  `resolve_llm_settings(metric_name) -> ResolvedMetricSettings`（frozen モデル）1メソッドに集約し、
  共通フィールドの merge は `model_dump(exclude_none=True)` ベースで汎用化する。
- **関連テスト**: test_evaluation_config.py にフォールバック検証あり。evaluator 側 unit テストも併用。
- **工数感**: S

### 候補3: MetricConfig / LLMDefaultConfig の共通基底クラス化
- **対象**: `src/mixseek/models/evaluation_config.py:12-374`
- **問題**（観点2・3）: 10フィールド＋ `validate_model_format` バリデータの完全重複（DRY違反）。
  875行（300行制限違反）の主因の一つ（重複定義＋過剰な docstring）。
- **影響度**: 中 / **リスク**: 低
- **推奨アプローチ**: 共通 `LLMParamsBase(BaseModel)` を切り出し両者が継承。モデル形式検証も
  共通関数化（evaluator/llm_client.py:80-92 の同種チェックとも将来統合）。冗長な Example/説明
  docstring は Sphinx ドキュメント側へ移し、ファイルを300行以内へ。候補1と同一PR系列で実施可。
- **関連テスト**: test_evaluation_config.py のバリデーションテスト群がそのまま回帰検証になる。
- **工数感**: S

### 候補4: member_agent.py の責務分割と EnvironmentConfig の config 層移設
- **対象**: `src/mixseek/models/member_agent.py`（487行）、`src/mixseek/config/member_agent_loader.py`
- **問題**（観点1・2・3）: 1ファイルに Result 型・Tool 設定3種・PluginMetadata・MemberAgentConfig・
  EnvironmentConfig（BaseSettings）の5責務が同居し300行制限違反。EnvironmentConfig は環境変数
  読み込みで config サブシステムの責務。`validate_model`（337-387行）はフィールド定義順に依存する
  脆い実装で、プロバイダ接頭辞リストがハードコード（core/auth.py の分岐と重複）。
- **影響度**: 中 / **リスク**: 中（import 元が agents/cli/config/framework 等12ファイルと広い）
- **推奨アプローチ**: `models/member/`（result.py / tool_config.py / agent_config.py）へ分割し、
  既存パスから re-export して互換維持。EnvironmentConfig は config 層へ移設。validate_model は
  `model_validator(mode="after")` 化して順序依存を解消し、接頭辞リストを定数として一元化する。
- **関連テスト**: test_member_agent_config.py（380行）、test_member_agent_result.py（165行）、
  tests/unit/test_*_agent.py 群。被覆は厚い。
- **工数感**: M

### 候補5: result.py の typer 依存除去（表示ロジックの CLI 層移動）
- **対象**: `src/mixseek/models/result.py`（InitResult.print_result, 49-56行）
- **問題**（観点1）: データモデルが `import typer` し標準出力まで担当しており、models → CLI の
  レイヤ違反。モデル層の依存を pydantic のみに保てない。
- **影響度**: 低 / **リスク**: 低
- **推奨アプローチ**: `print_result()` を `cli/` 側のフォーマッタ関数へ移動し、InitResult は純粋な
  データ保持に限定する。あわせて `models/__init__.py` の re-export 方針（現状 InitResult/Workspace
  のみで不統一）を整理する。
- **関連テスト**: tests/unit/cli/test_exec_dry_run.py 等の CLI テストで間接被覆。移動先で
  フォーマッタの単体テストを追加する。
- **工数感**: S
