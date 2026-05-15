# 高度な機能

このドキュメントでは、MixSeek-Coreの高度な機能と設定オプションについて説明します。

## system_promptとの併用

### 概要

MixSeek-Coreでは、`system_instruction`（Pydantic AIの`instructions`）を主要な指示として使用しますが、
特殊なケースでは`system_prompt`を併用することができます。

### system_promptの動作

Pydantic AIの`system_prompt`は、メッセージ履歴に保持され、エージェント間で引き継がれます。
これにより、以下のようなケースで有用です：

- **共有世界観/ルール**: 複数のターンやエージェント間で一貫したルールを適用
- **履歴継続**: 過去の会話コンテキストを維持したい場合

### 併用例: Leader Agent

```toml
[team.leader]
# 主要な指示（毎回再評価）
system_instruction = """
あなたは研究チームのリーダーエージェントです。
タスクを分析し、適切なMember Agentを選択してください。
"""

# 共有ルール（履歴保持）
system_prompt = """
常に日本語で回答してください。
回答は簡潔かつ具体的にしてください。
"""

model = "google-gla:gemini-2.5-flash-lite"
```

### 併用例: Member Agent

```toml
[agent]
name = "analyst"
type = "plain"

# 共有ルール（履歴保持）
system_prompt = "常に日本語で回答してください。"

[agent.system_instruction]
text = """
あなたはデータ分析の専門家です。
...
"""
```

### 注意事項

1. **ほとんどのケースでは不要**: `system_instruction`のみで十分です
2. **履歴肥大化**: `system_prompt`は履歴に蓄積されるため、トークン消費に注意
3. **動的コンテキスト**: コンテキストが変わる場合は`system_instruction`を使用

### いつ使うべきか

| ケース | 推奨設定 | 理由 |
|-------|---------|------|
| 通常のAgent | `system_instruction`のみ | シンプルで十分 |
| 言語指定など共通ルール | `system_instruction` + `system_prompt` | 履歴保持が有用 |
| マルチターン会話 | `system_instruction` + `system_prompt` | コンテキスト維持 |

参考: `references/system-prompt-vs-instructions.md`

## pydantic-ai ModelSettings の透過設定 (`model_settings` / `google_model_settings`)

### 概要

LLM Provider 側で頻繁に追加される設定（Gemini の Thinking、Anthropic の interleaved thinking、
OpenAI の reasoning_effort 等）に追従するため、各エージェント設定 TOML から pydantic-ai の
`ModelSettings` / `GoogleModelSettings` (`TypedDict`) に **dict を素通し** できる経路を提供します。

- mixseek-core 側では中身を検証しません（pydantic-ai が `TypedDict` を採用した設計思想に合わせる）。
- 値のキーやフォーマット誤りは Provider API 呼び出し時のエラーで顕在化します。
- 個別フィールド (`temperature`, `max_tokens`, `top_p`, `seed`, `stop_sequences`, `timeout_seconds`)
  が両方設定された場合は**個別フィールドが優先**されます。

### 対応エージェント

`leader` / `member` / `evaluator` (`llm_default` および各 `metrics`) / `judgment`。
プロンプトビルダーは LLM 呼び出しを持たないため対象外です。

### Gemini の Thinking を有効化する例

```toml
[team.leader]
model = "google-gla:gemini-2.5-pro"

[team.leader.google_model_settings]
google_thinking_config = { thinking_level = "HIGH", include_thoughts = true }
```

### Provider 共通設定の例

```toml
[team.leader]
model = "openai:gpt-4o"

[team.leader.model_settings]
parallel_tool_calls = true
extra_headers = { "x-trace-id" = "..." }
```

### 注意事項

- `google_model_settings` は **Google モデル** (`google-gla:` / `google-vertex:`) のときのみ適用されます。
  他 Provider で指定すると警告ログが出て無視されます。
- 設定の中身は pydantic-ai のフィールド名をそのまま使用してください。
  詳細は [pydantic-ai Thinking ドキュメント](https://pydantic.dev/docs/ai/advanced-features/thinking/)
  および各 Provider 固有 ModelSettings のリファレンスを参照してください。
