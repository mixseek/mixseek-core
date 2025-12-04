# Feature Specification: MixSeek-Core Member Agent バンドル

**Feature Branch**: `009-member`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "specs/001-specs/spec.md に従い、mixseek-coreにバンドルされるMember Agentの仕様を日本語で定義してください
- Pydantic AI(https://ai.pydantic.dev/) の機能を最大限に使う(ローカルドキュメント: draft/references/pydantic-ai-docs)
- Gemini API キーとVertex AIに対応する(GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_APPLICATION_CREDENTIALS=/path_to/gcp_credentials.json)
- 開発・テスト専用のCLIコマンドで動作する -> mixseek member "user prompt" --config agent_name.toml, mixseek member "user prompt" --agent agent_name
- バンドルされるMember Agent(プレーン, Web Search Tool, Code Execution Tool) https://ai.pydantic.dev/builtin-tools/
- システム指示（system_instruction）はTOMLファイルでカスタマイズでき、`system_prompt`が指定された場合はPydantic AIの`system_prompt`として併用される"

**CLI Command Design Decision**: 本機能は `mixseek member` コマンドを採用します。開発・テスト専用の性質は、コマンド名ではなく以下の方法で明確化します：
1. 実行時の警告メッセージ表示（毎回、開発・テスト専用であることを明示）
2. ドキュメントでの明確な用途説明（本番利用は推奨されない旨を記載）
3. 将来的な本番用コマンド（Leader Agentからの呼び出し）との棲み分けをドキュメント化

## Scope

本仕様は、MixSeek-Core Member Agentバンドルの完全な機能セットを定義します。スコープには以下が含まれます：

### In Scope (本仕様でカバー)

1. **標準Member Agent** (3種類のバンドル済みエージェント):
   - `plain`: プレーン推論エージェント
   - `web-search`: Web検索機能付きエージェント
   - `code-exec`: コード実行機能付きエージェント

2. **カスタムMember Agent作成の基本要件**:
   - `BaseMemberAgent` 抽象基底クラスの定義
   - `MemberAgentResult` 応答フォーマットの定義
   - TOML設定スキーマと検証ルール
   - `--config <path>` オプションによるカスタム設定読み込み
   - Pydantic AI統合パターン（モデル接続、ツール登録、エラーハンドリング）

3. **開発・テスト用CLIコマンド**:
   - `mixseek member "prompt" --agent <name>` (標準エージェント実行)
   - `mixseek member "prompt" --config <path>` (カスタムエージェント実行)
   - 警告メッセージ表示とエラーハンドリング

4. **MixSeek-Core Framework統合**:
   - Leader AgentからのPydantic AI Toolset呼び出し対応
   - `execute(task, context)` インターフェース実装
   - `all_messages` 履歴のLeader Agentへの引き渡し

### Out of Scope (子仕様または別ドキュメントで扱う)

1. **カスタムMember Agent開発の詳細ガイド**:
   - ステップバイステップ実装手順
   - カスタムツール作成方法
   - テストの書き方とベストプラクティス
   - パフォーマンスチューニング
   - デバッグ・トラブルシューティング
   - → 子仕様 (`specs/018-custom-member/`) で扱う

2. **本番環境での運用**:
   - Leader Agentによる複数Member Agentオーケストレーション
   - Round Controller統合
   - Evaluator連携
   - → MixSeek-Core Framework仕様 (`specs/001-specs/`) で扱う

3. **UI統合**:
   - Mixseek UI (`specs/014-ui/`) からのエージェント実行
   - → 076-ui仕様で扱う

**子仕様への切り出し方針**: 本仕様は「何を実装するか（What）」を定義し、カスタムエージェント開発者向けの「どう実装するか（How）」は別仕様またはドキュメントで詳述します。

## User Scenarios & Testing

### User Story 1 - 開発・テスト用Member Agent動作検証 (Priority: P1)

開発者は、mixseek-coreにバンドルされたプレーンなMember Agentの動作検証を実行します。エージェントはTOMLファイルで定義された`system_instruction`（Pydantic AIの`instructions`に対応）に従って動作し、Pydantic AIの機能を活用して一貫性のある高品質な応答を返します。本機能は開発・テスト用途に限定され、実行時は必ず警告メッセージを表示します。

**Why this priority**: これは最も基本的なユースケースであり、他の全ての機能の基盤となります。プレーンなエージェントが動作しなければ、より高度な機能も利用できません。

**Independent Test**: 単純なプロンプトを送信し、設定された`system_instruction`に従った適切な応答を受け取ることで完全にテスト可能です。

**Acceptance Scenarios**:

1. **Given** 開発者が `mixseek member "質問" --config custom.toml` コマンドでカスタム設定を指定する、**When** テスト用プロンプトを送信する、**Then** TOMLファイルで設定された`system_instruction`に従って回答を生成し、開発・テスト専用である旨の警告メッセージを表示する
2. **Given** 開発者が `mixseek member "質問" --agent plain` コマンドで標準エージェントを指定する、**When** プロンプトを送信する、**Then** バンドルされた標準エージェント設定に従って回答を生成し、警告メッセージを表示する
3. **Given** 開発者が `--config` と `--agent` を両方指定する、**When** コマンドを実行する、**Then** 相互排他エラーメッセージを表示して終了する
4. **Given** エージェントが動作している、**When** Gemini APIまたはVertex AIを使用する、**Then** 正しくモデルとの通信を行い高品質な応答を返す
5. **Given** ユーザが複数の異なるプロンプトを送信する、**When** システムが処理する、**Then** 一貫した品質とフォーマットで応答を提供する

---

### User Story 2 - Web検索機能付きMember Agentの利用 (Priority: P2)

ユーザは、Web検索機能を有効にしたMember Agentを使用して、リアルタイムの情報が必要な質問や最新データの分析を実行します。エージェントはPydantic AIのWebSearchToolを活用して、最新の情報を取得し、その情報を踏まえた分析結果を返します。

**Why this priority**: Web検索機能は現在の情報を必要とするタスクに不可欠であり、エージェントの実用性を大幅に向上させます。プレーンエージェントの後の優先度です。

**Independent Test**: 最新情報が必要な質問を送信し、Web検索結果に基づく正確で最新の回答を受け取ることで検証可能です。

**Acceptance Scenarios**:

1. **Given** Web検索機能付きエージェントが設定されている、**When** 最新情報が必要な質問を送信する、**Then** 自動的にWeb検索を実行し最新データに基づく回答を提供する
2. **Given** エージェントがWeb検索を実行する、**When** 検索結果を取得する、**Then** 関連性の高い情報を抽出し分析結果に統合する
3. **Given** ユーザが特定の日付や最新の出来事について質問する、**When** システムが処理する、**Then** Web検索で得た最新情報を根拠として明示する

---

### User Story 3 - コード実行機能付きMember Agentの利用 (Priority: P3)

ユーザは、コード実行機能を持つMember Agentを使用して、計算、データ分析、プログラミング問題の解決を実行します。エージェントはPydantic AIのCodeExecutionToolを利用して、安全な環境でコードを実行し、実行結果を含む包括的な回答を提供します。

**重要な制限**: 実装テスト結果により、コード実行機能は現在**Anthropic Claudeモデルのみ**で利用可能です。Google AI/Vertex AI、OpenAIでは動作しないことが確認されています。

**Why this priority**: コード実行機能は技術的なタスクや計算を伴う分析に重要ですが、基本機能とWeb検索の後の優先度です。

**Independent Test**: 計算やデータ分析を要求し、コード実行結果を含む正確な回答を受け取ることで検証可能です。

**Acceptance Scenarios**:

1. **Given** Anthropic Claudeモデルでコード実行機能付きエージェントが設定されている、**When** 数値計算やデータ処理を要求する、**Then** 適切なコードを生成・実行し結果を含む回答を提供する
2. **Given** エージェントがコードを実行する、**When** 実行が完了する、**Then** 実行結果とその解釈を分かりやすく説明する
3. **Given** ユーザが複雑な計算問題を送信する、**When** システムが処理する、**Then** step-by-stepでコード実行プロセスを示し最終結果を提供する
4. **Given** ユーザが実装テスト結果でサポートされていないプロバイダー（Google AI/Vertex AI/OpenAI）でコード実行を試行する、**When** システムが初期化を試行する、**Then** 明確なエラーメッセージでAnthropic Claudeの使用を促し、実行を終了する

---

## Authentication & Security Requirements

### AUTH-001: AI Provider Authentication

**憲章第9条準拠**: 暗黙的フォールバックを完全に禁止し、明示的エラー処理を強制します。

**サポート対象プロバイダー**:
1. **Google AI (Gemini API)**: `GOOGLE_API_KEY` 環境変数による認証（`plain`, `web-search`のデフォルト）
2. **Vertex AI**: `GOOGLE_APPLICATION_CREDENTIALS` 環境変数による認証（`plain`, `web-search`の代替）
3. **Anthropic Claude**: `ANTHROPIC_API_KEY` 環境変数による認証（`code-exec`専用）

**認証要件**:

#### AUTH-001a: Google AI認証
- **適用エージェント**: `plain`, `web-search`（デフォルト）
- **必須環境変数**: `GOOGLE_API_KEY`
- **検証タイミング**: エージェント初期化時（実行前）
- **失敗時動作**: 即座にエラー終了、明確なエラーメッセージ表示
- **フォールバック禁止**: 他の認証方法、モック応答、デフォルト値への自動切り替えを禁止

#### AUTH-001b: Vertex AI認証
- **適用エージェント**: `plain`, `web-search`（環境変数で切り替え時）
- **必須環境変数**: `GOOGLE_APPLICATION_CREDENTIALS`（GCP認証JSONファイルへのパス）
- **オプション変数**: `GOOGLE_GENAI_USE_VERTEXAI=true`（Vertex AI使用明示）
- **検証タイミング**: エージェント初期化時（実行前）
- **失敗時動作**: 即座にエラー終了、認証設定の確認を促すメッセージ
- **フォールバック禁止**: Google AI APIへの自動フォールバック、モック応答を禁止

#### AUTH-001c: Anthropic Claude認証
- **適用エージェント**: `code-exec`のみ（固定）
- **必須環境変数**: `ANTHROPIC_API_KEY`
- **検証タイミング**: エージェント初期化時（実行前）
- **失敗時動作**: 即座にエラー終了、明確なエラーメッセージ表示
- **フォールバック禁止**: 他のプロバイダーへの自動切り替え、モック応答を禁止

### AUTH-002: テスト環境分離

**憲章第9条準拠**: テスト環境と本番環境の明確な分離を強制します。

**テスト環境識別**:
- **条件**: `PYTEST_CURRENT_TEST` 環境変数が設定されている場合のみ
- **動作**: Pydantic AI `TestModel()` の使用を許可
- **制約**: 実際のAPI認証をスキップ（テスト専用）

**本番環境要件**:
- **条件**: `PYTEST_CURRENT_TEST` が未設定の場合
- **動作**: 必ず実際のAIプロバイダー認証を実行
- **TestModel禁止**: いかなる場合もTestModelへのフォールバックを禁止
- **認証失敗時**: 明確なエラーで即座に終了

### AUTH-003: 認証エラー処理

**憲章第9条準拠**: すべての認証エラーで明示的処理を強制します。

**エラー分類と対応**:

#### 資格情報不足
- **検出**: 必須環境変数の未設定
- **動作**: 設定手順を含む詳細なエラーメッセージで終了
- **例**: "GOOGLE_API_KEY not found. Set environment variable: export GOOGLE_API_KEY=your_key"

#### 資格情報無効
- **検出**: API呼び出し時の認証エラー
- **動作**: 認証情報の確認を促すエラーメッセージで終了
- **リトライ禁止**: 認証エラーでのリトライは実行しない

#### ファイル関連エラー（Vertex AI）
- **検出**: `GOOGLE_APPLICATION_CREDENTIALS` ファイル不存在、権限エラー
- **動作**: ファイルパスと権限の確認を促すエラーメッセージで終了

**禁止事項**:
- 認証エラー時のサイレント継続
- モック応答への自動切り替え
- 部分的機能での動作継続
- 認証情報の推測・補完

### AUTH-004: 憲章第9条遵守検証

**データ精度義務の強制**:

1. **NO ハードコーディング**: 認証情報のコード内埋め込み禁止
2. **NO 暗黙的フォールバック**: 認証失敗時の自動代替処理禁止
3. **NO サイレントエラー**: 認証関連エラーの隠蔽禁止
4. **明示的データソース**: 環境変数による明示的認証情報指定
5. **適切なエラー伝播**: 認証エラーの明確なメッセージと即座終了

**実装検証項目**:
- `TestModel()` 使用条件の厳密チェック
- 環境変数検証ロジックの実装
- エラーメッセージの明確性確認
- フォールバック処理の完全削除

---

### Edge Cases

以下のエッジケースに対する具体的な動作を定義します。**重要**: エラー発生時は代替処理を行わず、明確なエラーで終了します。

#### EC-000: コマンドラインオプションエラー

**問題**: `--config`と`--agent`オプションの不正な使用

**動作**:
1. **両方未指定**: エラーメッセージ「Error: Either --config or --agent must be specified」を表示して即座に終了
2. **両方指定**: エラーメッセージ「Error: --config and --agent are mutually exclusive」を表示して即座に終了
3. **存在しないファイルパス（--config）**: エラーメッセージ「Error: Config file not found: <path>」を表示して終了
4. **無効なエージェント名（--agent）**: エラーメッセージ「Error: Unknown agent '<name>'. Available agents: plain, web-search, code-exec」を表示して終了
5. **代替処理禁止**: デフォルト設定の自動適用、推測による代替エージェント選択は行わない

**ユーザー対応**: 正しいオプション指定方法を示すヘルプメッセージを表示

#### EC-001: TOML設定ファイルエラー

**問題**: TOMLファイルの構文エラー、必須フィールド不足、データ型不一致

**動作**:
1. **構文エラー**: CLI実行開始時に即座にエラー終了、詳細なエラー位置を表示
2. **バリデーションエラー**: Pydantic検証で詳細なフィールド別エラーメッセージを表示して終了
3. **代替処理禁止**: デフォルト値での自動補完や部分的な設定読み込みは行わない

**ユーザー対応**: 設定ファイル修正後の再実行を促すメッセージを表示

#### EC-002: Google API接続エラー

**問題**: APIキー無効、Vertex AI認証失敗、ネットワーク接続エラー、APIレート制限

**動作**:
1. **認証エラー**: 即座にエラー終了、認証設定の確認を促すメッセージを表示
2. **ネットワークエラー**: Pydantic AIの max_retries 設定に従い自動リトライ、上限到達後はエラー終了
3. **レート制限**: Pydantic AIの組み込みリトライロジックに従い指数バックオフで再試行、上限到達後はエラー終了
4. **代替処理禁止**: オフラインモード、モックレスポンス、別APIへのフォールバック等は行わない

**リトライ設定**: TOML設定ファイルの `agent.max_retries` で制御（Pydantic AIに委任）

#### EC-003: ツール実行タイムアウト

**問題**: Web検索、コード実行がタイムアウト制限を超過

**動作**:
1. **タイムアウト検出**: ツール固有のタイムアウト値で強制終了
2. **エラー結果**: 部分的な結果も含めて完全にエラーとして扱う
3. **代替処理禁止**: タイムアウト後の継続実行、部分結果の利用は行わない

**設定**: TOML設定の `tool_settings.*.timeout` で個別制御

#### EC-004: 複数ツール協調呼び出し

**問題**: Member Agentが複数のPydantic AI Toolを必要に応じて利用する際、構成不足やツール間依存が原因で失敗が発生する

**動作**:
1. **ツール登録**: `agent.capabilities` に列挙されたPydantic AI Toolをすべて登録し、Pydantic AIランタイムに委譲する
2. **設定検証**: `agent.tool_settings.<tool_name>` に定義されたパラメータが必要条件を満たしているかを実行前に検証し、不足時は構成エラーで終了する
3. **オーケストレーション**: ツール呼び出し順序や必要性の判断はPydantic AIのTool Routerに委ね、明示的な順序制御や並列強制は行わない
4. **代替処理禁止**: ツール呼び出しに失敗した場合でも暗黙のフォールバックや未定義ツールの自動利用は行わず、明示的なエラーハンドリングを適用する

#### EC-005: system_instruction / system_prompt検証エラー

**問題**: 無効な文字や利用不可能なフォーマットが含まれる`system_instruction`または`system_prompt`

**動作**:
1. **`system_instruction`/`system_prompt`空文字**: 許容し、そのままモデルに渡す（空文字は明示的指示なしとして扱う）
2. **`system_instruction`未定義**: TOMLに`system_instruction`が存在しない場合はエージェント同梱のデフォルト指示文を自動適用
3. **`system_prompt`指定**: 空文字ではない有効な文字列が設定されている場合はPydantic AIの`system_prompt`パラメータにそのまま渡し、`system_instruction`と併用する
4. **履歴継続時**: `system_prompt`は履歴内に保持され、`system_instruction`は最新値で再適用されることを前提にログ出力とテストを行う
5. **無効文字検出**: いずれのフィールドもPydanticバリデーションでエラー終了
6. **代替処理禁止**: 暗黙の推測や他フィールドへのフォールバックは行わない

**検証**: 設定読み込み時に実施、実行前にエラー検出

#### EC-006: 実行タイムアウト

**問題**: Agent実行が timeout_seconds で設定された制限を超過

**動作**:
1. **タイムアウト検出**: HTTP requestタイムアウトが発生
2. **即座に終了**: タイムアウト時は処理を完全停止
3. **タイムアウト情報表示**: 設定されたタイムアウト値を明示
4. **代替処理禁止**: タイムアウト延長、継続実行は行わない

**設定**: TOML設定の `agent.timeout_seconds` で制御

#### EC-007: 予期しないモデル出力

**問題**: Pydantic AI ReflectionでもValidationErrorが解決できない場合

**動作**:
1. **最大リトライ**: TOML設定の `agent.max_retries` まで自動リトライ（Pydantic AIに委任）
2. **リトライ後失敗**: 全リトライ試行後もエラーが継続する場合は完全にエラー終了
3. **代替処理禁止**: 部分的パース、フォーマット修正、手動解釈は行わない

**ログ**: 全リトライ履歴とエラー詳細を記録

#### EC-008: Code Execution Security

**問題**: Code Execution AgentによるPython実行時の安全性確保

**重要**: Pydantic AI の `CodeExecutionTool` はセキュリティ設定を一切持たない単なる有効化フラグです。全てのセキュリティ制約はモデルプロバイダー（Anthropic/OpenAI/Google）側で実装・制御されており、**設定不可能**です。

**サポート対象プロバイダー**: **Anthropic Claudeのみ**

##### Anthropic Claude (唯一の対応プロバイダー)
- **実行環境**: Linux-based x86_64 container、完全隔離（ホストおよび他コンテナから）
- **リソース制限**: 5 GiB RAM、5 GiB Disk、1 CPU（固定、設定不可）
- **タイムアウト**: 最小5分（設定不可、TOML設定は無効）
- **ネットワーク**: 完全無効（インターネットアクセス不可、セキュリティのため）
- **ファイルシステム**: ワークスペースディレクトリのみアクセス可
- **許可モジュール**: pandas, numpy, matplotlib, scikit-learn, scipy, seaborn, Pillow, openpyxl（固定、設定不可）

##### Google AI / Vertex AI / OpenAI
- **コード実行サポート**: **サポート対象外**
- **動作**: エージェント初期化時に明示的エラーで終了
- **エラーメッセージ**: Anthropic Claudeモデルの使用を促す具体的な指示を含む

**既知のセキュリティリスク**（修正済み）:
- **CVE-2025-54794** (CVSS 7.7): パス制限メカニズムの脆弱性 → 修正済み
- **CVE-2025-54795** (CVSS 8.7): コマンドインジェクション脆弱性 → 修正済み

**推奨セキュリティ対策**:
1. 本番環境では信頼できるプロンプトのみを使用
2. ユーザー入力を直接コード実行に渡さない
3. プロバイダーのセキュリティアップデートを継続監視
4. Anthropic Claude の利用を推奨（最も詳細なセキュリティ情報）

**設定制約**:
- TOML設定の `timeout`, `allowed_modules`, `max_output_length` は**実装不可能**
- これらの設定は documentation-only として扱う
- 実際の制約はプロバイダーに依存

**実装方針**:
1. Pydantic AI の `CodeExecutionTool()` をそのまま使用（設定パラメータなし）
2. プロバイダーのネイティブセキュリティ実装を信頼
3. セキュリティ設定の制御は行わない（実装不可能のため）
4. プロバイダーのセキュリティアップデートを定期監視

**テスト要件**:
- Escape attempt tests: サンドボックス脱出試行の検出
- Resource exhaustion tests: CPU/メモリ/ディスク上限の強制
- Malicious code detection: 不正モジュールimport、ネットワークアクセス試行の検出

**TOML設定例**:

**標準エージェント `plain`（デフォルト設定例）**:
```toml
# プレーン推論エージェント（mixseek_core/configs/agents/plain.toml）
[agent]
name = "plain"
type = "plain"
model = "google-gla:gemini-2.5-flash-lite"  # デフォルト: Gemini 2.0 Flash Lite
temperature = 0.7
max_tokens = 2048
system_instruction = "あなたは親切で正確な情報を提供するアシスタントです。"
# 任意: system_prompt = "常に日本語で回答してください"
capabilities = []  # ツール未使用
```

**標準エージェント `web-search`（デフォルト設定例）**:
```toml
# Web検索機能付きエージェント（mixseek_core/configs/agents/web-search.toml）
[agent]
name = "web-search"
type = "web_search"
model = "google-gla:gemini-2.5-flash-lite"  # デフォルト: Gemini 2.0 Flash Lite
temperature = 0.5
max_tokens = 4096
system_instruction = "あなたは最新情報を検索し、正確な分析を提供するリサーチエージェントです。"
# 任意: system_prompt = "常に日本語で回答してください"
capabilities = ["web_search"]
```

**標準エージェント `code-exec`（Anthropic Claude専用）**:
```toml
# コード実行機能付きエージェント（mixseek_core/configs/agents/code-exec.toml）
[agent]
name = "code-exec"
type = "code_execution"
model = "anthropic:claude-haiku-4-5"  # 固定: Claude Haiku 4.5
temperature = 0.1
max_tokens = 4096
system_instruction = "あなたはデータ分析とコード実行が可能なアシスタントです。"
# 任意: system_prompt = "常に日本語で回答してください"
capabilities = ["code_execution"]

[agent.tool_settings.code_execution]
# 注意: これらの設定は documentation-only です
# 実際のセキュリティ制約はAnthropic側で制御されます
expected_available_modules = ["pandas", "numpy", "matplotlib", "scikit-learn"]
expected_min_timeout_seconds = 300  # Anthropic側で5分最小値が強制される
```

**カスタムエージェント例（ユーザー定義）**:
```toml
# カスタムデータ分析エージェント（ユーザー定義TOML）
[agent]
name = "data-analyst"
type = "custom"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 4096
system_instruction = "あなたはデータ分析に特化したエージェントです。統計的手法を用いて洞察を提供します。"
capabilities = ["web_search"]  # カスタムエージェントでも標準ツールを使用可能
description = "データ分析と統計的洞察を提供するカスタムエージェント"

[agent.retry_config]
max_retries = 2

[agent.usage_limits]
total_tokens_limit = 50000
```

## Requirements

### Functional Requirements

- **FR-001**: システムは3種類の標準Member Agentをmixseek-coreパッケージ内にバンドルして提供しなければならない。各標準エージェントは以下の通り：
  - **`plain`**: プレーン推論エージェント（ツールなし、基本的な質問応答）
    - デフォルトモデル: `gemini-2.5-flash-lite`（Google AI Gemini 2.0 Flash Lite）
    - 環境変数（`GOOGLE_API_KEY`）で認証、`GOOGLE_GENAI_USE_VERTEXAI`でVertex AI切り替え可能
  - **`web-search`**: Web検索機能付きエージェント（Pydantic AI WebSearchTool統合）
    - デフォルトモデル: `gemini-2.5-flash-lite`（Google AI Gemini 2.0 Flash Lite）
    - 環境変数（`GOOGLE_API_KEY`）で認証、`GOOGLE_GENAI_USE_VERTEXAI`でVertex AI切り替え可能
  - **`code-exec`**: コード実行機能付きエージェント（Pydantic AI CodeExecutionTool統合、Anthropic Claude専用）
    - モデル: `claude-haiku-4-5`（Anthropic Claude Haiku 4.5）固定
    - 環境変数（`ANTHROPIC_API_KEY`）で認証
  - 各標準エージェントの設定は `mixseek_core/configs/agents/<name>.toml` にパッケージリソースとして格納
  - `--agent <name>` オプションで名前指定のみで利用可能
- **FR-002**: 各Member AgentはPydantic AIフレームワークを基盤として実装されなければならない
- **FR-003**: システムは以下のAIプロバイダーをサポートしなければならない：
  - **Google AI (Gemini API)**: `plain`, `web-search`のデフォルトプロバイダー（`GOOGLE_API_KEY`環境変数で認証）
  - **Vertex AI**: `plain`, `web-search`の代替プロバイダー（`GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_GENAI_USE_VERTEXAI=true`環境変数で認証）
  - **Anthropic Claude**: `code-exec`専用プロバイダー（`ANTHROPIC_API_KEY`環境変数で認証）
- **FR-004**: システムは開発・テスト用途に限定したMember Agent動作検証機能を提供しなければならない。以下の仕様に従う：
  - **コマンド形式**: `mixseek member "prompt" --config <path>` または `mixseek member "prompt" --agent <name>`
  - **オプション仕様**:
    - `--config <path>`: カスタムTOML設定ファイルのパス（絶対パスまたは相対パス）を指定
    - `--agent <name>`: mixseek-coreにバンドルされた標準エージェント名を指定（`plain`, `web-search`, `code-exec`のいずれか）
    - 両オプションは相互排他的であり、どちらか一方のみ指定可能
    - どちらか一方は必須（両方未指定または両方指定の場合はエラー）
  - **警告表示**: 実行時には毎回、開発・テスト専用である旨の簡潔な警告メッセージ（1行、例: "⚠️  Development/Testing only - Not for production use"）を標準エラー出力に表示しなければならない
- **FR-005**: 各Member Agentの`system_instruction`（Pydantic AIの`instructions`）はTOMLファイルでカスタマイズ可能でなければならない
  - 空文字も有効な入力として許容し、エージェントは該当指示文をそのまま使用する
  - TOMLに`system_instruction`が未定義の場合は、エージェントに同梱されたデフォルト指示文を自動適用する
  - `system_prompt`フィールドが設定された場合はPydantic AIの`system_prompt`パラメータに渡し、`system_instruction`（省略時デフォルト）と併用してエージェントを初期化する
  - 会話履歴が継続するケースでは`system_instruction`が常に現在の値で再評価され、`system_prompt`は履歴に保持されることを前提にテスト・実装する
- **FR-006**: Web検索機能付きエージェントはPydantic AIのWebSearchToolを統合しなければならない
- **FR-007**: コード実行機能付きエージェントはPydantic AIのCodeExecutionToolを統合しなければならない。**重要な制限**: 実装テスト結果により、コード実行機能は現在Anthropic Claudeモデル（anthropic:claude-sonnet-4-5-20250929等）でのみ利用可能です。Google AI/Vertex AI/OpenAIでは動作しないことが確認されており、明示的なエラーメッセージで終了しなければならない。セキュリティ制約は全てAnthropic側で制御され、設定不可能である
- **FR-008**: システムはGoogle Cloud認証情報（GOOGLE_APPLICATION_CREDENTIALS環境変数）を適切に処理しなければならない
- **FR-009**: TOMLファイルはエージェント名、`system_instruction`、ツール設定、モデル設定を定義できなければならない
  - `agent.type`フィールド: 標準タイプ（`"plain"`, `"web_search"`, `"code_execution"`）またはカスタムタイプ（`"custom"`で固定）を指定可能。カスタムエージェントの識別は`name`フィールドで行う
  - `system_prompt`フィールドは任意項目として定義でき、指定された場合はPydantic AIの`system_prompt`に渡す（ドキュメント上は高度な利用者向け注記として扱う）
  - `capabilities` 配列でPydantic AIが提供するTool IDを複数列挙できるようにし、配列順序には意味を持たせず、実際の呼び出し順序はPydantic AIのツールオーケストレーションに委ねる
  - 各ツール固有の設定値が存在する場合は `tool_settings.<tool_name>` セクションでユーザが明示的に指定する（例: `web_search`, `code_execution`）。詳細は `draft/references/pydantic-ai-docs/tools.md` を参照
- **FR-010**: エージェントは構造化出力をサポートしなければならない
- **FR-011**: システムはエージェント実行時の詳細なロギングと監視機能を提供しなければならない。以下の項目を記録する：
  - **必須ログ項目**:
    - Model ID and version (例: `google-gla:gemini-2.5-flash-lite`, `anthropic:claude-haiku-4-5`)
    - API request/response metadata (timestamp, latency, status code)
    - UsageLimits情報 (tokens used/limit, requests used/limit)
    - Tool invocation details (tool name, parameters, execution time, result status)
    - Retry attempts (retry count, backoff delay, final outcome)
    - Warning and error messages (with stack traces for errors)
    - Agent configuration summary (name, type, capabilities)
  - **監視メトリクス**:
    - Request latency (p50, p95, p99 percentiles)
    - Token usage per agent type and model
    - Tool execution success/failure rates
    - Retry rate and failure patterns by error type
    - API error rate by status code (4xx, 5xx)
  - **ログ出力先**:
    - Standard output: INFO level以上のメッセージ
    - File logging: DEBUG level含む全ログ (`~/.mixseek/logs/member-agent-{date}.log`)
    - Structured JSON format: 監視ツール連携用 (optional)
- **FR-012**: エラーハンドリングとタイムアウト処理を適切に実装しなければならない
- **FR-013**: 各エージェントタイプは独立して動作し、他のエージェントタイプに依存しないよう設計されなければならない
- **FR-014**: システムは設定検証機能を提供し、不正なTOMLファイルを検出・報告しなければならない
- **FR-015**: エージェントはmixseek-coreのMember Agentインターフェースと互換性を持たなければならない
- **FR-016**: `MemberAgentResult`はPydantic AIの`result.all_messages()`（完全なメッセージ履歴、`list[ModelMessage]`型）を保持し、Leader Agentに渡さなければならない。これにより、Member Agentの内部動作（ツール呼び出し、中間推論過程、リトライ履歴）をLeader Agentが記録・分析でき、デバッグ・監査・改善に活用できる
- **FR-017**: `BaseMemberAgent`抽象基底クラスは以下の要件を満たさなければならない：
  - **必須メソッド**: `execute(task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> MemberAgentResult` のみ
  - **初期化**: `__init__(config: MemberAgentConfig)` で統一（設定をコンストラクタで受け取る）
  - **型安全性**: すべてのメソッドシグネチャに型注釈を含む
  - カスタムエージェント開発者は `BaseMemberAgent` を継承し、`execute()` メソッドを実装することで最小限の実装が可能
- **FR-018**: `context`パラメータは以下の推奨構造に従うべきである（ただし完全な自由度を持つ`Dict[str, Any]`として定義され、追加キーも許可される）：
  - **推奨キー**:
    - `previous_results: list[Dict[str, Any]]` - 他のMember Agentの実行結果（任意）
    - `round_info: Dict[str, Any]` - ラウンド番号、チームID等のメタデータ（任意）
    - `constraints: Dict[str, Any]` - トークン制限、タイムアウト等の実行制約（任意）
    - `metadata: Dict[str, Any]` - その他のコンテキスト情報（任意）
  - **柔軟性**: 上記キーは推奨であり、実装者は独自のキーを追加可能
  - **現在のステータス**: Leader Agent実装では現在未使用、将来の拡張のために予約されている
- **FR-019**: すべてのエラーメッセージは以下の推奨フォーマットに従うべきである：
  - **形式**: `Error: <エラー概要>. <詳細説明または対処方法>`
  - **要件**:
    - 必ず `Error:` プレフィックスで開始
    - エラー概要は簡潔に（1文以内）
    - 可能な場合は具体的な対処方法を含める
    - 標準エラー出力（stderr）に出力
  - **例**:
    - `Error: Config file not found: /path/to/config.toml. Please check the file path.`
    - `Error: --config and --agent are mutually exclusive. Use only one option.`
    - `Error: GOOGLE_API_KEY not found. Set environment variable: export GOOGLE_API_KEY=your_key`
- **FR-020**: システムはカスタムMember Agentの動的ロード機構を提供しなければならない。以下の2つのロード方式をサポートする：
  - **agent_module方式（推奨）**: Pythonモジュールパス（`importlib.import_module`）からエージェントクラスをインポート
    - 用途: 本番環境、SDKとしての配布、`pip install`可能なパッケージ
    - 設定例: `[agent.metadata.plugin]`セクションで`agent_module = "my_package.agents.custom"`を指定
  - **path方式（代替）**: ファイルパス（`importlib.util`）からエージェントクラスをロード
    - 用途: 開発プロトタイピング、スタンドアロンファイルでの実装
    - 設定例: `[agent.metadata.plugin]`セクションで`path = "/path/to/custom_agent.py"`を指定
  - 両方式とも`agent_class`フィールドでクラス名を指定しなければならない（例: `agent_class = "MyCustomAgent"`）
- **FR-021**: カスタムエージェントロード時の優先順位処理を以下の通り実装しなければならない：
  - **第1優先**: `agent_module`が指定されている場合、モジュールインポートを試行
  - **第2優先**: `agent_module`が未指定または失敗した場合、`path`からのロードを試行
  - **標準エージェント**: `agent.type`が標準タイプ（`plain`, `web_search`, `code_execution`）の場合、動的ロードをスキップ
  - ロード成功後、`MemberAgentFactory.register_agent()`でファクトリに登録しなければならない
- **FR-022**: カスタムエージェントロード失敗時のエラーハンドリングを実装しなければならない：
  - **必須情報**: エラーメッセージには以下を含める
    - ロード方式（agent_module/path）
    - 試行したモジュール名またはファイルパス
    - 失敗原因（ModuleNotFoundError, ImportError, AttributeError等）
    - 推奨対処方法（パッケージインストール、パスの確認、クラス名の確認等）
  - **例**:
    - `Error: Failed to load custom agent from module 'my_package.agents.custom'. ModuleNotFoundError: No module named 'my_package'. Install package: pip install my-package`
    - `Error: Failed to load custom agent from path '/path/to/custom_agent.py'. FileNotFoundError: File not found. Check file path in TOML config.`
    - `Error: Custom agent class 'MyCustomAgent' not found in module 'my_package.agents.custom'. Check agent_class in TOML config.`

### Key Entities

- **BaseMemberAgent**: すべてのMember Agentが継承する抽象基底クラス
  - **必須メソッド**: `execute(task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> MemberAgentResult`
  - **初期化**: `__init__(config: MemberAgentConfig)` で設定を受け取る
  - **用途**: カスタムエージェント開発者はこのクラスを継承して`execute()`を実装する
- **Context Parameter**: `execute()`メソッドの`context`パラメータ（Leader AgentからMember Agentへのコンテキスト情報）
  - **型**: `Optional[Dict[str, Any]]`（完全な柔軟性）
  - **推奨キー**: `previous_results`, `round_info`, `constraints`, `metadata`（詳細はFR-018参照）
  - **現在のステータス**: 将来の拡張のために予約（現在のLeader Agent実装では未使用）
- **Member Agent**: Pydantic AIベースの専門エージェント（プレーン、Web検索付き、コード実行付きの3種類）
- **Standard Bundled Agents**: mixseek-coreパッケージにバンドルされる3つの標準エージェント
  - `plain`: プレーン推論エージェント（デフォルトモデル: `gemini-2.5-flash-lite`、設定: `mixseek_core/configs/agents/plain.toml`）
  - `web-search`: Web検索機能付きエージェント（デフォルトモデル: `gemini-2.5-flash-lite`、設定: `mixseek_core/configs/agents/web-search.toml`）
  - `code-exec`: コード実行機能付きエージェント（モデル: `claude-haiku-4-5` 固定、設定: `mixseek_core/configs/agents/code-exec.toml`、Anthropic Claude専用）
- **TOML Configuration**: エージェントの`system_instruction`、ツール設定、モデル設定を定義する設定ファイル
  - **`agent.type`**: 標準タイプ（`"plain"`, `"web_search"`, `"code_execution"`）またはカスタムタイプ（`"custom"`で固定。エージェント識別は`name`フィールドで行う）
  - **`agent.metadata.plugin`**: カスタムエージェントの動的ロード設定（`type = "custom"`使用時のみ必須）
    - **`agent_module`** (推奨): Pythonモジュールパス（例: `"my_package.agents.custom"`、本番環境・SDK配布用）
    - **`path`** (代替): ファイルパス（例: `"/path/to/custom_agent.py"`、開発プロトタイピング用）
    - **`agent_class`** (必須): エージェントクラス名（例: `"MyCustomAgent"`）
    - 優先順位: `agent_module` → `path`（両方指定時は`agent_module`を優先）
- **System Instruction**: エージェントの動作を制御する指示文（TOMLの`system_instruction`で定義、Pydantic AI `instructions`にマッピング）
- **System Prompt (optional)**: メッセージ履歴に保持され、他エージェントに引き継がれる永続的なガイドラインを定義するプロンプト（TOMLの`system_prompt`で定義、Pydantic AI `system_prompt`に渡され`system_instruction`と併用）
- **Tool Integration**: WebSearchToolとCodeExecutionToolのPydantic AI統合
- **Model Connection**: Gemini API/Vertex AIへの接続と認証処理
- **Command Interface**: `mixseek member`コマンドの開発・テスト用CLIインターフェース
- **Response Output**: エージェントが生成する構造化された応答結果（`MemberAgentResult`）。`content`（テキスト応答）、`status`、`usage_info`に加え、`all_messages`（Pydantic AI `list[ModelMessage]`型の完全な対話履歴）を含み、Leader Agentがツール呼び出しや中間推論を記録・分析できる
- **Configuration Validator**: TOML設定ファイルの検証とエラー処理機能

## Success Criteria

### Measurable Outcomes

- **SC-001**: ユーザが各タイプのMember Agentを30秒以内で起動し、基本的な質問応答を完了できる
- **SC-002**: Web検索機能付きエージェントが90%以上の確率で関連性の高い最新情報を取得・提供する
- **SC-003**: コード実行機能付きエージェントが数値計算タスクを95%以上の精度で正しく実行し結果を提供する
- **SC-004**: TOML設定ファイルの変更がエージェントの動作に即座に反映され、設定ミスは明確なエラーメッセージで報告される
- **SC-005**: Gemini APIとVertex AI両方の接続で99%以上の可用性を維持する
- **SC-006**: システムが複数の同時リクエストを処理し、応答時間が平均5秒以内を維持する
- **SC-007**: エージェント実行の全プロセスが詳細にロギングされ、デバッグ情報が完全に取得される
- **SC-008**: ユーザ満足度調査で80%以上のユーザがエージェントの応答品質に満足する
- **SC-009**: システムエラー発生時に90%以上のケースで自動回復または適切なエラー処理を実行する

## Clarifications

### Session 2025-10-21

- Q: FR-004の用途をmixseek-coreアーキテクチャに適合するよう開発・テスト用途に限定すべきか？ → A: 開発・テスト用途に限定
- Q: FR-010のストリーミング応答サポートを削除すべきか？ → A: ストリーミング応答は削除
- Q: 技術調査結果に基づき、コード実行機能をAnthropic Claudeモデルのみに明示的に制限すべきでしょうか？ → A: コード実行をAnthropic Claudeモデルのみに制限し、要件とユーザーストーリーを更新
- Q: FR-007のコード実行機能要件において、サポートされていないプロバイダー（Google AI/Vertex AI/OpenAI）に対する明示的なエラーハンドリングを追加すべきでしょうか？ → A: 明示的なエラーハンドリングを追加し、サポートされていないプロバイダーに対して具体的なエラーメッセージを表示
- Q: User Story 3（コード実行機能付きMember Agent）において、Anthropic Claude以外のプロバイダーを使用した場合の代替動作を定義すべきでしょうか？ → A: 明示的エラーで終了し、Anthropic Claudeの使用を促すメッセージを表示
- Q: TOML設定例やドキュメントにおいて、コード実行機能のためのモデル指定例をAnthropic Claudeのみに更新すべきでしょうか？ → A: Anthropic Claude専用の設定例のみを提供し、他のプロバイダーの例は削除または非推奨として明記
- Q: EC-008（Code Execution Security）セクションにおいて、プロバイダー別セキュリティ制約の記述をAnthropic Claudeに焦点を当てて簡素化すべきでしょうか？ → A: Anthropic Claudeのセキュリティ制約を詳細に記述し、他のプロバイダーは「サポート対象外」として簡潔に記載

### Session 2025-10-22

- Q: コマンド名を `mixseek member` に変更すると、「開発・テスト専用」という性質が名前から読み取れなくなります。この点についてどのように対処しますか？ → A: 開発・テスト専用であることを警告メッセージとドキュメントで明確化し、コマンド名はシンプルに保つ
- Q: `mixseek member` コマンドの実行時に表示する警告メッセージについて、どのような内容と表示方法が適切でしょうか？ → A: 毎回表示するが簡潔な1行メッセージ（例: "⚠️  Development/Testing only - Not for production use"）
- Q: `--config agent_name.toml` と `--agent agent_name` の2つのオプションの使い分けについて明確化が必要です。どのように区別しますか？ → A: `--config`は設定ファイルパス指定、`--agent`はmixseek-core標準エージェント名指定（相互排他的）
- Q: 標準エージェントの命名規則とバンドル構成について、どのようにしますか？ → A: 各タイプごとに1つの標準エージェント（`plain`, `web-search`, `code-exec`）をパッケージ内TOMLファイルとしてバンドル
- Q: 標準エージェント（`plain`, `web-search`, `code-exec`）のデフォルトAIモデル設定について明確化が必要です。どのモデルを使用しますか？ → A: `plain`と`web-search`はGemini（Google AI）をデフォルトとし、`code-exec`は`claude-haiku-4-5`（Anthropic Claude Haiku 4.5）を使用。ユーザーは環境変数でプロバイダー切り替え可能
- Q: Gemini 1.5 Flashは利用できません。どのモデルを使用しますか？ → A: `gemini-2.5-flash-lite`を使用

### Session 2025-10-28

- Q: Member Agentのツール呼び出しポリシーをどのように定義しますか？ → A: 複数ツールを必要に応じて呼び出し、設定項目があるツールはTOMLでユーザが制御
- Q: `system_instruction`（旧system_prompt）のバリデーションで空文字を許容しますか？ → A: 空文字を許容し、バリデーションではエラーにしない

### Session 2025-10-29

- Q: `system_instruction` 未指定時の挙動をどのように定義しますか？ → A: バンドル済みデフォルトの`system_instruction`を自動適用
- Q: `system_prompt`が設定された場合の扱いはどうなりますか？ → A: Pydantic AIの`system_prompt`として渡し、`system_instruction`（省略時はデフォルト）と併用する
- Q: `system_prompt`と`system_instruction`の履歴挙動はPydantic AIの公式ガイドに沿っていますか？ → A: Pydantic AIドキュメントの推奨通り、`system_instruction`は都度再適用し`system_prompt`は履歴に保持する前提で仕様化

### Session 2025-10-30

- Q: Member AgentはLeader Agentに`all_messages()`を渡すべきか？ → A: `MemberAgentResult`に`all_messages: list[ModelMessage]`フィールドを追加し、Pydantic AIの`result.all_messages()`を保持してLeader Agentに渡す

### Session 2025-11-19

- Q: 親仕様（標準エージェントバンドル）と子仕様（カスタムエージェント開発）のスコープ境界を明確化します。どのように分離しますか？ → A: 親仕様はカスタムエージェント作成の基本要件（BaseMemberAgent、TOML設定、--config）を含み、詳細な開発ガイドのみ子仕様へ切り出し
- Q: `BaseMemberAgent`インターフェースの必須メソッドと型定義を明確化します。カスタムエージェント開発者が実装する際、最小限実装すべきメソッドは何ですか？ → A: `execute(task, context, **kwargs) -> MemberAgentResult`のみ必須。初期化は`__init__(config: MemberAgentConfig)`で統一
- Q: TOML設定ファイルの`agent.type`フィールドについて明確化します。カスタムエージェントを作成する際、`type`にはどのような値を設定できますか？ → A: `"custom"`で固定。独自識別子（"data_analyst", "code_reviewer"等）は使用せず、エージェントの識別は`name`フィールドで行う
- Q: `context`パラメータ（`execute(task, context)`）の具体的な使用例とデータ構造を明確化します。Leader Agentが渡す`context`には何が含まれますか？ → A: 推奨構造を定義（標準キーを明示）、追加キーも許可（柔軟性維持）
- Q: エラーメッセージの形式について明確化します。すべてのエラーメッセージ（CLI、設定検証、認証エラー等）は統一されたフォーマットに従うべきですか？ → A: 推奨フォーマット定義（`Error: <概要>. <詳細>`形式、一貫性確保）
- Q: カスタムエージェントの動的ロード機構について明確化します。TOML設定で`agent.type = "custom"`と指定した場合、どのようにカスタムエージェントクラスをロードしますか？ → A: 2つのロード方式を実装：（1）agent_module方式（推奨、本番環境・SDK配布用、モジュールパスでインポート）、（2）path方式（代替、開発プロトタイピング用、ファイルパスでロード）。優先順位はagent_module→pathとし、両方とも`[agent.metadata.plugin]`セクションで設定

### Session 2025-11-20

- Q: 子仕様（018-custom-member）で`type = "custom"`固定に決定されました。親仕様でも同様に統一すべきですか？ → A: 親仕様でも`type = "custom"`固定に統一。独自識別子（"data_analyst", "code_reviewer"等）の使用は禁止し、エージェント識別は`name`フィールドで行う。これにより親仕様と子仕様の一貫性を確保

## MixSeek-Core Framework Integration

本Member Agentバンドルは、specs/001-specs/spec.mdで定義されたMixSeek-Coreフレームワークの要件に完全準拠します。以下に具体的な整合性を示します：

### FR-005 Member Agent要件との整合性

**FR-005要件**: "Member Agentは特定ドメインに特化しなければならない。システム標準Member Agent: mixseek-coreパッケージに組み込まれた標準エージェント。TOMLファイルで名前を指定するのみで利用可能"

**本仕様の対応**:
1. **特定ドメイン特化**: 3種類の特化エージェント（Plain推論、Web検索、コード実行）を提供
2. **システム標準Member Agent**: mixseek-coreパッケージに直接バンドル（`plain`, `web-search`, `code-exec`）
3. **名前指定のみで利用可能**: `--agent plain` 形式で標準エージェントを即座に利用可能
4. **カスタマイズ**: `--config custom.toml` でカスタムTOML設定も使用可能

### FR-005 共通実装パターンとの整合性

**FR-005要件**: "すべてのMember Agentは`BaseMemberAgent`基底クラスを継承し、`execute(task, context)`メソッドを実装"

**本仕様の対応** (contracts/member_agent_interface.py):
```python
class BaseMemberAgent(ABC):
    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MemberAgentResult:
```

### FR-019 通信プロトコルとの整合性

**FR-019要件**: "Leader AgentとMember Agent間の通信は、Pydantic AI Toolsetを通じた直接呼び出しで行う。同一プロセス内で実行される"

**本仕様の対応** (research.md Toolset Architecture):
- FunctionToolsetベースの実装パターン採用
- Leader Agentからの直接呼び出しをサポート
- 同一プロセス内実行による高速・低オーバーヘッド通信
- Usage trackingの完全対応

### FR-020 拡張可能設計との整合性

**FR-020要件**: "Member Agentのクラス設計は、ユーザがSDKでカスタムMember Agentを開発できるよう拡張可能でなければならない"

**本仕様の対応**:
1. **BaseMemberAgent基底クラス**: 拡張可能な抽象基底クラス提供
2. **Protocol定義**: MemberAgentProtocolによる型安全なインターフェース
3. **Factory Pattern**: MemberAgentFactoryによる拡張可能な登録システム
4. **TOML統合**: カスタムエージェントのTOML設定完全対応

### FR-012 リソース管理との整合性

**FR-012要件**: "Pydantic AI UsageLimitsによる1回のagent.run()呼び出しに対する制限"

**本仕様の対応**:
1. **UsageLimitsConfig**: TOML設定でのPydantic AI UsageLimits完全対応
2. **階層的制限**: request_limit, total_tokens_limit, tool_calls_limitをサポート
3. **リトライ統合**: RetryConfigとの連携による適切なエラーハンドリング

### FR-014 設定構造との整合性

**FR-014要件**: "Member Agent設定：名前、タイプ(system/custom)、モデル、capabilities、descriptionを定義。Pydantic Modelで設定構造を検証"

**本仕様の対応** (data-model.md MemberAgentConfig):
```python
class MemberAgentConfig(BaseModel):
    name: str                    # 名前
    type: AgentType             # タイプ(system相当)
    model: str                  # モデル
    system_instruction: str | None = None  # Pydantic AI instructions（Noneはデフォルト適用）
    system_prompt: str | None = None       # Pydantic AI system_prompt（Noneは未設定）
    capabilities: list[str]     # capabilities
    description: str            # description
    # Pydantic Modelによる完全検証
```

### Submission互換性

**MixSeek-Core Submission形式**: `content`, `format`, `metadata`, `generated_at`, `team_id`, `round_number`

**本仕様のMemberAgentResult**: 容易にSubmission形式に変換可能
- `content` → `content`
- `metadata` → `metadata`
- `timestamp` → `generated_at`
- 追加フィールド: `agent_name`, `agent_type`, `retry_count`, `all_messages`（Pydantic AI `list[ModelMessage]`型、Member Agentの完全な対話履歴を含む）

### TUMIX統合ポイント

**データベース永続化**: MixSeek-CoreのMessage History JSON保存と互換
**評価システム**: MemberAgentResultは`EvaluationResult`に変換可能
**チーム設定**: TOML階層構造でチーム全体設定に統合可能

### 開発・テスト専用の位置づけ

本Member Agentバンドルの`mixseek member`コマンドは開発・テスト専用です：

**本番環境での利用**:
- Leader AgentからPydantic AI Toolsetを通じた呼び出し
- Round ControllerによるSubmission管理
- Evaluatorによる評価とフィードバック

**開発環境での利用**:
- `mixseek member`による単体動作検証
- TOML設定の妥当性テスト
- API接続とツール動作の確認

## Assumptions

- Pydantic AIフレームワークの最新版を使用し、WebSearchToolとCodeExecutionToolが利用可能である
- Google Cloud Platform環境またはGemini API環境が適切に設定されている
- TOMLファイルはユーザが手動で作成・編集し、基本的なTOML構文を理解している
- Member Agentはmixseek-coreのチーム構成で他のエージェントと協調して動作する
- `system_instruction`は日本語と英語の両方をサポートし、`system_prompt`（任意指定）も同様に多言語対応する
- Pydantic AIの履歴挙動（`system_prompt`保持、`system_instruction`毎回再適用）を理解していることを前提とする
- エージェント実行環境はPython 3.13.9と必要な依存関係が利用可能である
- ネットワーク接続が安定しており、外部API（Gemini、Web検索）へのアクセスが可能である
- ユーザはCLIコマンドの基本的な使用方法を理解している
- セキュリティ設定では、コード実行は安全な環境で実行され、システムへの脅威とならない
- 設定ファイルとログファイルは適切なファイル権限で保護される
