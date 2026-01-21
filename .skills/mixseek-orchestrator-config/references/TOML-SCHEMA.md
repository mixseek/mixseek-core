# Orchestrator Configuration TOML Schema

## 概要

オーケストレーター設定ファイル（orchestrator.toml）のスキーマ定義です。複数チームの並列実行とTUMIXトーナメントの設定を定義します。

## ファイル配置

- パス: `$MIXSEEK_WORKSPACE/orchestrator.toml`
- または: `$MIXSEEK_WORKSPACE/configs/orchestrator-<name>.toml`

## 必須フィールド

### [[orchestrator.teams]] セクション（1つ以上必須）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `config` | string | チーム設定ファイルへのパス（ワークスペースからの相対パス） |

## オプションフィールド

### [orchestrator] セクション

| フィールド | 型 | デフォルト | 範囲 | 説明 |
|-----------|-----|----------|------|------|
| `timeout_per_team_seconds` | integer | 300 | 10-3600 | チームごとのタイムアウト秒数 |
| `max_rounds` | integer | 5 | 1-10 | 最大ラウンド数 |
| `min_rounds` | integer | 2 | >=1 | 最小ラウンド数 |
| `submission_timeout_seconds` | integer | 300 | >0 | Submission生成のタイムアウト |
| `judgment_timeout_seconds` | integer | 60 | >0 | Judgment処理のタイムアウト |

## バリデーションルール

1. **ラウンド設定**: `min_rounds <= max_rounds`
2. **チーム数**: 1つ以上のチーム設定が必要
3. **チーム設定ファイル**: 指定されたパスにファイルが存在すること

```python
# バリデーション例
assert orchestrator.min_rounds <= orchestrator.max_rounds
assert len(orchestrator.teams) >= 1
for team in orchestrator.teams:
    assert os.path.exists(workspace / team.config)
```

## 完全な設定例

### 最小構成

```toml
[[orchestrator.teams]]
config = "configs/agents/team-a.toml"

[[orchestrator.teams]]
config = "configs/agents/team-b.toml"
```

### 標準構成

```toml
[orchestrator]
max_rounds = 5
min_rounds = 2
timeout_per_team_seconds = 600

[[orchestrator.teams]]
config = "configs/agents/team-web-research.toml"

[[orchestrator.teams]]
config = "configs/agents/team-analysis.toml"
```

### フル構成

```toml
[orchestrator]
# ラウンド設定
max_rounds = 5
min_rounds = 2

# タイムアウト設定
timeout_per_team_seconds = 900
submission_timeout_seconds = 600
judgment_timeout_seconds = 120

# 競合チーム設定
[[orchestrator.teams]]
config = "configs/agents/team-creative.toml"

[[orchestrator.teams]]
config = "configs/agents/team-analytical.toml"

[[orchestrator.teams]]
config = "configs/agents/team-practical.toml"
```

## TUMIX実行フロー

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Round N (min_rounds ~ max_rounds)   │    │
│  │                                                  │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │    │
│  │  │ Team A  │  │ Team B  │  │ Team C  │  ...    │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘         │    │
│  │       │            │            │               │    │
│  │       ▼            ▼            ▼               │    │
│  │  ┌─────────────────────────────────────────┐   │    │
│  │  │         Submissions (並列生成)           │   │    │
│  │  └─────────────────────────────────────────┘   │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │  ┌─────────────────────────────────────────┐   │    │
│  │  │         Evaluator (スコアリング)         │   │    │
│  │  └─────────────────────────────────────────┘   │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │  ┌─────────────────────────────────────────┐   │    │
│  │  │         Judgment (最終判定)              │   │    │
│  │  └─────────────────────────────────────────┘   │    │
│  │                      │                          │    │
│  │                      ▼                          │    │
│  │              Round Winner                       │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                         ▼                                │
│                  Final Winner                            │
└─────────────────────────────────────────────────────────┘
```

## 関連設定ファイル

### 評価設定（evaluator.toml）

```toml
# $MIXSEEK_WORKSPACE/configs/evaluators/evaluator.toml
default_model = "google-gla:gemini-2.5-pro"

[[metrics]]
name = "ClarityCoherence"
weight = 0.34

[[metrics]]
name = "Coverage"
weight = 0.33

[[metrics]]
name = "Relevance"
weight = 0.33
```

### 判定設定（judgment.toml）

```toml
# $MIXSEEK_WORKSPACE/configs/judgment/judgment.toml
model = "google-gla:gemini-2.5-pro"
temperature = 0.0
```

## パス解決

チーム設定ファイルのパスは `$MIXSEEK_WORKSPACE` からの相対パスで指定します:

```toml
# 正しい例
[[orchestrator.teams]]
config = "configs/agents/team-a.toml"

# 誤った例（絶対パス）
[[orchestrator.teams]]
config = "/home/user/workspace/configs/agents/team-a.toml"  # ❌
```

## トラブルシューティング

### チーム設定が見つからない

```
Error: Team config not found
```

- ワークスペースパスを確認: `echo $MIXSEEK_WORKSPACE`
- ファイルの存在を確認: `ls $MIXSEEK_WORKSPACE/configs/agents/`
- パスが相対パスであることを確認

### ラウンド設定エラー

```
Error: min_rounds > max_rounds
```

- `min_rounds`を`max_rounds`以下に設定

### タイムアウト値エラー

```
Error: timeout_per_team_seconds must be between 10 and 3600
```

- 値を10-3600の範囲内に設定
