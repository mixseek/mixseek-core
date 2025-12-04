# Configuration Reference

MixSeek-Core 設定リファレンス（完全版）

**このドキュメントについて**: 全設定項目の詳細リファレンス。基本的な使い方は [設定管理ガイド](configuration-guide.md) を参照してください。

---

## 概要

このドキュメントは、mixseek-coreで使用される全設定項目の網羅的なリファレンスです。

設定の基本的な使い方、優先順位チェーン、ユースケース例は [設定管理ガイド](configuration-guide.md) を参照してください。

---

## Leader Agent設定

Leader Agentは複数のMember Agentを統括し、タスクを分配・集約します。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| system_instruction | str \| None | None | TOML/定数 | team.leader.system_instruction | - | - | オプション | システム指示（Pydantic AIのinstructions） | ❌ |
| system_prompt | str \| None | None | TOML/定数 | team.leader.system_prompt | - | - | オプション | システムプロンプト（高度な利用者向け） | ❌ |
| model | str | "openai:gpt-4o" | TOML/定数 | team.leader.model | - | - | 必須 | LLMモデル（例: openai:gpt-4o, anthropic:claude-sonnet-4-5, grok:grok-2-1212, grok-responses:grok-4-fast） | ✅ |
| temperature | float \| None | None | TOML/定数 | team.leader.temperature | - | - | オプション | Temperature（0.0-2.0、Noneの場合はモデルデフォルト） | ❌ |
| max_tokens | int \| None | None | TOML/定数 | team.leader.max_tokens | - | - | オプション | 最大トークン数（> 0、Noneの場合はモデルデフォルト） | ❌ |
| timeout_seconds | int | 300 | TOML/定数 | team.leader.timeout_seconds | - | - | オプション | HTTPタイムアウト（秒、>= 0） | ✅ |
| max_retries | int | 3 | TOML/定数 | team.leader.max_retries | - | - | オプション | LLM API呼び出しの最大リトライ回数（>= 0） | ❌ |
| stop_sequences | list[str] \| None | None | TOML/定数 | team.leader.stop_sequences | - | - | オプション | 生成を停止するシーケンスのリスト | ❌ |
| top_p | float \| None | None | TOML/定数 | team.leader.top_p | - | - | オプション | Top-pサンプリングパラメータ（0.0-1.0、Noneの場合はモデルデフォルト） | ❌ |
| seed | int \| None | None | TOML/定数 | team.leader.seed | - | - | オプション | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | ❌ |

**設定例（TOML）**:
```toml
[team.leader]
model = "openai:gpt-4o"
system_instruction = "You are a helpful team leader coordinating multiple agents."
temperature = 0.7
timeout_seconds = 300
```

---

## Member Agent設定

Member Agentは特定のタスクを実行する専門エージェントです。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| name | str | - | TOML | agent.name | - | - | 必須 | Agent識別子 | ❌ |
| type | str | - | TOML | agent.type | - | - | 必須 | Agent種別（plain/web_search/code_execution） | ❌ |
| model | str | "google-gla:gemini-2.5-flash-lite" | TOML/定数 | agent.model | - | - | 必須 | Pydantic AIモデル識別子 | ✅ |
| temperature | float \| None | None | TOML/定数 | agent.temperature | - | - | オプション | Temperature（0.0-2.0、Noneの場合はモデルデフォルト） | ❌ |
| max_tokens | int \| None | None | TOML/定数 | agent.max_tokens | - | - | オプション | 最大トークン数（> 0、Noneの場合はモデルデフォルト） | ❌ |
| stop_sequences | list[str] \| None | None | TOML/定数 | agent.stop_sequences | - | - | オプション | 生成を停止するシーケンスのリスト | ❌ |
| top_p | float \| None | None | TOML/定数 | agent.top_p | - | - | オプション | Top-pサンプリングパラメータ（0.0-1.0、Noneの場合はモデルデフォルト） | ❌ |
| seed | int \| None | None | TOML/定数 | agent.seed | - | - | オプション | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | ❌ |
| timeout_seconds | int \| None | None | TOML/定数 | agent.timeout_seconds | - | - | オプション | HTTPリクエストタイムアウト（秒、>= 1、Noneの場合はデフォルトタイムアウト） | ❌ |
| max_retries | int | 3 | TOML/定数 | agent.max_retries | - | - | オプション | LLM API呼び出しの最大リトライ回数（>= 0、Pydantic AIに委任） | ❌ |
| system_instruction | str \| None | None | TOML | agent.system_instruction | - | - | オプション | システム指示テキスト | ❌ |
| system_prompt | str \| None | None | TOML/定数 | agent.system_prompt | - | - | オプション | システムプロンプト | ❌ |
| metadata | dict[str, Any] | {} | TOML/定数 | agent.metadata | - | - | オプション | カスタムプラグイン用メタデータ | ❌ |

**Tool設定（Web Search）**:

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| tool_settings.web_search.max_results | int | 10 | TOML/定数 | agent.tool_settings.web_search.max_results | - | - | オプション | Web検索最大結果数（範囲: 1-50） | ✅ |
| tool_settings.web_search.timeout | int | 30 | TOML/定数 | agent.tool_settings.web_search.timeout | - | - | オプション | Web検索タイムアウト（秒、範囲: 1-120） | ✅ |

**Tool設定（Code Execution）**:

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| tool_settings.code_execution.provider_controlled | Literal[True] | True | TOML/定数 | - | - | - | オプション | プロバイダー制御フラグ（ドキュメントのみ） | ✅ |
| tool_settings.code_execution.expected_min_timeout_seconds | int | 300 | TOML/定数 | - | - | - | オプション | 期待される最小タイムアウト（Anthropic固有） | ✅ |

**設定例（TOML）**:
```toml
[agent]
name = "researcher"
type = "web_search"
model = "google-gla:gemini-2.5-flash"
temperature = 0.7
max_tokens = 4096
timeout_seconds = 60
max_retries = 3
system_instruction = "You are a research agent specializing in web searches."

[agent.tool_settings.web_search]
max_results = 10
timeout = 30

[agent.metadata]
created_by = "user"
version = "1.0.0"
```

---

## Team Agent設定

Teamは1つのLeader Agentと複数のMember Agentで構成されます。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| team_id | str | - | TOML | team.team_id | - | - | 必須 | チームID | ❌ |
| team_name | str | - | TOML | team.team_name | - | - | 必須 | チーム名 | ❌ |
| max_concurrent_members | int | 15 | TOML/定数 | team.max_concurrent_members | - | - | オプション | 最大Member Agent数（範囲: 1-50） | ✅ |

**Member配列設定**:

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| members[].agent_name | str | - | TOML | team.members[].agent_name | - | - | 必須 | Agent名 | ❌ |
| members[].agent_type | str | - | TOML | team.members[].agent_type | - | - | 必須 | Agent種別 | ❌ |
| members[].tool_name | str \| None | None | TOML | team.members[].tool_name | - | - | オプション | Tool名（未指定時は自動生成: `delegate_to_{agent_name}`） | ❌ |
| members[].tool_description | str | - | TOML | team.members[].tool_description | - | - | 必須 | Tool説明（空文字列不可） | ❌ |
| members[].model | str | - | TOML | team.members[].model | - | - | 必須 | LLMモデル | ❌ |
| members[].system_instruction | str \| None | None | TOML | team.members[].system_instruction | - | - | オプション | システム指示 | ❌ |
| members[].temperature | float \| None | None | TOML | team.members[].temperature | - | - | オプション | Temperature | ❌ |
| members[].max_tokens | int | - | TOML | team.members[].max_tokens | - | - | 必須 | 最大トークン数 | ❌ |
| members[].timeout | int \| None | None | TOML | team.members[].timeout | - | - | オプション | タイムアウト | ❌ |
| members[].config | str \| None | None | TOML | team.members[].config | - | - | オプション | 参照形式パス（別TOMLファイルへの相対パス） | ❌ |

**設定例（TOML - インライン形式）**:
```toml
[team]
team_id = "research-team-01"
team_name = "Research Team"
max_concurrent_members = 20

[team.leader]
model = "openai:gpt-4o"
system_instruction = "You are coordinating a research team."
timeout_seconds = 300

[[team.members]]
name = "researcher"
type = "web_search"
tool_description = "Searches the web for information"
model = "google-gla:gemini-2.5-flash"
max_tokens = 4096
```

**設定例（TOML - 参照形式）**:
```toml
[team]
team_id = "research-team-01"
team_name = "Research Team"

[[team.members]]
config = "agents/researcher.toml"
tool_description = "Searches the web for information"

[[team.members]]
config = "agents/analyst.toml"
tool_description = "Analyzes research results"
```

---

## Evaluator設定

Evaluatorは複数のメトリクスを使用してAgent出力を評価します。

**LLMデフォルト設定**:

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| default_model | str | "google-gla:gemini-2.5-flash" | TOML/定数 | default_model | - | - | オプション | デフォルトLLMモデル | ✅ |
| temperature | float \| None | None | TOML/定数 | temperature | - | - | オプション | デフォルトtemperature（0.0-2.0、Noneの場合はモデルデフォルト） | ✅ |
| max_tokens | int \| None | None | TOML/定数 | max_tokens | - | - | オプション | デフォルトmax_tokens（> 0、Noneの場合はモデルデフォルト） | ❌ |
| max_retries | int | 3 | TOML/定数 | max_retries | - | - | オプション | デフォルトmax_retries（>= 0） | ✅ |
| timeout_seconds | int | 300 | TOML/定数 | timeout_seconds | - | - | オプション | HTTPタイムアウト（秒、>= 0） | ✅ |
| stop_sequences | list[str] \| None | None | TOML/定数 | stop_sequences | - | - | オプション | 生成を停止するシーケンスのリスト | ❌ |
| top_p | float \| None | None | TOML/定数 | top_p | - | - | オプション | Top-pサンプリングパラメータ（0.0-1.0、Noneの場合はモデルデフォルト） | ❌ |
| seed | int \| None | None | TOML/定数 | seed | - | - | オプション | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | ❌ |

**Metrics設定**:

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| metrics[].name | str | - | TOML | metrics[].name | - | - | 必須 | メトリクス名（例: ClarityCoherence、Coverage、Relevance） | ❌ |
| metrics[].weight | float \| None | None | TOML | metrics[].weight | - | - | オプション | メトリクスの重み（範囲: 0.0-1.0、全メトリクスの合計が1.0、Noneの場合は均等割当） | ❌ |
| metrics[].model | str \| None | None | TOML | metrics[].model | - | - | オプション | メトリクス固有のLLMモデル（Noneの場合はllm_default.modelを使用） | ❌ |
| metrics[].system_instruction | str \| None | None | TOML | metrics[].system_instruction | - | - | オプション | カスタムsystem_instruction（Noneの場合はメトリクスのデフォルトプロンプトを使用） | ❌ |
| metrics[].temperature | float \| None | None | TOML | metrics[].temperature | - | - | オプション | メトリクス固有のtemperature（Noneの場合はllm_default.temperatureを使用） | ❌ |
| metrics[].max_tokens | int \| None | None | TOML | metrics[].max_tokens | - | - | オプション | メトリクス固有のmax_tokens（Noneの場合はllm_default.max_tokensを使用） | ❌ |
| metrics[].max_retries | int \| None | None | TOML | metrics[].max_retries | - | - | オプション | メトリクス固有のmax_retries（Noneの場合はllm_default.max_retriesを使用） | ❌ |
| metrics[].timeout_seconds | int \| None | None | TOML | metrics[].timeout_seconds | - | - | オプション | メトリクス固有のHTTPタイムアウト（秒、>= 0、Noneの場合はllm_default.timeout_secondsを使用） | ❌ |
| metrics[].stop_sequences | list[str] \| None | None | TOML | metrics[].stop_sequences | - | - | オプション | メトリクス固有の生成停止シーケンス（Noneの場合はllm_default.stop_sequencesを使用） | ❌ |
| metrics[].top_p | float \| None | None | TOML | metrics[].top_p | - | - | オプション | メトリクス固有のTop-pサンプリング（0.0-1.0、Noneの場合はllm_default.top_pを使用） | ❌ |
| metrics[].seed | int \| None | None | TOML | metrics[].seed | - | - | オプション | メトリクス固有のランダムシード（Noneの場合はllm_default.seedを使用） | ❌ |

**設定例（TOML）**:
```toml
[llm_default]
model = "anthropic:claude-sonnet-4-5-20250929"
temperature = 0.0
max_tokens = 2000
max_retries = 3
timeout_seconds = 300
stop_sequences = ["END", "STOP"]
top_p = 0.9
seed = 42

[[metrics]]
name = "ClarityCoherence"
weight = 0.334

[[metrics]]
name = "Coverage"
weight = 0.333

[[metrics]]
name = "Relevance"
weight = 0.333
model = "openai:gpt-5"  # このメトリクスだけ異なるモデルを使用
```

---

## Judgment設定

JudgmentはLLM-as-a-Judgeによるラウンド継続判定機能を提供します。複数ラウンド実行時に、過去の提出物と評価スコアのトレンドを分析し、次のラウンドに進むべきかを判定します。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| model | str | "google-gla:gemini-2.5-flash" | TOML/定数 | model | MIXSEEK_JUDGMENT__MODEL | - | オプション | LLMモデル（例: google-gla:gemini-2.5-flash、anthropic:claude-sonnet-4-5） | ✅ |
| temperature | float | 0.0 | TOML/定数 | temperature | MIXSEEK_JUDGMENT__TEMPERATURE | - | オプション | Temperature（0.0-2.0、デフォルト: 0.0、決定論的判定） | ✅ |
| max_tokens | int \| None | None | TOML/定数 | max_tokens | MIXSEEK_JUDGMENT__MAX_TOKENS | - | オプション | 最大トークン数（> 0、Noneの場合はLLM側のデフォルト値） | ❌ |
| max_retries | int | 3 | TOML/定数 | max_retries | MIXSEEK_JUDGMENT__MAX_RETRIES | - | オプション | LLM API呼び出しの最大リトライ回数（>= 0） | ✅ |
| timeout_seconds | int | 60 | TOML/定数 | timeout_seconds | MIXSEEK_JUDGMENT__TIMEOUT_SECONDS | - | オプション | HTTPタイムアウト（秒、デフォルト: 60秒） | ✅ |
| stop_sequences | list[str] \| None | None | TOML/定数 | stop_sequences | MIXSEEK_JUDGMENT__STOP_SEQUENCES | - | オプション | 生成を停止するシーケンスのリスト | ❌ |
| top_p | float \| None | None | TOML/定数 | top_p | MIXSEEK_JUDGMENT__TOP_P | - | オプション | Top-pサンプリングパラメータ（0.0-1.0、Noneの場合はLLM側のデフォルト値） | ❌ |
| seed | int \| None | None | TOML/定数 | seed | MIXSEEK_JUDGMENT__SEED | - | オプション | ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート） | ❌ |
| system_instruction | str \| None | None | TOML/定数 | system_instruction | MIXSEEK_JUDGMENT__SYSTEM_INSTRUCTION | - | オプション | システム指示（Noneの場合はデフォルト指示を使用） | ❌ |

**デフォルトsystem_instruction**:

Judgment機能のデフォルトシステム指示は以下の通りです：

```
あなたは複数ラウンドにわたるチームの提出物の改善を分析する専門的な判定者です。

あなたのタスクは、以下の要素に基づいて、チームが次のラウンドに進むべきかを判定することです：
1. 過去の提出物の品質トレンド
2. 評価スコアの推移
3. さらなる改善の可能性

提出履歴を注意深く分析し、以下を提供してください：
- should_continue: 真偽値の判定（継続する場合はTrue、停止する場合はFalse）
- reasoning: あなたの判定の詳細な説明
- confidence_score: あなたの確信度（0.0-1.0）

以下の要素を考慮してください：
- スコアが一貫して改善している場合は、継続を推奨
- 提出物が収穫逓減を示している場合は、停止を推奨
- 直近のスコアが低くても、数ラウンド先での改善が見込まれる場合は、継続を推奨
```

**判定出力形式**:

Judgment機能はPydantic AIの構造化出力を使用し、以下の形式で判定結果を返します：

```python
class ImprovementJudgment(BaseModel):
    should_continue: bool  # 次のラウンドに進むべきか
    reasoning: str         # 判定の詳細な理由
    confidence_score: float  # 確信度（0.0-1.0）
```

**設定例（TOML）**:

```toml
# judgment.toml
model = "anthropic:claude-sonnet-4-5"
temperature = 0.0  # 決定論的判定
max_tokens = 1000
max_retries = 3
timeout_seconds = 60
system_instruction = """
あなたは改善判定の専門家です。
スコアのトレンドと提出物の品質を総合的に評価し、
次のラウンドに進むべきかを判定してください。
"""
```

**環境変数設定例**:

```bash
# 環境変数で設定
export MIXSEEK_JUDGMENT__MODEL="google-gla:gemini-2.5-flash"
export MIXSEEK_JUDGMENT__TEMPERATURE=0.0
export MIXSEEK_JUDGMENT__MAX_TOKENS=1000
export MIXSEEK_JUDGMENT__TIMEOUT_SECONDS=60
```

**Orchestratorとの統合**:

Judgment設定はOrchestratorから参照されます：

```toml
# orchestrator.toml
[orchestrator]
timeout_per_team_seconds = 600
judgment_config = "configs/judgment.toml"  # Judgment設定ファイルパス
max_rounds = 5  # 最大ラウンド数
min_rounds = 2  # LLM判定を開始する最小ラウンド数

[[orchestrator.teams]]
config = "configs/team.toml"
```

**使用シナリオ**:

1. **ラウンド1〜min_rounds**: 自動実行（Judgment判定なし）
2. **ラウンドmin_rounds+1以降**: 各ラウンド後にJudgment判定
   - `should_continue=True`: 次のラウンドを実行
   - `should_continue=False`: 実行を停止し、最良のラウンドを選択
3. **max_rounds到達**: 自動停止

**JudgmentClientの実装**:

JudgmentClientは以下の責務を持ちます：

- Pydantic AIによるLLM呼び出し（自動リトライ付き）
- 構造化出力（ImprovementJudgment）の取得
- エラーハンドリング（JudgmentAPIError）

プロンプト整形はRoundControllerがUserPromptBuilderで行います（FR-021準拠）。

**Article 9準拠**:

- すべてのLLMパラメータを明示的に設定可能
- デフォルト値はコード内定数として明示（暗黙的フォールバックなし）
- 環境変数、TOML、CLI引数による上書きをサポート

---

## Orchestrator設定

Orchestratorは複数のチームを並列実行し、最適な結果を選択します。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| timeout_per_team_seconds | int | - | TOML | orchestrator.timeout_per_team_seconds | - | - | 必須 | チーム単位タイムアウト（秒） | ❌ |
| evaluator_config | str \| None | None | TOML | orchestrator.evaluator_config | - | - | オプション | Evaluator設定ファイルパス（相対パスまたは絶対パス、未指定時は{workspace}/configs/evaluator.tomlまたはデフォルト値） | ❌ |
| judgment_config | str \| None | None | TOML | orchestrator.judgment_config | - | - | オプション | Judgment設定ファイルパス（相対パスまたは絶対パス、未指定時は{workspace}/configs/judgment.tomlまたはデフォルト値） | ❌ |
| teams[].config | Path | - | TOML | orchestrator.teams[].config | - | - | 必須 | チーム設定TOMLファイルパス（相対パスまたは絶対パス） | ❌ |
| judgment_timeout_seconds | int | 60 | TOML/定数 | orchestrator.judgment_timeout_seconds | MIXSEEK__JUDGMENT_TIMEOUT_SECONDS | - | オプション | 各ラウンドの評価判定タイムアウト（秒、> 0） | ✅ |

**設定例（TOML）**:
```toml
[orchestrator]
timeout_per_team_seconds = 600
evaluator_config = "configs/custom_evaluator.toml"  # オプション: カスタムEvaluator設定
judgment_config = "configs/judgment.toml"  # オプション: Judgment設定
judgment_timeout_seconds = 60  # 各ラウンドの判定タイムアウト

[[orchestrator.teams]]
config = "agents/team-research.toml"

[[orchestrator.teams]]
config = "agents/team-creative.toml"

[[orchestrator.teams]]
config = "agents/team-balanced.toml"
```

---

## CLI設定

mixseek CLIコマンドで使用可能な引数です。

### `mixseek team` コマンド

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| prompt | str | - | CLI | - | - | （位置引数） | 必須 | ユーザプロンプト | ❌ |
| config | Path | - | CLI | - | - | --config, -c | 必須 | チーム設定ファイルパス | ❌ |
| output_format | str | "text" | CLI/定数 | - | - | --output-format, -f | オプション | 出力形式（json/text） | ✅ |
| save_db | bool | False | CLI/定数 | - | - | --save-db | オプション | DuckDB保存フラグ | ✅ |
| evaluate | bool | False | CLI/定数 | - | - | --evaluate | オプション | 評価実行フラグ | ✅ |
| workspace | Path \| None | None | CLI/ENV/定数 | - | MIXSEEK_WORKSPACE | --workspace, -w | オプション | ワークスペースパス（未指定時はMIXSEEK_WORKSPACE環境変数を使用） | ❌ |
| evaluate_config | Path \| None | None | CLI | - | - | --evaluate-config, -e | オプション | 評価設定ファイルパス | ❌ |
| verbose | bool | False | CLI/定数 | - | - | --verbose, -v | オプション | 詳細出力フラグ | ✅ |
| logfire | bool | False | CLI/定数 | - | - | --logfire | オプション | Logfire有効化（fullモード） | ✅ |
| logfire_metadata | bool | False | CLI/定数 | - | - | --logfire-metadata | オプション | Logfire有効化（metadataモード） | ✅ |
| logfire_http | bool | False | CLI/定数 | - | - | --logfire-http | オプション | Logfire有効化（full + HTTPキャプチャ） | ✅ |

**使用例**:
```bash
# 基本的な使用
mixseek team "タスクの説明" --config team.toml

# 評価付き実行
mixseek team "タスクの説明" --config team.toml --evaluate --evaluate-config evaluator.toml

# DuckDB保存
mixseek team "タスクの説明" --config team.toml --save-db --workspace /path/to/workspace

# JSON出力
mixseek team "タスクの説明" --config team.toml --output-format json

# Logfire観測
mixseek team "タスクの説明" --config team.toml --logfire
```

### `mixseek exec` コマンド

**注意**: `mixseek exec` コマンドは `mixseek team` と類似の引数を使用しますが、リーダーボード機能のため **DuckDB への保存が必須** であり、`--save-db` オプションは存在しません（常に保存されます）。

### `mixseek ui` コマンド

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| port | int | 8501 | CLI/定数 | - | - | --port | オプション | Streamlitポート番号 | ✅ |
| workspace | Path \| None | None | CLI/ENV | - | MIXSEEK_WORKSPACE | --workspace, -w | オプション | ワークスペースパス | ❌ |

**使用例**:
```bash
# デフォルトポート（8501）で起動
mixseek ui

# カスタムポート
mixseek ui --port 8080

# ワークスペース指定
mixseek ui --workspace /path/to/workspace
```

---

## UI (Streamlit) 設定

StreamlitベースのMixSeek UIの設定です。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| workspace | Path | - | ENV/CLI | - | MIXSEEK_WORKSPACE | --workspace, -w | 必須 | ワークスペースパス（設定ファイル、DB、ログの起点） | ❌ |

**起動方法**:
```bash
# 環境変数で設定
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek ui

# CLI引数で上書き
mixseek ui --workspace /path/to/workspace
```

---

## ログ/観測性設定

ログ出力とLogfire観測性の設定です。

### 基本ログ設定

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| MIXSEEK_WORKSPACE | str | - | ENV | - | MIXSEEK_WORKSPACE | - | 必須（ファイルログ有効時） | ワークスペースパス（ログディレクトリ: `$MIXSEEK_WORKSPACE/logs/`） | ❌ |

### Logfire設定

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| LOGFIRE_ENABLED | str | - | ENV | logfire.enabled | LOGFIRE_ENABLED | - | オプション | Logfire有効化フラグ（"1"で有効） | ❌ |
| LOGFIRE_PRIVACY_MODE | str | "metadata_only" | ENV/TOML/定数 | logfire.privacy_mode | LOGFIRE_PRIVACY_MODE | - | オプション | プライバシーモード（full/metadata_only/disabled） | ✅ |
| LOGFIRE_CAPTURE_HTTP | str | - | ENV/TOML | logfire.capture_http | LOGFIRE_CAPTURE_HTTP | - | オプション | HTTPキャプチャフラグ（"1"で有効） | ❌ |
| LOGFIRE_PROJECT | str | - | ENV/TOML | logfire.project_name | LOGFIRE_PROJECT | - | オプション | Logfireプロジェクト名 | ❌ |
| LOGFIRE_SEND_TO_LOGFIRE | str | "1" | ENV/TOML/定数 | logfire.send_to_logfire | LOGFIRE_SEND_TO_LOGFIRE | - | オプション | Logfireクラウド送信フラグ（"1"で有効） | ✅ |

**使用例**:
```bash
# 環境変数でLogfire有効化
export LOGFIRE_ENABLED=1
export LOGFIRE_PRIVACY_MODE=full
export LOGFIRE_CAPTURE_HTTP=1
mixseek team "タスク" --config team.toml

# CLI引数でLogfire有効化
mixseek team "タスク" --config team.toml --logfire
mixseek team "タスク" --config team.toml --logfire-metadata
mixseek team "タスク" --config team.toml --logfire-http
```

---

## ストレージ設定

DuckDBストレージの設定です。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| db_path | Path \| None | None | プログラマティック/ENV | - | MIXSEEK_WORKSPACE | - | オプション | DuckDBファイルパス（Noneの場合は`$MIXSEEK_WORKSPACE/mixseek.db`を使用） | ❌ |

**注意事項**:
- `db_path`が`None`の場合、`$MIXSEEK_WORKSPACE`環境変数が必須
- `$MIXSEEK_WORKSPACE`未設定時は`EnvironmentError`が発生（Article 9準拠）

---

## 認証設定

AI APIの認証設定（環境変数のみ）です。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| GOOGLE_API_KEY | str | - | ENV | - | GOOGLE_API_KEY | - | 必須（Google AI使用時） | Google AI APIキー | ❌ |
| GOOGLE_APPLICATION_CREDENTIALS | str | - | ENV | - | GOOGLE_APPLICATION_CREDENTIALS | - | 必須（Vertex AI使用時） | GCPサービスアカウントJSONファイルパス | ❌ |
| GOOGLE_GENAI_USE_VERTEXAI | str | - | ENV | - | GOOGLE_GENAI_USE_VERTEXAI | - | オプション | Vertex AI使用フラグ（"true"/"1"/"yes"で有効） | ❌ |
| ANTHROPIC_API_KEY | str | - | ENV | - | ANTHROPIC_API_KEY | - | 必須（Anthropic使用時） | Anthropic APIキー | ❌ |
| OPENAI_API_KEY | str | - | ENV | - | OPENAI_API_KEY | - | 必須（OpenAI使用時） | OpenAI APIキー | ❌ |
| GROK_API_KEY | str | - | ENV | - | GROK_API_KEY | - | 必須（Grok使用時） | xAI Grok APIキー | ❌ |

**設定例**:
```bash
# Google AI
export GOOGLE_API_KEY=your_api_key_here

# Vertex AI
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GOOGLE_GENAI_USE_VERTEXAI=true

# Anthropic
export ANTHROPIC_API_KEY=your_api_key_here

# OpenAI
export OPENAI_API_KEY=your_api_key_here

# Grok (xAI)
export GROK_API_KEY=your_api_key_here
```

**Grokモデルプレフィックス**:

| プレフィックス | 用途 | 例 |
|--------------|------|-----|
| `grok:` | 基本的なチャット機能 | `grok:grok-2-1212` |
| `grok-responses:` | ツール使用（Web検索等） | `grok-responses:grok-4-fast` |

Web検索機能を使用する場合は`grok-responses:`プレフィックスを使用してください。xAIのResponses APIを通じてネイティブWeb検索ツールが利用可能になります。

**セキュリティ注意事項**:
- APIキーは環境変数または`.env`ファイルで管理
- `.env`ファイルは`.gitignore`に追加（コミット禁止）
- 本番環境ではシークレット管理サービス（AWS Secrets Manager、GCP Secret Manager等）の使用を推奨

---

## 環境変数設定（MixSeek固有）

MixSeek固有の環境変数です。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| MIXSEEK_DEVELOPMENT_MODE | bool | False | ENV/定数 | - | MIXSEEK_DEVELOPMENT_MODE | - | オプション | 開発モードフラグ（追加のデバッグ情報を出力） | ✅ |
| MIXSEEK_LOG_LEVEL | str | "INFO" | ENV/定数 | - | MIXSEEK_LOG_LEVEL | - | オプション | ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） | ✅ |
| MIXSEEK_CLI_OUTPUT_FORMAT | str | "structured" | ENV/定数 | - | MIXSEEK_CLI_OUTPUT_FORMAT | - | オプション | CLI出力形式（json/text/structured） | ✅ |
| MIXSEEK_GOOGLE_GENAI_USE_VERTEXAI | bool | False | ENV/定数 | - | MIXSEEK_GOOGLE_GENAI_USE_VERTEXAI | - | オプション | Vertex AI使用フラグ | ✅ |

---

## 定数設定

コード内で定義されている定数です（Article 9違反の可能性あり）。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| DEFAULT_PROJECT_NAME | str | "mixseek-project" | 定数 | - | - | - | - | デフォルトプロジェクト名 | ✅ |
| WORKSPACE_ENV_VAR | str | "MIXSEEK_WORKSPACE" | 定数 | - | - | - | - | ワークスペース環境変数名 | ✅ |
| DEFAULT_LOG_FORMAT | str | "%(asctime)s - %(name)s - %(levelname)s - %(message)s" | 定数 | - | - | - | - | ログフォーマット | ✅ |
| DEFAULT_LOG_LEVEL | str | "INFO" | 定数 | - | - | - | - | デフォルトログレベル | ✅ |
| MAX_TOKENS_LOWER_BOUND | int | 1 | 定数 | - | - | - | - | max_tokens下限 | ✅ |
| MAX_TOKENS_UPPER_BOUND | int | 65536 | 定数 | - | - | - | - | max_tokens上限 | ✅ |
| MAX_TOKENS_DEFAULT | int | 2048 | 定数 | - | - | - | - | max_tokensデフォルト値 | ✅ |

---

## Validation設定

モデル検証用の設定です。

| 設定項目名 | データ型 | デフォルト値 | 設定方法 | TOMLキー | 環境変数名 | CLI引数名 | 必須/オプション | 説明 | Article 9違反 |
|-----------|---------|------------|---------|---------|-----------|----------|--------------|------|-------------|
| MIXSEEK_COST_LIMIT_USD | Decimal | Decimal("1.00") | ENV/定数 | - | MIXSEEK_COST_LIMIT_USD | - | オプション | 累積コスト上限（USD） | ✅ |
| MIXSEEK_MAX_RETRIES | int | 3 | ENV/定数 | - | MIXSEEK_MAX_RETRIES | - | オプション | 最大リトライ回数 | ✅ |
| MIXSEEK_RETRY_BASE_DELAY | float | 1.0 | ENV/定数 | - | MIXSEEK_RETRY_BASE_DELAY | - | オプション | リトライ基本遅延（秒） | ✅ |
| MIXSEEK_VALIDATION_TIMEOUT | int | 120 | ENV/定数 | - | MIXSEEK_VALIDATION_TIMEOUT | - | オプション | 検証タイムアウト（秒） | ✅ |
| MIXSEEK_MAX_CONCURRENT_VALIDATIONS | int | 5 | ENV/定数 | - | MIXSEEK_MAX_CONCURRENT_VALIDATIONS | - | オプション | 最大並列検証数 | ✅ |

---

## Article 9違反のサマリー

### ✅ Article 9違反が確認された設定値

以下の設定値はハードコードされたデフォルト値を持ち、**Article 9（Data Accuracy Mandate）に違反**しています：

#### 高優先度（即座に修正が必要）

1. **LLMモデル指定**:
   - `Leader.model = "openai:gpt-4o"`
   - `Member.model = "google-gla:gemini-2.5-flash-lite"`
   - `Evaluator.llm_default.model = "anthropic:claude-sonnet-4-5-20250929"`

2. **タイムアウト設定**:
   - `Leader.timeout_seconds = 300`
   - `Member.timeout_seconds = 300`

3. **トークン制限**:
   - `Member.max_tokens = 2048`

#### 中優先度（Phase 2で修正）

4. **リトライ設定**:
   - `Member.max_retries = 3`
   - `Evaluator.llm_default.max_retries = 3`

5. **ログ設定**:
   - `LOGFIRE_PRIVACY_MODE = "metadata_only"`
   - `LOGFIRE_SEND_TO_LOGFIRE = "1"`

6. **CLI設定**:
   - `output = "text"`
   - `save_db = False` (`team` コマンドのみ、`exec` は常に True)
   - `evaluate = False`
   - `verbose = False`
   - `port = 8501`

#### 低優先度（Phase 3で修正、または許容）

7. **Team設定**:
   - `max_concurrent_members = 15`

8. **Tool設定**:
   - `web_search.max_results = 10`
   - `web_search.timeout = 30`
   - `code_execution.expected_min_timeout_seconds = 300`

9. **Usage Limits**:
   - `max_requests_per_hour = 100`

10. **Validation設定**:
    - すべてのデフォルト値

11. **定数**:
    - すべての定数（`DEFAULT_PROJECT_NAME`, `DEFAULT_LOG_FORMAT`等）

### Article 9 コンプライアンス（051-configuration後）

**Phase 11 実装完了により、Article 9（Data Accuracy Mandate）への準拠が大幅に改善されました:**

#### 修正完了（Phase 11で対応）

✅ **Configuration Manager 統一管理**:
- すべての設定値が Configuration Manager 経由で管理
- Pydantic スキーマから明示的にフィールド情報を抽出
- 暗黙的デフォルト値の完全排除
- 環境変数、TOML、CLI から明示的に読み込み

✅ **セキュリティ強化**:
- パストラバーサル攻撃防止
- エラーメッセージサニタイゼーション
- 情報漏洩防止

✅ **テスト検証**:
- Edge case テスト (17 tests)
- Security テスト (15 tests)
- Quickstart シナリオテスト (12 tests)
- 総計 178 テスト PASS

#### Article 9 違反箇所の推移

| フェーズ | 違反箇所 | 準拠箇所 | 進捗 |
|---------|---------|---------|------|
| **初期状態** | ~80箇所 | ~40箇所 | 33% 準拠 |
| **Phase 11後** | **< 10箇所** | **> 110箇所** | **>90% 準拠** |

SC-008 要件：**成功基準を達成** ✅

### 推奨される修正アプローチ

1. **Phase 1（Week 1-2）**: 高優先度の修正
   - LLMモデル指定を環境変数/TOMLから読み込み
   - タイムアウト、トークン制限を設定可能に

2. **Phase 2（Week 3-4）**: 中優先度の修正
   - リトライ設定、ログ設定を環境変数/TOMLから読み込み

3. **Phase 3（Week 5+）**: 低優先度の修正
   - 残りのデフォルト値を環境変数/TOMLから読み込み
   - Configuration Managerの導入

詳細は以下を参照:
- `plans/configuration-management-deep-analysis.md`
- `plans/configuration-management-scope-limitations.md`

---

## Configuration Manager

Configuration Managerは統一設定管理システムです。詳細な使い方は [設定管理ガイド](configuration-guide.md) を参照してください。

### 設定スキーマ一覧

| スキーマ名 | TOMLセクション | 環境変数プレフィックス |
|-----------|---------------|-------------------|
| OrchestratorSettings | `[orchestrator]` | `MIXSEEK_` |
| LeaderAgentSettings | `[leader]` | `MIXSEEK_LEADER__` |
| MemberAgentSettings | `[member]` | `MIXSEEK_MEMBER__` |
| EvaluatorSettings | `[evaluator]` | `MIXSEEK_EVALUATOR__` |
| TeamSettings | `[team]` | `MIXSEEK_TEAM__` |
| UISettings | `[ui]` | `MIXSEEK_UI__` |

### Article 9 準拠

Configuration Manager は Article 9 (Data Accuracy Mandate) に完全準拠しています。

---

## 関連ドキュメント

- [Configuration Management Deep Analysis](../plans/configuration-management-deep-analysis.md) - 設定管理の根本的再設計の提案
- [Configuration Management Scope & Limitations](../plans/configuration-management-scope-limitations.md) - 設定管理の管理範囲と限界
- [Constitution Article 9](../.specify/memory/constitution.md#article-9-data-accuracy-mandate) - Data Accuracy Mandate

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-10
**Maintainer**: mixseek-core team
