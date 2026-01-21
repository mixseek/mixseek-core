# Member Agent Types Reference

## 概要

MixSeek-CoreのMember Agentタイプの詳細説明と使用例です。

## タイプ一覧

### 1. `plain` - 基本テキスト生成

**説明**: 最もシンプルなエージェントタイプ。追加ツールなしでテキスト生成のみを行います。

**用途**:
- テキストの要約・分析
- 文章の生成・編集
- 質問への回答
- データの解釈

**推奨モデル**:
- `google-gla:gemini-2.5-flash`（高速）
- `google-gla:gemini-2.5-pro`（高品質）

**設定例**:
```toml
[[team.members]]
agent_name = "summarizer"
agent_type = "plain"
tool_description = "テキストを要約し、重要なポイントを抽出します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたは要約の専門家です。
提供されたテキストを簡潔かつ正確に要約してください。
重要なポイントを箇条書きで整理してください。
"""
temperature = 0.2
```

### 2. `web_search` - Web検索機能付き

**説明**: Web検索ツールを持つエージェント。最新情報の取得やリサーチタスクに適しています。

**用途**:
- 最新ニュースの取得
- 特定トピックの調査
- 事実確認
- 市場調査

**推奨モデル**:
- `google-gla:gemini-2.5-flash`（Google検索統合）
- `grok:grok-4-fast`（Grok Web Search内蔵）

**設定例**:
```toml
[[team.members]]
agent_name = "web_researcher"
agent_type = "web_search"
tool_description = "Web検索を実行し、最新の情報を取得します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたはWeb検索の専門家です。

検索を行う際は以下のガイドラインに従ってください:
1. 信頼性の高い情報源を優先
2. 最新の情報を取得
3. 複数の情報源で事実確認
4. 出典URLを必ず含める
"""
temperature = 0.2
```

### 3. `code_execution` - コード実行機能付き

**説明**: Pythonコードを実行できるエージェント。計算、データ処理、スクリプト実行に適しています。

**用途**:
- 数値計算
- データ処理・変換
- グラフ・チャート生成
- ファイル操作
- API呼び出し

**推奨モデル**:
- `anthropic:claude-sonnet-4-5-20250929`（code_execution完全対応）
- `anthropic:claude-haiku-4-5`（高速、code_execution対応）

**注意**: Google/OpenAI系モデルはcode_execution非対応（`plain_compatible`のみ）

**設定例**:
```toml
[[team.members]]
agent_name = "python_coder"
agent_type = "code_execution"
tool_description = "Pythonコードを実行して計算やデータ処理を行います"
model = "anthropic:claude-sonnet-4-5-20250929"
system_instruction = """
あなたはPythonプログラマーです。

コード作成時のガイドライン:
1. 安全で効率的なコードを書く
2. エラーハンドリングを含める
3. 結果を明確に出力する
4. 必要なライブラリをインポートする

使用可能な主なライブラリ:
- pandas, numpy (データ処理)
- matplotlib, plotly (可視化)
- requests (API呼び出し)
"""
temperature = 0.0
timeout_seconds = 120
```

### 4. `web_fetch` - Webフェッチ機能付き

**説明**: 特定URLからコンテンツを取得するエージェント。既知のURLからのデータ取得に適しています。

**用途**:
- 特定ページのスクレイピング
- API呼び出し（認証不要）
- RSS/フィード取得
- ドキュメント取得

**推奨モデル**:
- `google-gla:gemini-2.5-flash`
- `anthropic:claude-haiku-4-5`

**設定例**:
```toml
[[team.members]]
agent_name = "page_fetcher"
agent_type = "web_fetch"
tool_description = "指定されたURLからWebページの内容を取得します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたはWebコンテンツ取得の専門家です。

取得時のガイドライン:
1. 指定されたURLから正確にコンテンツを取得
2. HTMLから必要な情報を抽出
3. 構造化された形式で結果を返す
4. エラー時は適切なメッセージを返す
"""
temperature = 0.1
```

### 5. `custom` - カスタムプラグイン

**説明**: 独自のツールやプラグインを統合するエージェント。MixSeekプラグインシステムと連携します。

**用途**:
- 社内システムとの連携
- 独自APIの呼び出し
- 特殊なツール統合
- 外部サービス連携

**注意**: カスタムプラグインの実装が必要です。

**設定例**:
```toml
[[team.members]]
agent_name = "slack_agent"
agent_type = "custom"
tool_description = "Slackにメッセージを送信します"
model = "google-gla:gemini-2.5-flash"
system_instruction = """
あなたはSlack連携エージェントです。
指示に従ってSlackチャンネルにメッセージを送信してください。
"""
# カスタムプラグイン設定は別途必要
```

## タイプ選択ガイド

### 用途別推奨

| タスク | 推奨タイプ | 理由 |
|--------|-----------|------|
| テキスト要約 | `plain` | 追加ツール不要 |
| 最新ニュース取得 | `web_search` | リアルタイム情報が必要 |
| データ計算 | `code_execution` | 正確な計算が必要 |
| 特定ページ分析 | `web_fetch` | URLが既知 |
| 社内システム連携 | `custom` | 独自統合が必要 |

### 複合タスクの構成例

**リサーチ＆分析チーム**:
```
- web_researcher (web_search): 情報収集
- analyst (plain): 情報分析
- summarizer (plain): 要約作成
```

**データ処理チーム**:
```
- data_fetcher (web_fetch): データ取得
- processor (code_execution): データ処理
- reporter (plain): レポート作成
```

## モデル互換性マトリックス

| タイプ | Google | Anthropic | OpenAI | Grok |
|--------|--------|-----------|--------|------|
| `plain` | ✓ | ✓ | ✓ | ✓ |
| `web_search` | ✓ | ✓ | ✓ | ✓ |
| `code_execution` | ✗ | ✓ | ✗ | ✗ |
| `web_fetch` | ✓ | ✓ | ✓ | ✓ |
| `custom` | ✓ | ✓ | ✓ | ✓ |

**注意**: `code_execution`はAnthropicモデルのみ完全対応
