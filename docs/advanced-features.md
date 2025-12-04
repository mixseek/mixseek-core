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
