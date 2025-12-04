# MixSeek-Core Orchestrator - マルチチーム競合サンプル

このサンプルプロジェクトは、MixSeek-Core Orchestrator の基本的な使い方を示します。

## 📋 概要

**ユースケース**: 複数の異なる分析アプローチを持つチームが、同じテーマについて並列に分析・比較

### 実演内容

- **5チームの並列実行**: 異なる戦略を持つ5つのチームが同時に実行
- **異なるアプローチ**:
  - **チームA**: 論理的・構造的な分析を重視（temperature=0.3）
  - **チームB**: 洞察・創造的な視点を重視（temperature=0.8）
  - **Research Team**: Web検索 + 論理分析で信頼性重視（temperature=0.3）
  - **Creative Team**: Web検索 + データ分析で革新性重視（temperature=0.7）
  - **Balanced Team**: Web検索 + 論理分析 + データ分析で包括的アプローチ（temperature=0.5）
- **Member Agent機能**: Web Search、Logical Analyst、Data Analyst を組み合わせた複合的な分析
- **結果比較**: スコアとフィードバックの自動記録、最高スコアチームの自動選択

### 処理フロー

```
User Prompt (ユーザプロンプト)
        ↓
 ┌──────┴──────┐
 ↓             ↓
チームA       チームB
 ↓             ↓
提案生成       提案生成
 ↓             ↓
評価スコア    評価スコア
 ↓             ↓
 └──────┬──────┘
        ↓
   結果統合・表示
        ↓
   DuckDB記録
```

## 🚀 クイックスタート（3ステップ）

### ステップ1: ワークスペースの準備

```bash
# ワークスペースディレクトリを作成し、サンプルをコピー
mkdir -p workspaces
cp -rp examples/orchestrator-sample workspaces
```

**セットアップ後の構造**:
```
workspaces/orchestrator-sample/
├── mixseek.db           # DuckDB（実行時に自動作成）
├── configs/
│   ├── orchestrator.toml
│   └── agents/
│       ├── analyst-team-a.toml      # チームA: 論理的分析
│       ├── analyst-team-b.toml      # チームB: 創造的視点
│       ├── team-research.toml       # Research Team: Web検索 + 論理分析
│       ├── team-creative.toml       # Creative Team: Web検索 + データ分析
│       └── team-balanced.toml       # Balanced Team: 全方位アプローチ
└── sample-data/         # オプション
```

### ステップ2: 環境変数の設定

```bash
# ワークスペースパスを設定
export MIXSEEK_WORKSPACE=/app/workspaces/orchestrator-sample

# API キーを設定（いずれか1つ）
export GOOGLE_API_KEY="your-api-key"
# または
export OPENAI_API_KEY="your-api-key"
```

### ステップ3: 実行

```bash
mixseek exec "2025年の重要なAI関連法規制の動向と企業への影響を分析してください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

**出力例**:
```
🚀 MixSeek Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task: 2025年の重要なAI関連法規制の動向と企業への影響を分析してください

🔄 Orchestrator Configuration
  Workspace: /path/to/orchestrator-sample
  Config:    /path/to/orchestrator-sample/configs/orchestrator.toml
  Teams:     5 (team-a, team-b, team-research, team-creative, team-balanced)

⏱️  Execution starting...

✅ Team team-a: チームA (completed in 12.3s)
   Score: 0.85
   Feedback: 構造的で理解しやすい分析。ただし、リスク評価が軽視されている点が課題。

✅ Team team-b: チームB (completed in 14.1s)
   Score: 0.88
   Feedback: 創造的な視点が評価されました。リスク観点の統合で、より実用的な提案になっています。

✅ Team team-research: Research Team (completed in 18.5s)
   Score: 0.92
   Feedback: Web検索で最新情報を収集し、論理的に分析。信頼性の高い情報源を適切に引用しています。

✅ Team team-creative: Creative Team (completed in 16.7s)
   Score: 0.89
   Feedback: Web検索とデータ分析を組み合わせた革新的なアプローチ。具体的な数値データで裏付けされています。

✅ Team team-balanced: Balanced Team (completed in 20.2s)
   Score: 0.94
   Feedback: 包括的な分析。Web検索、論理分析、データ分析を統合し、多角的な視点を提供しています。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Best Result (Team team-balanced, Score: 0.94)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Balanced Teamの提案内容がここに表示...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Teams:      5
Completed Teams:  5
Failed Teams:     0
Execution Time:   45.8s

💾 Results saved to DuckDB
```

## 📊 実行結果の確認

### 標準出力（デフォルト）

上記のコマンドで実行すると、見出し付きでスコア、フィードバック、チーム比較が表示されます。

### JSON形式で確認

```bash
mixseek exec "2025年の重要なAI関連法規制の動向と企業への影響を分析してください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml \
  --output json | jq .
```

JSON形式で以下の情報が出力されます:
- `task_id`: タスク識別子
- `user_prompt`: ユーザプロンプト
- `team_results`: 各チームの詳細結果
  - `team_id`, `team_name`
  - `submission_content`: チームの提案
  - `evaluation_score`: 評価スコア（0.0-1.0）
  - `evaluation_feedback`: 評価フィードバック
  - `execution_time_seconds`: 実行時間
- `best_team_id`, `best_score`: 最高スコアチーム情報
- `total_execution_time_seconds`: 全体実行時間

### DuckDB で確認

```bash
# DuckDB CLIで結果を確認
duckdb $MIXSEEK_WORKSPACE/mixseek.db

# leader_board テーブルの確認
SELECT
  team_id,
  team_name,
  evaluation_score,
  evaluation_feedback
FROM leader_board
ORDER BY evaluation_score DESC;

# round_history テーブルの確認（メッセージ履歴）
SELECT
  team_id,
  round_number,
  COUNT(*) as message_count
FROM round_history
GROUP BY team_id, round_number;
```

## 📝 ファイル構成の説明

### `configs/orchestrator.toml`

**5チームの定義ファイル**

```toml
[orchestrator]
timeout_per_team_seconds = 600        # 各チームのタイムアウト

# 基本チーム（Member Agent なし）
[[orchestrator.teams]]
config = "configs/agents/analyst-team-a.toml"  # チームA: 論理的分析

[[orchestrator.teams]]
config = "configs/agents/analyst-team-b.toml"  # チームB: 創造的視点

# Web Search を含むチーム（Member Agent あり）
[[orchestrator.teams]]
config = "configs/agents/team-research.toml"   # Research Team: Web検索 + 論理分析

[[orchestrator.teams]]
config = "configs/agents/team-creative.toml"   # Creative Team: Web検索 + データ分析

[[orchestrator.teams]]
config = "configs/agents/team-balanced.toml"   # Balanced Team: Web検索 + 論理 + データ
```

**ポイント**:
- 相対パスは `$MIXSEEK_WORKSPACE` から解釈されます
- `timeout_per_team_seconds`: 長めに設定（LLM API呼び出しを考慮）
- 新しいチームを追加するには、`[[orchestrator.teams]]` セクションを追加
- Member Agent を使用すると、より専門的な分析が可能

### `configs/agents/analyst-team-a.toml`

**チームAの設定: 論理的分析重視**

```toml
[team]
team_id = "team-a"
team_name = "チームA: 論理的分析"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
system_instruction = """
あなたは論理的で構造的な分析を得意とする戦略コンサルタントです。
以下の手順で分析してください：
1. 主要なファクターを特定
2. 論理的な因果関係を構築
3. 根拠に基づいた結論を導出

回答は明確で段階的に説明してください。
"""
```

### `configs/agents/analyst-team-b.toml`

**チームBの設定: 創造的視点重視**

```toml
[team]
team_id = "team-b"
team_name = "チームB: 創造的視点"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.8
system_instruction = """
あなたは創造的な思考と新しい視点を得意とする戦略家です。
以下のアプローチで分析してください：
1. 非従来的な観点から状況を解釈
2. 潜在的な機会やリスクを探索
3. 革新的なソリューションを提案

創造性と実用性のバランスを取りながら回答してください。
"""
```

### `configs/agents/team-research.toml`

**Research Teamの設定: Web検索 + 論理分析**

```toml
[team]
team_id = "team-research"
team_name = "Research Team: 研究重視チーム"
max_concurrent_members = 5

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3  # 低温度で決定的・正確な判断
system_instruction = """
あなたは研究重視の Leader Agent です。
ユーザーのタスクを分析し、適切な Member Agent に委譲してください。

【利用可能な Member Agents】
1. web_search: 最新情報の収集、Web検索が必要な場合
2. logical_analyst: 論理的・構造的な分析が必要な場合

Agent Delegation 戦略:
- 最新情報が必要 → delegate_to_web_search
- 論理的分析が必要 → delegate_to_logical_analyst
"""

# Member Agent 1: Web Search Agent
[[team.members]]
agent_name = "web_search"
agent_type = "web_search"
tool_description = "Web検索で最新情報を収集します。市場動向、技術トレンド、統計データなど。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
max_tokens = 6144

[team.members.system_instruction]
text = "あなたはWeb検索に特化した研究エージェントです。信頼できる情報源を優先し、最新情報を正確に提供してください。"

[team.members.tool_settings.web_search]
max_results = 15
timeout = 60
include_raw_content = true

# Member Agent 2: Logical Analyst Agent
[[team.members]]
agent_name = "logical_analyst"
agent_type = "plain"
tool_description = "論理的・構造的な分析を実行します。因果関係の整理、フレームワーク適用。"
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.2
max_tokens = 4096

[team.members.system_instruction]
text = "あなたは論理的分析に特化したエージェントです。構造的に整理し、明確な結論を導出してください。"
```

**ポイント**:
- **Agent Delegation**: Leader Agent が LLM で判断し、必要な Member Agent のみを実行
- **Web Search Agent**: `agent_type = "web_search"` で Web 検索機能を有効化
- **tool_settings.web_search**: 検索結果の最大数、タイムアウト、生コンテンツ取得を設定
- **temperature 設定**: 低温度（0.2-0.3）で正確性・信頼性を重視

### `configs/agents/team-creative.toml` と `team-balanced.toml`

**Creative Team** と **Balanced Team** も同様の構造ですが、以下の違いがあります：

| チーム | Temperature | Member Agents | 特徴 |
|--------|-------------|---------------|------|
| Research | 0.3 | Web Search + Logical Analyst | 信頼性・正確性重視 |
| Creative | 0.7 | Web Search + Data Analyst | 創造性・革新性重視 |
| Balanced | 0.5 | Web Search + Logical + Data | 包括的・多角的アプローチ |

## 🔧 カスタマイズガイド

### 異なるテーマで実行

プロンプトを変更して実行するには、コマンドのプロンプト部分を変更します：

```bash
# 例: 別のテーマで実行
mixseek exec "ベンチャー企業がSaaS事業を立ち上げる際の成功要因を分析してください" \
  --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### チームのアプローチをカスタマイズ

`$MIXSEEK_WORKSPACE/configs/agents/analyst-team-*.toml` の `system_instruction` を編集：

```toml
system_instruction = """
あなたはマーケティング戦略の専門家です。
顧客セグメント、競争分析、機会特定に焦点を当てて分析してください。
"""
```

編集後、再度 `mixseek exec` を実行します。

### タイムアウト値を調整

`$MIXSEEK_WORKSPACE/configs/orchestrator.toml` で：

```toml
[orchestrator]
timeout_per_team_seconds = 300  # 短いテストなら300秒
```

編集後、再度 `mixseek exec` を実行します。

## 🐛 トラブルシューティング

### エラー: `MIXSEEK_WORKSPACE 環境変数が設定されていません`

**原因**: 環境変数が設定されていない

**解決**:
```bash
# 環境変数を設定
export MIXSEEK_WORKSPACE=/app/workspaces/orchestrator-sample

# 現在のシェルで確認
echo $MIXSEEK_WORKSPACE
```

### エラー: `ワークスペースが見つかりません`

**原因**: ワークスペースディレクトリが削除されたか、パスが誤っている

**解決**:
```bash
# ワークスペースが存在するか確認
ls -la $MIXSEEK_WORKSPACE

# 存在しない場合は、再度セットアップ
mkdir -p workspaces
cp -rp examples/orchestrator-sample workspaces
export MIXSEEK_WORKSPACE=/app/workspaces/orchestrator-sample
```

### エラー: `FileNotFoundError: configs/agents/analyst-team-a.toml`

**原因**: 設定ファイルパスが正しくない

**解決**:
```bash
# ワークスペース内の設定ファイルを確認
ls -la $MIXSEEK_WORKSPACE/configs/agents/

# orchestrator.toml の相対パスを確認
cat $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### エラー: `API キーが設定されていません`

**原因**: LLM API キーが設定されていない

**解決** (Google Gemini の場合):
```bash
export GOOGLE_API_KEY="your-api-key-here"
mixseek exec "..." --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

OpenAI の場合:
```bash
export OPENAI_API_KEY="your-api-key-here"
mixseek exec "..." --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### 実行が遅い・タイムアウト

**原因**: ネットワーク遅延またはLLM API が遅い

**対策**:
```bash
# Orchestratorレベルのタイムアウト値を増やす
nano $MIXSEEK_WORKSPACE/configs/orchestrator.toml
# timeout_per_team_seconds = 900 に変更

# 編集後、再実行
mixseek exec "..." --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### エラー: `httpx.ReadError` (ネットワーク読み取りエラー)

**原因**: HTTPタイムアウト（デフォルト5秒）が短すぎて、LLM APIの応答を待機中にタイムアウトする

**典型的なエラーメッセージ**:
```
Team team-b encountered transient network error (ReadError). Retrying (attempt 1/2)...
httpcore.ReadError
```

**対策**: Leader AgentのHTTPタイムアウトを延長

```toml
# $MIXSEEK_WORKSPACE/configs/agents/analyst-team-a.toml

[team.leader]
model = "google-gla:gemini-2.5-flash-lite"
temperature = 0.3
timeout_seconds = 300  # ← 追加（デフォルト: 300秒 / 5分）
```

**タイムアウト設定の推奨値**:
- **デフォルト**: 300秒（5分） - 通常の使用に適切
- **高温度設定時**: 600秒（10分） - `temperature=0.8`以上の創造的タスク
- **最小値**: 10秒 - 短いテストのみ
- **最大値**: 600秒 - システム制約

**注意**: `temperature`が高い（0.7以上）場合、LLM APIの応答生成時間が長くなるため、ReadErrorが発生しやすくなります。

## FAQ

### Q: 複数のワークスペースで並行実行したい？

```bash
# 2つ目のワークスペースを作成
mkdir -p workspaces/orchestrator-sample-2
cp -rp examples/orchestrator-sample/* workspaces/orchestrator-sample-2/

# 別のシェルタブで設定
export MIXSEEK_WORKSPACE=/app/workspaces/orchestrator-sample-2
export GOOGLE_API_KEY="your-api-key"
mixseek exec "..." --config $MIXSEEK_WORKSPACE/configs/orchestrator.toml
```

### Q: ワークスペースをリセットしたい？

```bash
# ワークスペースを削除
rm -rf $MIXSEEK_WORKSPACE

# 再度セットアップ
mkdir -p workspaces
cp -rp examples/orchestrator-sample workspaces
export MIXSEEK_WORKSPACE=/app/workspaces/orchestrator-sample
```

## 🎓 学習ポイント

このサンプルで学べること：

1. **Orchestratorの基本**
   - 複数チームの並列実行方式
   - タイムアウト管理
   - チーム間の独立性

2. **チーム設定の設計**
   - `system_instruction` による振る舞いの制御
   - 異なるアプローチの組み合わせ
   - `temperature` パラメータによる出力の多様性制御

3. **評価・比較**
   - LLM-as-a-Judge による自動評価
   - スコアベースの順位付け

4. **結果の永続化**
   - DuckDB への自動記録
   - JSON 出力による外部連携

5. **ワークスペース管理**
   - `$MIXSEEK_WORKSPACE` 環境変数による標準構造
   - 複数のワークスペースの並行管理

## 📚 次のステップ

このサンプルを理解した後：

1. **更に多くのチームを追加** → `configs/orchestrator.toml` を編集
2. **異なるLLMモデルを試す** → `model = "..."` を変更（OpenAI、Anthropic Claude など）
3. **独自のチーム定義を作成** → `configs/agents/` に新しいファイルを追加
4. **Member Agent のカスタマイズ** → `system_instruction` や `tool_settings` を調整
5. **本番環境への応用** → 設定をカスタマイズして実運用

### Member Agent の活用例

- **Web Search Agent**: 最新ニュース、市場動向、技術トレンド調査に活用
- **Logical Analyst Agent**: 戦略立案、リスク分析、意思決定支援に活用
- **Data Analyst Agent**: 数値データ分析、統計的検証、予測モデル構築に活用
- **複数 Agent の組み合わせ**: Balanced Team のように、複数の視点を統合した包括的な分析

## 🧹 クリーンアップ

ワークスペースを削除する場合：

```bash
# ワークスペースを削除
rm -rf $MIXSEEK_WORKSPACE

# または直接パスを指定
rm -rf workspaces/orchestrator-sample
```

## 📞 サポート

問題が発生した場合：

1. ワークスペースをリセット（上記の FAQ 参照）
2. 環境変数を再設定
3. このドキュメントの FAQ とトラブルシューティングを確認
4. リポジトリの Issue を確認

## 📄 関連ドキュメント

- [specs/007-orchestration/spec.md](../../specs/007-orchestration/spec.md): 仕様書
- [docs/orchestrator.md](../../docs/orchestrator.md): 詳細ドキュメント

---

**Happy Learning! 🚀**
