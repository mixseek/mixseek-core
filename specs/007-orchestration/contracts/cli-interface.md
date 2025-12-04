# CLI Interface Contract: mixseek exec

**Date**: 2025-11-05
**Spec**: [../spec.md](../spec.md)
**Data Model**: [../data-model.md](../data-model.md)

このドキュメントは、`mixseek exec`コマンドのCLIインターフェースを定義します。

## Command: mixseek exec

ユーザプロンプトを受け取り、複数チームを並列実行してSubmissionを返すコマンド。

### Syntax

```bash
mixseek exec <USER_PROMPT> [OPTIONS]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `USER_PROMPT` | `str` | Yes | ユーザプロンプト（引用符で囲む） |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config PATH` | `Path` | `workspace/configs/orchestrator.toml` | オーケストレータ設定TOMLファイルパス |
| `--timeout INT` | `int` | (configから取得) | チーム単位タイムアウト（秒） |
| `--workspace PATH` | `Path` | `$MIXSEEK_WORKSPACE` | ワークスペースパス |
| `--output FORMAT` | `str` | `text` | 出力フォーマット（`text`, `json`） |
| `--verbose` / `-v` | `bool` | `False` | 詳細ログ表示 |

### Examples

#### 基本的な使用方法

```bash
# 最もシンプルな実行
mixseek exec "最新のAI技術トレンドを調査してください"
```

#### カスタム設定ファイルを指定

```bash
mixseek exec "最新のAI技術トレンドを調査してください" \
  --config workspace/configs/my-orchestrator.toml
```

#### タイムアウトを指定

```bash
mixseek exec "最新のAI技術トレンドを調査してください" \
  --timeout 300
```

#### JSON出力

```bash
mixseek exec "最新のAI技術トレンドを調査してください" \
  --output-format json > result.json
```

#### 詳細ログ付き実行

```bash
mixseek exec "最新のAI技術トレンドを調査してください" \
  --verbose
```

### Output Format

#### text形式（デフォルト）

```
🚀 MixSeek Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Task: 最新のAI技術トレンドを調査してください

🔄 Running 2 teams in parallel...

✅ Team 1: Research Team (completed in 45.2s)
   Score: 0.92
   Feedback: 包括的な調査結果が提供されました。

✅ Team 2: Analysis Team (completed in 38.7s)
   Score: 0.88
   Feedback: 詳細な分析が行われました。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Best Result (Team 1: Research Team, Score: 0.92)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Submissionテキストがここに表示される]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Teams:      2
Completed Teams:  2
Failed Teams:     0
Execution Time:   45.2s

💾 Results saved to DuckDB
```

#### json形式

```json
{
  "task_id": "12345678-1234-1234-1234-123456789abc",
  "user_prompt": "最新のAI技術トレンドを調査してください",
  "team_results": [
    {
      "team_id": "team-001",
      "team_name": "Research Team",
      "round_number": 1,
      "submission_content": "[Submissionテキスト]",
      "evaluation_score": 0.92,
      "evaluation_feedback": "包括的な調査結果が提供されました。",
      "usage": {
        "input_tokens": 1500,
        "output_tokens": 800,
        "requests": 5
      },
      "execution_time_seconds": 45.2,
      "completed_at": "2025-11-05T12:34:56Z"
    },
    {
      "team_id": "team-002",
      "team_name": "Analysis Team",
      "round_number": 1,
      "submission_content": "[Submissionテキスト]",
      "evaluation_score": 0.88,
      "evaluation_feedback": "詳細な分析が行われました。",
      "usage": {
        "input_tokens": 1200,
        "output_tokens": 600,
        "requests": 4
      },
      "execution_time_seconds": 38.7,
      "completed_at": "2025-11-05T12:34:50Z"
    }
  ],
  "best_team_id": "team-001",
  "best_score": 0.92,
  "total_teams": 2,
  "completed_teams": 2,
  "failed_teams": 0,
  "total_execution_time_seconds": 45.2,
  "created_at": "2025-11-05T12:35:00Z"
}
```

### Exit Codes

| Code | Condition | Description |
|------|-----------|-------------|
| `0` | Success | 少なくとも1チームが正常に完了 |
| `1` | Error | 全チームが失敗、またはシステムエラー |
| `2` | Timeout | 全チームがタイムアウト |
| `3` | Invalid Config | 設定ファイルが不正 |

### Error Messages

#### 環境変数未設定

```
Error: MIXSEEK_WORKSPACE environment variable is not set.
Please set it: export MIXSEEK_WORKSPACE=/path/to/workspace
```

#### 設定ファイル不在

```
Error: Orchestrator config file not found: workspace/configs/orchestrator.toml
Please check the path or use --config option.
```

#### 全チーム失敗

```
Error: All teams failed to complete the task.

Team 1 (Research Team): TimeoutError - Execution exceeded 600 seconds
Team 2 (Analysis Team): Exception - Leader Agent failed

No valid results to display.
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MIXSEEK_WORKSPACE` | Yes | ワークスペースパス（DuckDB、設定ファイル等の保存先） |
| `GOOGLE_API_KEY` | Yes | Google AI APIキー（Leader Agent/Member Agentで使用） |
| `OPENAI_API_KEY` | Optional | OpenAI APIキー（OpenAIモデル使用時） |

### Implementation Location

- **ファイル**: `src/mixseek/cli/commands/exec.py`
- **登録**: `src/mixseek/cli/main.py`の`app.command()`で登録

### Implementation Signature

```python
# src/mixseek/cli/commands/exec.py
import typer
from pathlib import Path
from mixseek.orchestrator import Orchestrator, load_orchestrator_settings

def exec(
    user_prompt: str = typer.Argument(..., help="ユーザプロンプト"),
    config: Path = typer.Option(
        "workspace/configs/orchestrator.toml",
        "--config",
        help="オーケストレータ設定TOMLファイルパス",
    ),
    timeout: int | None = typer.Option(
        None,
        "--timeout",
        help="チーム単位タイムアウト（秒）",
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        help="ワークスペースパス（デフォルト: $MIXSEEK_WORKSPACE）",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        help="出力フォーマット（text/json）",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="詳細ログ表示",
    ),
) -> None:
    """ユーザプロンプトを複数チームで並列実行

    Note: exec コマンドではリーダーボード機能のため、常に DuckDB に保存されます。
    """
    # 実装...
```

### Contract Compliance

- **FR-010**: CLIインターフェース提供（`mixseek exec`コマンド） ✅
- **FR-005**: 全チーム完了後に完了通知と結果を表示 ✅
- **FR-007**: 実行中にチーム単位の状態を監視可能（`--verbose`オプション） ✅

### Testing Considerations

- **E2Eテスト**: `subprocess`で実際にコマンドを実行してテスト
- **出力検証**: text形式とjson形式の両方で出力をテスト
- **エラーケース**: 環境変数未設定、設定ファイル不在、全チーム失敗をテスト
- **タイムアウト**: 意図的にタイムアウトを発生させてエラーメッセージをテスト
