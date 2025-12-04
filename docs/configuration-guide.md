# 設定管理ガイド

MixSeek-Coreの統一設定管理システム（Configuration Manager）の完全ガイドです。

## 概要

MixSeek-Coreは、Pydantic Settingsベースの統一設定管理システムを提供します。すべての設定値を一元化し、複数のソースから優先順位に従って読み込みます。

### 主な機能

- **統一設定管理**: すべての設定値を Configuration Manager で一元管理
- **優先順位チェーン**: CLI > 環境変数 > .env > TOML > デフォルト値
- **トレーサビリティ**: 各設定値の出所を追跡可能
- **Article 9準拠**: Data Accuracy Mandate に完全準拠

## 優先順位チェーン

設定値は以下の優先順位で読み込まれます（高い順）：

```
1. CLI引数 (--config オプション等) ← 最高優先度
2. 環境変数 (MIXSEEK_* プレフィックス)
3. .env ファイル
4. TOML設定ファイル (config.toml, team.toml 等)
5. デフォルト値 (スキーマ定義) ← 最低優先度
```

**優先順位の例**:

```bash
# 例: timeout_per_team_seconds の設定

# 1. CLI引数で指定
mixseek exec "タスク" --config orch.toml --timeout 600  # → 600秒

# 2. 環境変数も設定されている場合
export MIXSEEK_TIMEOUT_PER_TEAM_SECONDS=300
mixseek exec "タスク" --config orch.toml --timeout 600  # → 600秒（CLI優先）

# 3. TOML設定ファイルにも記載されている場合
# orch.toml: timeout_per_team_seconds = 120
export MIXSEEK_TIMEOUT_PER_TEAM_SECONDS=300
mixseek exec "タスク" --config orch.toml  # → 300秒（環境変数優先）

# 4. すべて未指定の場合
mixseek exec "タスク" --config orch.toml  # → 120秒（TOML設定）
```

## Configuration Manager

### 基本的な使い方

```python
from pathlib import Path
from mixseek.config import ConfigurationManager, OrchestratorSettings

# Configuration Manager初期化
manager = ConfigurationManager(
    cli_args={"timeout_per_team_seconds": 600},
    workspace=Path("/workspace"),
    environment="prod"
)

# 設定読み込み
settings = manager.load_settings(OrchestratorSettings)

# 設定値の確認
print(f"Timeout: {settings.timeout_per_team_seconds}")
```

### トレーサビリティ

各設定値の出所を追跡できます：

```python
# 特定フィールドの出所を確認
trace = manager.get_trace_info(OrchestratorSettings, "timeout_per_team_seconds")
print(f"Value: {trace.value}")
print(f"Source: {trace.source_name}")  # cli/env/toml/default
print(f"Timestamp: {trace.timestamp}")
```

## 設定スキーマ一覧

Configuration Manager で管理される主要な設定スキーマ：

| スキーマ名 | 説明 | TOMLセクション | 環境変数プレフィックス |
|-----------|------|---------------|-------------------|
| OrchestratorSettings | ワークスペースとチーム並列実行 | `[orchestrator]` | `MIXSEEK_` |
| LeaderAgentSettings | リーダーエージェント | `[leader]` | `MIXSEEK_LEADER__` |
| MemberAgentSettings | メンバーエージェント | `[member]` | `MIXSEEK_MEMBER__` |
| EvaluatorSettings | 評価器 | `[evaluator]` | `MIXSEEK_EVALUATOR__` |
| JudgmentSettings | ラウンド継続判定 | `[judgment]` | `MIXSEEK_JUDGMENT__` |
| TeamSettings | チーム全体 | `[team]` | `MIXSEEK_TEAM__` |
| UISettings | Streamlit UI | `[ui]` | `MIXSEEK_UI__` |

詳細は [設定リファレンス](configuration-reference.md) を参照してください。

## ユースケース

### ユースケース1: 開発環境と本番環境の設定分離

**開発環境** (`.env.dev`):

```bash
MIXSEEK_WORKSPACE=/home/dev/mixseek-workspace
MIXSEEK_LEADER__TIMEOUT_SECONDS=120
MIXSEEK_LEADER__MODEL=google-gla:gemini-2.5-flash-lite
```

**本番環境** (`.env.prod`):

```bash
MIXSEEK_WORKSPACE=/var/mixseek/workspace
MIXSEEK_LEADER__TIMEOUT_SECONDS=600
MIXSEEK_LEADER__MODEL=anthropic:claude-sonnet-4-5
```

実行時に環境変数ファイルを切り替え：

```bash
# 開発環境
source .env.dev
mixseek team "タスク" --config team.toml

# 本番環境
source .env.prod
mixseek team "タスク" --config team.toml
```

### ユースケース2: CI/CD環境での設定上書き

GitLab CI/CD で環境変数を設定：

```yaml
# .gitlab-ci.yml
test:
  variables:
    MIXSEEK_WORKSPACE: /builds/workspace
    MIXSEEK_LEADER__TIMEOUT_SECONDS: "300"
    MIXSEEK_LEADER__MODEL: "google-gla:gemini-2.5-flash-lite"
  script:
    - mixseek team "テストタスク" --config team.toml
```

### ユースケース3: デバッグ時の一時的な設定変更

デバッグ時に CLI 引数で一時的に設定を上書き：

```bash
# 通常実行
mixseek team "タスク" --config team.toml

# デバッグ: タイムアウトを延長
mixseek team "タスク" --config team.toml --workspace /tmp/debug-ws

# デバッグ: 詳細ログ
export MIXSEEK_LOG_LEVEL=DEBUG
mixseek team "タスク" --config team.toml --verbose
```

## CLIコマンド

### config init - テンプレート生成

TOML設定ファイルのテンプレートを生成します。

**オプション**:
- `--component` / `-c`: コンポーネント名（orchestrator, team, evaluator, judgment, prompt_builder）
- `--workspace` / `-w`: ワークスペースパス（省略時は `MIXSEEK_WORKSPACE` 環境変数を使用）
- `--output-path` / `-o`: 出力ファイルパス（絶対パスまたはworkspaceからの相対パス、デフォルト: `workspace/configs/<component>.toml`）
- `--force` / `-f`: 既存ファイルを上書き

**基本的な使用例**:

```bash
# デフォルトパス: workspace/configs/config.toml
mixseek config init --workspace /path/to/workspace

# コンポーネント別テンプレート（workspace/configs/<component>.toml）
mixseek config init --component orchestrator --workspace /path/to/workspace
mixseek config init --component team --workspace /path/to/workspace
mixseek config init --component evaluator --workspace /path/to/workspace

# 環境変数を使用
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config init --component orchestrator
```

**出力先のカスタマイズ**:

```bash
# カスタム相対パス: workspace/my-configs/orchestrator.toml
mixseek config init --component orchestrator \
  --output-path my-configs/orchestrator.toml \
  --workspace /path/to/workspace

# 絶対パス: /tmp/orchestrator.toml
mixseek config init --component orchestrator \
  --output-path /tmp/orchestrator.toml

# 強制上書き
mixseek config init --component orchestrator \
  --workspace /path/to/workspace \
  --force
```

### config show - 設定値表示

現在の設定値を階層形式で表示します。

**必須オプション**:
- `--config` / `-c`: orchestrator TOML ファイルパス（必須）

**オプション**:
- `--workspace` / `-w`: ワークスペースパス（省略時は `MIXSEEK_WORKSPACE` 環境変数を使用）
- `--output-format` / `-f`: 出力形式（text/json、デフォルト: text）
- `--environment` / `-e`: 環境（dev/staging/prod）

**表示される Settings**:
- `OrchestratorSettings` - オーケストレーション全体の設定
- `TeamSettings` - Team設定（Leader + Members）
- `MemberAgentSettings` - Member Agentの設定
- `EvaluatorSettings` - 評価器の設定（orchestrator.evaluator_config で指定）
- `JudgmentSettings` - 継続判定の設定（orchestrator.judgment_config で指定）
- `PromptBuilderSettings` - プロンプトビルダーの設定（configs/prompt_builder.toml）

```bash
# 全設定値を表示（階層形式、デフォルト）
mixseek config show --config orchestrator.toml --workspace /path/to/workspace

# MIXSEEK_WORKSPACE 環境変数を使用
export MIXSEEK_WORKSPACE=/path/to/workspace
mixseek config show --config orchestrator.toml

# 特定フィールドを表示
mixseek config show timeout_per_team_seconds --config orchestrator.toml --workspace /path/to/workspace

# JSON形式で表示（プログラム用）
mixseek config show --config orchestrator.toml --workspace /path/to/workspace --output-format json
```

**出力形式** (`--output-format` / `-f`):
- `text`: 階層的インデント表示（デフォルト）
  - orchestrator レベル: インデントなし
  - team レベル: 2スペースインデント
  - member レベル: 4スペースインデント
- `json`: JSON形式（階層構造を JSON オブジェクトとして出力）
  - 全設定表示時:
    ```json
    {
      "orchestrator": {
        "source_file": "/path/to/orchestrator.toml",
        "settings": {"timeout_per_team_seconds": 600, ...}
      },
      "teams": [
        {
          "source_file": "/path/to/team.toml",
          "settings": {...},
          "members": [
            {
              "source_file": "/path/to/member.toml",
              "settings": {...}
            }
          ]
        }
      ],
      "evaluator": {
        "source_file": "/path/to/evaluator.toml",
        "settings": {...}
      },
      "judgment": {
        "source_file": "/path/to/judgment.toml",
        "settings": {...}
      },
      "prompt_builder": {
        "source_file": "/path/to/prompt_builder.toml",
        "settings": {...}
      }
    }
    ```
  - 特定キー指定時:
    ```json
    {
      "class": "OrchestratorSettings",
      "key": "timeout_per_team_seconds",
      "current_value": "600",
      "default_value": "300",
      "source": "TOML",
      "source_type": "toml",
      "type": "int",
      "overridden": true
    }
    ```

**安全機能**:
- 循環参照検出（エラー時に参照パスを表示）
- 最大再帰深度制限（10レベル）

### config list - 設定項目一覧

利用可能な設定項目のスキーマ情報をリスト表示します。

```bash
# 全設定項目をリスト表示（テーブル形式）
mixseek config list

# テキスト形式で詳細表示
mixseek config list --output-format text

# JSON形式（プログラム用）
mixseek config list --output-format json
```

**表示内容**:
- **テーブル形式**: Key, Default, Type, Description の列を表示
- **テキスト形式**: Required/Optional でグループ化し、各項目の詳細を表示
- **JSON形式**: プログラムで処理可能な JSON 配列形式で出力（key, class_name, raw_key, default, type, description を含む）

**注意**: このコマンドはスキーマ情報（デフォルト値、型、説明）のみを表示します。実際の設定値や設定ソースを確認するには `config show` を使用してください。

## 環境変数設定

### 環境変数命名規則

環境変数名は以下の規則に従います：

- **プレフィックス**: `MIXSEEK_`
- **ネスト**: ダブルアンダースコア (`__`) で区切る
- **大文字**: すべて大文字

**例**:

```bash
# フラットな設定
export MIXSEEK_WORKSPACE=/path/to/workspace

# ネストされた設定
export MIXSEEK_LEADER__MODEL=openai:gpt-4o
export MIXSEEK_LEADER__TIMEOUT_SECONDS=600
export MIXSEEK_MEMBER__MODEL=google-gla:gemini-2.5-flash-lite
```

### .env ファイル

`.env` ファイルで環境変数を管理できます：

```bash
# .env
MIXSEEK_WORKSPACE=/home/user/workspace
MIXSEEK_LEADER__MODEL=openai:gpt-4o
MIXSEEK_LEADER__TIMEOUT_SECONDS=600
```

`.env` ファイルの読み込み：

```bash
# 自動読み込み（プロジェクトルートに配置）
mixseek team "タスク" --config team.toml

# 手動読み込み
source .env
mixseek team "タスク" --config team.toml
```

## Article 9 準拠

Configuration Manager は Article 9 (Data Accuracy Mandate) に完全準拠しています：

### 準拠ポイント

1. **明示的なデータソース**: すべての設定値は明示的なソース（CLI、環境変数、TOML等）から取得
2. **暗黙的デフォルトなし**: ハードコードされたデフォルト値を排除
3. **適切なエラー伝播**: 無効な設定時に明確なエラーメッセージを表示
4. **トレーサビリティ**: すべての設定値の出所を追跡可能

### 実装例

```python
from mixseek.config import ConfigurationManager, OrchestratorSettings

manager = ConfigurationManager()

# 設定読み込み（Article 9準拠）
settings = manager.load_settings(OrchestratorSettings)

# エラーが発生した場合、明確なメッセージが表示される
# 例: "MIXSEEK_WORKSPACE environment variable is not set"
```

## トラブルシューティング

### 環境変数が反映されない

**症状**: 環境変数を設定しても反映されない

**原因**:
- 環境変数名の誤り
- 環境変数のスコープ（シェルセッション限定）

**解決方法**:

```bash
# 環境変数の確認
echo $MIXSEEK_WORKSPACE

# 設定されていない場合は設定
export MIXSEEK_WORKSPACE=/path/to/workspace

# 永続化（~/.bashrc または ~/.zshrc に追加）
echo 'export MIXSEEK_WORKSPACE=/path/to/workspace' >> ~/.bashrc
source ~/.bashrc
```

### TOML設定が読み込まれない

**症状**: TOML設定ファイルが読み込まれない

**原因**:
- ファイルパスの誤り
- TOML構文エラー

**解決方法**:

```bash
# ファイルの存在確認
ls -la team.toml

# TOML構文の検証（Python）
python -c "import tomllib; tomllib.load(open('team.toml', 'rb'))"
```

### 優先順位が不明確

**症状**: どの設定値が使われているか分からない

**解決方法**:

```bash
# 設定値の出所を確認
mixseek config show workspace_path

# デバッグ情報を表示
mixseek team "タスク" --config team.toml --verbose
```

## セキュリティ

### 機密情報の取り扱い

設定値を表示する際、以下のフィールド名パターンを含む設定は自動的にマスクされます：

- `api_key`
- `password`
- `secret`
- `token`
- `credential`
- `private_key`
- `access_key`

**Article 9準拠**: 機密情報フィールドは明示的なパターンリストで定義されています（暗黙的な推測は行いません）。

#### 例

```bash
# 機密情報を含む設定の表示
$ mixseek config show
api_key: [REDACTED]
model: gemini-2.5-flash-lite
workspace_path: /path/to/workspace
```

#### 機密情報の保護

**推奨事項**:

1. **環境変数の使用**: API キーやパスワードは環境変数で管理してください
2. **TOMLファイルのGit除外**: 機密情報を含む`.toml`ファイルは`.gitignore`に追加してください
3. **アクセス権限の設定**: TOMLファイルのパーミッションを適切に制限してください（例: `chmod 600 config.toml`）

```bash
# 良い例: 環境変数で管理
export MIXSEEK_API_KEY="your-secret-key"
mixseek team "タスク" --config team.toml

# 避けるべき: TOMLファイルに直接記載
# [bad] team.toml:
# api_key = "your-secret-key"  # Git履歴に残る可能性
```

## 関連ドキュメント

- [設定リファレンス](configuration-reference.md) - 全設定項目の詳細
- [クイックスタート](quickstart.md) - 基本的な使い方
- [開発者ガイド](developer-guide.md) - カスタム設定スキーマの作成
