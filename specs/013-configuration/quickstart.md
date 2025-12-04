# Quickstart: Configuration Manager

**Feature**: 051-configuration
**Last Updated**: 2025-11-11

このガイドでは、Pydantic Settings based Configuration Managerの基本的な使い方を学びます。

## Prerequisites

### 必須パッケージ

- Python 3.13.9
- uv (パッケージマネージャー)

### 必須ライブラリ

Configuration Manager機能を使用するために、以下のライブラリが必要です：

```bash
# 依存関係はpyproject.tomlで定義済み
pydantic>=2.12
pydantic-settings>=2.12
typer  # CLI統合用
```

## Installation

### 依存関係のインストール

```bash
# すべての依存関係をインストール
uv sync

# 開発用の依存関係も含める場合
uv sync --group dev
```

## Basic Usage

### 1. TOMLファイルの作成

設定ファイル `config.toml` を作成します：

```toml
# config.toml
workspace_path = "/path/to/workspace"

[leader]
model = "openai:gpt-4o"
timeout_seconds = 300
temperature = 0.7

[member]
model = "anthropic:claude-sonnet-4-5"
timeout_seconds = 180
```

### 2. 環境変数の設定

環境変数で設定を上書きできます：

```bash
# 必須設定
export MIXSEEK_WORKSPACE_PATH="/path/to/workspace"

# Leader Agent設定
export MIXSEEK_LEADER__MODEL="openai:gpt-5"
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600

# Member Agent設定
export MIXSEEK_MEMBER__MODEL="anthropic:claude-opus-4"
```

**注意**: ネスト構造は `__`（アンダースコア2つ）で区切ります。

### 3. Configuration Managerの使用

Pythonコードで設定を読み込みます：

```python
from pathlib import Path
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import LeaderAgentSettings

# ConfigurationManagerの初期化
manager = ConfigurationManager(
    workspace=Path("/path/to/workspace"),
    environment="dev",  # dev, staging, prod
)

# 設定の読み込み
# 優先順位: CLI引数 > 環境変数 > .env > TOML > デフォルト値
settings = manager.load_settings(LeaderAgentSettings)

# 設定値へのアクセス
print(f"Model: {settings.model}")
print(f"Timeout: {settings.timeout_seconds}")
print(f"Temperature: {settings.temperature}")
```

### 4. CLI引数での上書き

Typerを使ったCLI統合の例：

```python
from typing import Optional
from pathlib import Path
import typer
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import LeaderAgentSettings

app = typer.Typer()

@app.command()
def main(
    task: str,
    model: Optional[str] = typer.Option(None, help="LLMモデル"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="タイムアウト（秒）"),
    workspace: Path = typer.Option(..., help="ワークスペースパス"),
    debug: bool = typer.Option(False, "--debug", help="デバッグ情報を表示"),
):
    """タスクを実行します。"""
    # CLI引数を渡す
    manager = ConfigurationManager(
        cli_args={
            "model": model,
            "timeout_seconds": timeout,
        },
        workspace=workspace,
        environment="dev",
    )

    # 設定の読み込み
    settings = manager.load_settings(LeaderAgentSettings)

    # デバッグ情報の出力
    if debug:
        manager.print_debug_info(settings, verbose=True)

    # タスク実行
    typer.echo(f"Executing task: {task}")
    typer.echo(f"Model: {settings.model}")
    typer.echo(f"Timeout: {settings.timeout_seconds}s")

if __name__ == "__main__":
    app()
```

実行例：

```bash
# CLI引数で一時的に設定を上書き（LeaderAgent設定の例）
uv run python main.py "Generate report" \
    --workspace /path/to/workspace \
    --timeout-per-team-seconds 600 \
    --debug
```

## CLI Usage

Configuration Managerは専用のCLIコマンドを提供します。

### 設定値の表示

#### すべての設定を表示

**表示される Settings**:
- `OrchestratorSettings` - オーケストレーション全体の設定
- `UISettings` - Streamlit UI実行時の設定
- `LeaderAgentSettings` - Leader Agentの設定
- `MemberAgentSettings` - Member Agentの設定
- `EvaluatorSettings` - Evaluatorの設定
- `JudgmentSettings` - Judgment（ラウンド継続判定）の設定
- `PromptBuilderSettings` - UserPromptBuilderの設定
- `TeamSettings` - Team設定（Leader + Members）

```bash
# すべての現在の設定値を階層形式で表示
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config show --config orchestrator.toml

# または --workspace オプションで指定
mixseek config show --config orchestrator.toml --workspace /path/to/workspace
```

出力例：

```
[orchestrator] (orchestrator.toml)
  timeout_per_team_seconds: 600
  max_concurrent_teams: 4

  [team 1] (configs/team.toml)
    name: Research Team

    [member 1] (configs/member-leader.toml)
      role: leader
      model: openai:gpt-4o

    [member 2] (configs/member-analyst.toml)
      role: member
      model: google-gla:gemini-2.5-flash-lite
```

#### 特定の設定を表示

```bash
# 特定の設定項目の詳細を表示
mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace
```

出力例：

```
Class: OrchestratorSettings
Key: timeout_per_team_seconds
Current Value: 600
Default Value: 300
Source: orchestrator.toml (toml)
Type: int
Overridden: Yes
```

#### JSON形式で表示（プログラム用）

```bash
# 全設定をJSON形式で表示
mixseek config show --config orchestrator.toml --workspace /path/to/workspace --output-format json

# 特定キーをJSON形式で表示
mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace --output-format json
```

出力例（全設定）：

```json
{
  "orchestrator": {
    "source_file": "/path/to/orchestrator.toml",
    "settings": {
      "timeout_per_team_seconds": 600,
      "max_concurrent_teams": 4,
      ...
    }
  },
  "teams": [
    {
      "source_file": "/path/to/team.toml",
      "settings": {...},
      "members": [...]
    }
  ]
}
```

出力例（特定キー）：

```json
{
  "class": "OrchestratorSettings",
  "key": "timeout_per_team_seconds",
  "current_value": "600",
  "default_value": "300",
  "source": "orchestrator.toml",
  "source_type": "toml",
  "type": "int",
  "overridden": true
}
```

### 設定項目の一覧表示（スキーマ情報）

```bash
# すべての利用可能な設定項目のスキーマ情報を表示
mixseek config list

# テキスト形式で詳細表示
mixseek config list --output-format text

# JSON形式で出力（プログラム用）
mixseek config list --output-format json
```

**注意**: このコマンドはスキーマ情報のみを表示します。実際の設定値を確認するには `config show` を使用してください。

出力例（テーブル形式）：

```
Key                                      | Default | Type | Description
OrchestratorSettings.timeout_per_team_seconds | 300     | int  | チーム単位タイムアウト（秒）
OrchestratorSettings.max_concurrent_teams     | 3       | int  | 同時実行チーム数
OrchestratorSettings.workspace_path           | None    | Path | ワークスペースディレクトリパス
```

出力例（テキスト形式）：

```
Available Configuration Settings:

[Required]
  workspace_path (Path)
    Description: ワークスペースディレクトリパス
    Default: None (must be set)

[Optional]
  timeout_per_team_seconds (int)
    Description: チーム単位タイムアウト（秒）
    Default: 300

  max_concurrent_teams (int)
    Description: 同時実行チーム数
    Default: 3
```

出力例（JSON形式）：

```json
[
  {
    "key": "OrchestratorSettings.timeout_per_team_seconds",
    "class_name": "OrchestratorSettings",
    "raw_key": "timeout_per_team_seconds",
    "default": "300",
    "type": "int",
    "description": "チーム単位タイムアウト（秒）"
  },
  {
    "key": "OrchestratorSettings.max_concurrent_teams",
    "class_name": "OrchestratorSettings",
    "raw_key": "max_concurrent_teams",
    "default": "3",
    "type": "int",
    "description": "同時実行チーム数"
  }
]
```

### TOMLテンプレートの生成

#### デフォルトテンプレートの生成

```bash
# config.tomlテンプレートを生成
mixseek config init
```

生成されるファイル（`config.toml`）:

```toml
# Configuration Template
# Generated by mixseek config init

# ===== Required Settings =====
workspace_path = ""  # Path: ワークスペースディレクトリパス

# ===== Optional Settings =====
# model = "openai:gpt-4o"  # str: LLMモデル (例: openai:gpt-4o)
# temperature = null  # float | None: Temperature (Noneの場合はモデルのデフォルト値) [0.0-2.0]
# max_tokens = null  # int | None: 最大トークン数 (Noneの場合はLLM側のデフォルト値) [> 0]
# timeout_seconds = 300  # int: HTTPタイムアウト（秒） [>= 0]
# max_retries = 3  # int: LLM API呼び出しの最大リトライ回数 [>= 0]
# stop_sequences = null  # list[str] | None: 停止シーケンス（オプション）
# top_p = null  # float | None: Top-pサンプリング [0.0-1.0]
# seed = null  # int | None: ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）
```

#### コンポーネント別のテンプレート生成

```bash
# Team設定用のテンプレート生成
mixseek config init --component team
```

生成されるファイル（`team.toml`）:

```toml
# Team Configuration Template
# Generated by mixseek config init --component team

# ===== Team Settings =====
name = ""  # str: チーム名

# ===== Leader Agent Settings =====
[leader]
# model = "openai:gpt-4o"  # str: LLMモデル
# temperature = null  # float | None: Temperature [0.0-2.0]
# max_tokens = null  # int | None: 最大トークン数 [> 0]
# timeout_seconds = 300  # int: HTTPタイムアウト（秒） [>= 0]
# max_retries = 3  # int: LLM API呼び出しの最大リトライ回数 [>= 0]
# stop_sequences = null  # list[str] | None: 停止シーケンス（オプション）
# top_p = null  # float | None: Top-pサンプリング [0.0-1.0]
# seed = null  # int | None: ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）

# ===== Member Agent Settings =====
[member]
# model = "anthropic:claude-sonnet-4-5"  # str: LLMモデル
# temperature = null  # float | None: Temperature [0.0-2.0]
# max_tokens = null  # int | None: 最大トークン数 [> 0]
# timeout_seconds = 180  # int: HTTPタイムアウト（秒） [>= 0]
# max_retries = 3  # int: LLM API呼び出しの最大リトライ回数 [>= 0]
# stop_sequences = null  # list[str] | None: 停止シーケンス（オプション）
# top_p = null  # float | None: Top-pサンプリング [0.0-1.0]
# seed = null  # int | None: ランダムシード（OpenAI/Geminiでサポート、Anthropicでは非サポート）
```

#### Orchestrator設定用のテンプレート生成

```bash
# Orchestrator設定用のテンプレート生成
mixseek config init --component orchestrator
```

#### 既存ファイルの上書き

```bash
# 既存のconfig.tomlを上書き
mixseek config init --force
```

## Common Patterns

### パターン1: 環境変数による上書き

TOMLファイルで基本設定を管理し、環境変数で環境別に上書きします。

**ステップ1**: TOMLファイルで基本設定を定義

```toml
# config.toml
[leader]
model = "openai:gpt-4o"
timeout_seconds = 300
```

**ステップ2**: 本番環境で環境変数を設定

```bash
# 本番環境の環境変数
export MIXSEEK_ENVIRONMENT=prod
export MIXSEEK_LEADER__MODEL="openai:gpt-4-turbo"
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600
```

**ステップ3**: アプリケーションを起動

```python
manager = ConfigurationManager(environment="prod")
settings = manager.load_settings(LeaderAgentSettings)
# settings.model は "openai:gpt-4-turbo" (環境変数から)
# settings.timeout_seconds は 600 (環境変数から)
```

### パターン2: CLI引数で一時的に設定変更

テストやデバッグ時にCLI引数で設定を一時的に変更します。

```bash
# テスト実行時に異なるタイムアウトを試す（LeaderAgent設定の例）
uv run mixseek team "Task description" \
    --config team.toml \
    --timeout-per-team-seconds 900
```

**優先順位**:
1. CLI引数（`--timeout-per-team-seconds 900`）
2. 環境変数（`MIXSEEK_TIMEOUT_PER_TEAM_SECONDS`）
3. .envファイル
4. TOMLファイル（`team.toml`）
5. デフォルト値

### パターン3: デバッグ情報の活用

`--debug` フラグで設定の出所を追跡します。

```bash
# デバッグ情報を表示して実行
uv run python main.py "task" --debug
```

出力例：

```
============================================================
Configuration Debug Information
============================================================

model: 'anthropic:claude-opus-4'
  Source: init (cli)
  Timestamp: 2025-11-11T12:00:00+00:00

timeout_seconds: 600
  Source: environment_variables (env)
  Timestamp: 2025-11-11T12:00:00+00:00

temperature: 0.7
  Source: config.toml (toml)
  Timestamp: 2025-11-11T12:00:00+00:00

============================================================
```

### パターン4: トレース情報の取得

Pythonコードでトレース情報にアクセスします。

```python
from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import LeaderAgentSettings

manager = ConfigurationManager()
settings = manager.load_settings(LeaderAgentSettings)

# 特定のフィールドのトレース情報を取得
model_trace = manager.get_trace_info(LeaderAgentSettings, "model")
if model_trace:
    print(f"Model value: {model_trace.value}")
    print(f"Source: {model_trace.source_name} ({model_trace.source_type})")
    print(f"Timestamp: {model_trace.timestamp.isoformat()}")
```

出力例：

```
Model value: openai:gpt-5
Source: environment_variables (env)
Timestamp: 2025-11-11T12:00:00+00:00
```

### パターン5: 環境別バリデーション

開発環境と本番環境で異なるバリデーションを適用します。

**開発環境（dev/staging）**:

```bash
# デフォルト値で起動可能
export MIXSEEK_ENVIRONMENT=dev
uv run python main.py
# settings.model は "openai:gpt-4o" (デフォルト値)
```

**本番環境（prod）**:

```bash
# 必須設定が未設定の場合はエラー
export MIXSEEK_ENVIRONMENT=prod
uv run python main.py
# ValidationError: MIXSEEK_LEADER_MODEL must be explicitly set in production

# 明示的に設定する必要がある
export MIXSEEK_LEADER__MODEL="openai:gpt-4-turbo"
uv run python main.py
# OK
```

## Next Steps

### 詳細ドキュメント

- **仕様書**: `/home/driller/repo/dseek_for_drillan/specs/013-configuration/spec.md`
  - 完全な機能要件、User Stories、成功基準
- **技術評価**: `/home/driller/repo/dseek_for_drillan/specs/013-configuration/assets/pydantic-settings-configuration-manager.md`
  - pydantic-settingsの詳細な評価と実装例
- **研究レポート**: `/home/driller/repo/dseek_for_drillan/specs/013-configuration/research.md`
  - 技術的意思決定とベストプラクティス

### 関連機能

- **Article 9準拠**: Configuration Managerは「Data Accuracy Mandate」に完全準拠しています
  - ハードコーディング禁止
  - 暗黙的フォールバック禁止
  - 明示的データソース指定
  - 適切なエラー伝播

### サンプルコード

完全な実装例は `/home/driller/repo/dseek_for_drillan/specs/013-configuration/assets/pydantic-settings-configuration-manager.md` の Section 2.3に記載されています。

### トラブルシューティング

**Q: 設定値が反映されない**

A: `--debug` フラグで設定の出所を確認してください：

```bash
uv run python main.py --debug
```

**Q: 環境変数の命名規則がわからない**

A: 以下のルールに従います：

- プレフィックス: `MIXSEEK_`
- ネスト区切り: `__`（アンダースコア2つ）
- 例: `MIXSEEK_LEADER__MODEL`, `MIXSEEK_LEADER__TIMEOUT_SECONDS`

**Q: 必須設定が未設定でエラーになる**

A: 環境変数、.env、TOMLファイルのいずれかで設定してください：

```bash
# 環境変数で設定
export MIXSEEK_WORKSPACE_PATH="/path/to/workspace"

# または .env ファイルで設定
echo "MIXSEEK_WORKSPACE_PATH=/path/to/workspace" >> .env

# または TOML ファイルで設定
echo "workspace_path = '/path/to/workspace'" >> config.toml
```

**Q: TOMLファイルの構文エラー**

A: TOMLファイルの構文を確認してください。文字列は引用符で囲む必要があります：

```toml
# ❌ 誤り
workspace_path = /path/to/workspace

# ✅ 正しい
workspace_path = "/path/to/workspace"
```

### コミュニティとサポート

- **Issue報告**: [GitHub Issues](https://github.com/AlpacaTechSolution/mixseek-core/issues/51)
- **ディスカッション**: GitHub Discussions
