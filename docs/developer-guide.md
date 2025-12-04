# 開発者ガイド: mixseek-core

このガイドでは、mixseek-core CLIツールのアーキテクチャ、開発ワークフロー、テスト戦略について説明します。

## アーキテクチャ概要

### プロジェクト構造

```
src/mixseek/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Typer app entry point
│   └── commands/
│       ├── __init__.py
│       └── init.py          # mixseek init command
├── config/
│   ├── __init__.py
│   ├── constants.py         # Default values and constants
│   └── templates.py         # TOML template generation
├── models/
│   ├── __init__.py
│   ├── config.py            # ProjectConfig Pydantic model
│   ├── result.py            # InitResult model
│   └── workspace.py         # WorkspacePath, WorkspaceStructure models
└── utils/
    ├── __init__.py
    ├── env.py               # Environment variable handling
    └── filesystem.py        # Path validation utilities
```

### 技術スタック

- **Python**: 3.13.7+ （mypy厳格型チェック付き）
- **CLIフレームワーク**: Typer（Clickベース）
- **データ検証**: Pydantic v2（ランタイム検証付き）
- **設定**: TOML形式（tomli-w使用）
- **テスト**: pytest（仕様準拠テスト、統合テスト、ユニットテスト）
- **コード品質**: Ruff（リント/フォーマット）、mypy（型チェック）

## 開発ワークフロー

### 開発環境のセットアップ

MixSeek-Coreは、ローカル環境とDocker環境の両方で開発できます。

#### ローカル環境でのセットアップ

```bash
# リポジトリのクローン
git clone <repository-url>
cd mixseek-core

# 依存関係のインストール（uv推奨）
uv sync --all-groups

# または pip を使用
pip install -e .

# インストール確認
mixseek --version
```

#### Docker環境でのセットアップ

Docker環境では、標準化された再現可能な開発環境が提供されます。開発環境（`dockerfiles/dev/`）とCI環境（`dockerfiles/ci/`）の2種類が用意されています。

##### 開発環境（ローカル開発用）

詳細なセットアップ手順は [docker-setup.md](docker-setup.md) を参照してください。

```bash
# 環境設定ファイルのコピー
cp dockerfiles/dev/.env.dev.template .env.dev
vim .env.dev  # APIキーと設定を記述

# 開発コンテナのビルド・起動
make -C dockerfiles/dev build
make -C dockerfiles/dev run

# コンテナに接続
make -C dockerfiles/dev bash
```

##### CI環境（GitHub Actions CI検証用）

CI専用の最小構成Docker環境で、**GitHub Actions CIと全く同じ環境**をローカルで再現できます。

```bash
# CI環境イメージのビルド
make -C dockerfiles/ci build

# コードリンティング（GitHub Actions CIと同じ）
make -C dockerfiles/ci lint

# フォーマットチェック
make -C dockerfiles/ci format-check

# 型チェック
make -C dockerfiles/ci type-check

# テスト実行（E2E除く）
make -C dockerfiles/ci test-fast

# すべてのCIチェックを実行
make -C dockerfiles/ci check

# より詳細なテスト実行（高速版）
make -C dockerfiles/ci quality-gate-fast
```

**開発環境とCI環境の使い分け**:
- **開発環境**: 日常的なコーディング、デバッグ、対話的な作業に使用
- **CI環境**: PR作成前のCI検証、リリース前の品質チェックに使用
  - GitHub Actions CIと完全に同じ環境
  - PR送信前にローカルでCIの動作を確認可能
  - CI失敗のトラブルシューティングに有用

詳細は以下を参照：
- **Dockerセットアップ**: [docker-setup.md](docker-setup.md)
- **CI環境の詳細**: `../dockerfiles/ci/README.md`
- **Docker開発環境の詳細**: `../dockerfiles/README.ja.md`

### テストの実行

#### ローカル環境でのテスト

```bash
# すべてのテストを実行
pytest

# 特定のテストカテゴリを実行
pytest tests/contract/     # CLI仕様準拠テスト
pytest tests/integration/  # 統合テスト
pytest tests/unit/         # ユニットテスト

# カバレッジ付きで実行
pytest --cov=src/mixseek --cov-report=html

# 詳細出力付きでテストを実行
pytest -v -s
```

#### Docker環境でのテスト

```bash
# 完全なテストスイートを実行
make -C dockerfiles/dev unittest

# コード品質チェック
make -C dockerfiles/dev lint
make -C dockerfiles/dev format

# コンテナ内で直接pytestを実行
make -C dockerfiles/dev bash
# コンテナ内で:
pytest -v -s
```

### コード品質

#### ローカル環境

```bash
# リントと自動修正
ruff check --fix .

# コードフォーマット
ruff format .

# 型チェック
mypy src/

# 厳格な型チェック（推奨）
mypy --strict src/

# すべての品質チェックを実行
ruff check . && ruff format . && mypy src/
```

#### Docker環境

```bash
# 開発環境でのコード品質チェック
make -C dockerfiles/dev lint
make -C dockerfiles/dev format

# CI環境でのコード品質チェック（PR前の検証）
make -C dockerfiles/ci check

# より詳細な品質チェック（高速版）
make -C dockerfiles/ci quality-gate-fast
```

**`make -C dockerfiles/ci check` の内容**:
1. Ruff linting
2. コードフォーマットチェック
3. mypy型チェック

**`make -C dockerfiles/ci quality-gate-fast` の内容**:
1. Ruff linting
2. コードフォーマットチェック
3. pytestテスト実行（E2E除く）

詳細は `../dockerfiles/ci/README.md` を参照してください。

### テスト戦略

#### テストカテゴリ

1. **仕様準拠テスト** (`tests/contract/`)
   - CLIインターフェースの仕様準拠性をテスト
   - 終了コード、出力形式、オプション動作
   - subprocessを使用して実際のCLIをテスト

2. **統合テスト** (`tests/integration/`)
   - 完全な機能ワークフローをテスト
   - 一時ディレクトリを使用した実際のファイルシステム操作
   - 環境変数の処理
   - エラーシナリオとエッジケース

3. **ユニットテスト** (`tests/unit/`)
   - 個別の関数とクラスをテスト
   - Pydanticモデルの検証
   - ユーティリティ関数（env.py、filesystem.py、templates.py）
   - モックされた外部依存関係

#### テスト駆動開発

このプロジェクトはTDDアプローチに従います（Article 3準拠）：

1. **テストを最初に書く** - テストは最初は失敗するべき
2. **最小限のコードを実装** してテストをパスさせる
3. **リファクタリング** を行いながらテストをグリーンに保つ
4. **受け入れ基準に対して検証** する

#### 特定のテストの実行

```bash
# CLI仕様準拠性のための仕様準拠テスト
pytest tests/contract/test_init_contract.py -v

# 機能ワークフローのための統合テスト
pytest tests/integration/test_init_integration.py -v

# モデルのためのユニットテスト
pytest tests/unit/test_models.py -v

# 特定の機能をテスト
pytest -k "test_specific_feature" -v
```

## CLIの拡張

### 新しいコマンドの追加

1. `src/mixseek/cli/commands/`にコマンドモジュールを作成：

```python
# src/mixseek/cli/commands/new_command.py
import typer
from pathlib import Path
from typing import Optional

def new_command(
    option: Optional[str] = typer.Option(None, help="Description")
) -> None:
    """新しいコマンドの説明

    Args:
        option: オプションの説明

    Examples:
        mixseek new-command --option value
    """
    # 実装はここに
    # mypy strict モードでエラーが出ないよう型チェックを徹底
    pass
```

2. メインCLIアプリに登録：

```python
# src/mixseek/cli/main.py
from mixseek.cli.commands.new_command import new_command

app.command()(new_command)
```

3. 最初にテストを書く（TDD）：
   - CLIインターフェースのための仕様準拠テスト
   - 機能のための統合テスト
   - コンポーネントのためのユニットテスト

### CLIオプションの標準化

**Constitution Article 10 (DRY Principle) 準拠**: CLIオプションは `src/mixseek/cli/common_options.py` で定義された共通定数を使用してください。

#### 利用可能な共通オプション

```python
from mixseek.cli.common_options import (
    WORKSPACE_OPTION,      # --workspace, -w
    VERBOSE_OPTION,        # --verbose, -v
    LOGFIRE_OPTION,        # --logfire
    LOGFIRE_METADATA_OPTION,  # --logfire-metadata
    LOGFIRE_HTTP_OPTION,   # --logfire-http
    LOG_LEVEL_OPTION,      # --log-level
    NO_LOG_CONSOLE_OPTION, # --no-log-console
    NO_LOG_FILE_OPTION,    # --no-log-file
)
```

#### 使用例

```python
# src/mixseek/cli/commands/my_command.py
from pathlib import Path
import typer
from mixseek.cli.common_options import WORKSPACE_OPTION, VERBOSE_OPTION

def my_command(
    workspace: Path | None = WORKSPACE_OPTION,
    verbose: bool = VERBOSE_OPTION,
    # カスタムオプション
    custom_option: str = typer.Option(..., "--custom", help="Custom option"),
) -> None:
    """My command description."""
    # 実装
    pass
```

#### 利点

- **一貫性**: すべてのコマンドで同じオプション定義を使用
- **保守性**: オプション定義を一箇所で管理
- **変更容易性**: ヘルプテキストやデフォルト値の変更が容易

#### 新しい共通オプションの追加

複数のコマンドで使用するオプションは `common_options.py` に追加してください：

```python
# src/mixseek/cli/common_options.py

# New option - used by: command1, command2, command3
NEW_OPTION = typer.Option(
    default_value,
    "--new-option",
    "-n",
    help="Description of the new option",
)
```

### 新しいモデルの追加

すべてのデータモデルにはPydantic v2を使用します：

```python
from pydantic import BaseModel, field_validator
from typing import Literal

class NewModel(BaseModel):
    """モデルの説明

    すべてのフィールドには明示的な型注釈が必要です。
    mypy strict モードでエラーが出ないことを確認してください。
    """

    field_name: str
    status: Literal["active", "inactive"] = "active"

    @field_validator("field_name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("field_name cannot be empty")
        return v

    @classmethod
    def create_default(cls) -> "NewModel":
        """デフォルトインスタンスのためのファクトリメソッド

        Returns:
            NewModel: デフォルト設定のインスタンス
        """
        return cls(field_name="default")
```

## アーキテクチャパターン

### ライブラリファースト設計（Article 1）

すべての機能はまずライブラリコードとして実装され、その後CLIでラップされます：

```python
from pathlib import Path
from typing import TypedDict

class ProcessResult(TypedDict):
    """処理結果の型定義（Article 16: 型安全性）"""
    success: bool
    processed_count: int
    errors: list[str]

# ライブラリ関数
def process_data(data_path: Path) -> ProcessResult:
    """コアビジネスロジック"""
    # 実装例
    return ProcessResult(
        success=True,
        processed_count=100,
        errors=[]
    )

# CLIラッパー
@app.command()
def process(data: Path = typer.Option(...)):
    """CLIインターフェース"""
    result = process_data(data)
    # CLI固有の処理（出力、エラー）を扱う
    if result["success"]:
        print(f"処理完了: {result['processed_count']}件")
```

### エラー処理戦略

1. **ライブラリレベル**: 特定の例外を発生させる
2. **CLIレベル**: 例外をキャッチしてユーザーフレンドリーなメッセージに変換
3. **テスト**: 例外の型とユーザーメッセージの両方を検証

```python
# ライブラリコード
def validate_path(path: Path) -> None:
    if not path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {path.parent}")

# CLIコード
try:
    validate_path(target_path)
except ValueError as e:
    typer.echo(f"Error: {e}", err=True)
    typer.echo("Solution: Ensure the path is valid", err=True)
    raise typer.Exit(1)
```

### 検証戦略

包括的なランタイム検証にはPydanticを使用します：

- **フィールドバリデーター**: 単一フィールドの検証
- **モデルバリデーター**: フィールド間の検証
- **ファクトリメソッド**: 制御されたオブジェクト生成

### 型安全性の徹底

コードの品質と保守性を確保するため、厳格な型安全性を採用します：

#### mypy設定要件

```ini
# mypy.ini または pyproject.toml [tool.mypy]
[mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
```

#### 型注釈のベストプラクティス

1. **全ての関数に型注釈**: 引数と戻り値の両方
2. **変数の型注釈**: 複雑な型や曖昧な場合は明示
3. **Any型の回避**: 具体的な型を常に使用
4. **Union型の適切な使用**: Python 3.10+ では `|` 構文推奨

```python
# 良い例
def process_file(file_path: Path, encoding: str = "utf-8") -> dict[str, Any]:
    """ファイルを処理してメタデータを返す"""
    # 実装...
    return {"size": 1024, "type": "text"}

# 避けるべき例
def process_file(file_path, encoding="utf-8"):  # 型注釈なし
    return {"size": 1024, "type": "text"}
```

## パフォーマンスに関する考慮事項

### パフォーマンス目標

実装は以下の一般的なパフォーマンス目標を満たす必要があります：

- **ディスク操作**: ファイルシステムI/Oを最小化
- **メモリ使用量**: 大きなデータ構造でも効率的

### 最適化テクニック

1. **パス操作**: 効率性のために`pathlib.Path`を使用
2. **バッチ操作**: 単一の呼び出しでディレクトリを作成
3. **遅延ロード**: 必要な時のみ設定を読み込む

## 設定管理

### Configuration Manager概要

MixSeek-Coreは、Pydantic Settingsベースの統一設定管理システム（Configuration Manager）を採用しています。

#### アーキテクチャ

```python
from mixseek.config import ConfigurationManager, OrchestratorSettings

# Configuration Manager初期化
manager = ConfigurationManager(
    cli_args={"timeout_per_team_seconds": 600},
    workspace=Path("/workspace"),
    environment="prod"
)

# 設定読み込み（優先順位: CLI > ENV > .env > TOML > defaults）
settings = manager.load_settings(OrchestratorSettings)
```

#### 優先順位チェーン

設定値は以下の優先順位で適用されます：

```
CLI引数 > 環境変数 > .env > TOML > デフォルト値
```

#### Article 9準拠

Configuration Managerは Article 9 (Data Accuracy Mandate) に完全準拠：

- **明示的なデータソース**: Pydantic スキーマから明示的にフィールド情報を取得
- **暗黙的デフォルトなし**: すべての値はスキーマまたはソースから取得
- **適切なエラー伝播**: 無効な設定時に明確なエラーメッセージ
- **ハードコード禁止**: 設定値のハードコードを排除

#### カスタム設定スキーマの作成

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class CustomSettings(BaseSettings):
    """カスタム設定スキーマ"""

    api_endpoint: str = Field(
        ...,
        description="APIエンドポイントURL"
    )
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="タイムアウト（秒）"
    )

    class Config:
        env_prefix = "MIXSEEK_CUSTOM__"
```

#### トレーサビリティ

各設定値の出所を追跡できます：

```python
# 設定値の出所を確認
trace = manager.get_trace_info(OrchestratorSettings, "workspace_path")
print(f"Value: {trace.value}")
print(f"Source: {trace.source_name}")  # cli/env/toml/default
```

詳細は [設定リファレンス](configuration-reference.md) を参照してください。

## セキュリティ強化

### 入力検証

1. **パストラバーサル防止**:
   ```python
   def validate_safe_path(path: Path) -> Path:
       resolved = path.resolve()
       # 許可されたディレクトリ外へのトラバーサルを防止
       if ".." in resolved.parts:
           raise ValueError("Path traversal not allowed")
       return resolved
   ```

2. **ファイル権限**: 操作前に書き込み権限を検証

3. **入力のサニタイズ**: すべてのユーザー提供文字列をクリーン

### セキュリティのベストプラクティス

- すべてのCLI入力を検証
- 絶対パスのみを使用
- ファイル操作前に権限をチェック
- 設定内容をサニタイズ
- セキュリティ関連の操作をログに記録

## Docker環境での開発

MixSeek-Coreは、開発環境（`dockerfiles/dev/`）とCI環境（`dockerfiles/ci/`）の2種類のDocker環境を提供します。

### 開発環境 vs CI環境

| 項目 | 開発環境 (`dev/`) | CI環境 (`ci/`) |
|------|------------------|----------------|
| **目的** | ローカル開発 | GitHub Actions CI |
| **Node.js** | ✅ あり (22.20.0) | ❌ なし |
| **AI Tools** | ✅ あり (claude-code, codex, gemini-cli) | ❌ なし |
| **エディタ** | ✅ あり (vim, nano) | ❌ なし |
| **Pythonバージョン** | 3.13系最新 | 3.13.9 (固定) |

### 日常の開発作業（開発環境）

```bash
# 開発セッションを開始
make -C dockerfiles/dev build && make -C dockerfiles/dev run
make -C dockerfiles/dev bash

# コンテナ内での一般的なワークフロー
make lint          # コード品質チェック
make format        # コードフォーマット
make unittest      # テスト実行
```

詳細は `../dockerfiles/README.ja.md` を参照してください。

### PR作成前のCI検証（CI環境）

PR作成前に、GitHub Actions CIと同じチェックをDocker CI環境で実行できます。

```bash
# Docker CI環境でチェックを実行
make -C dockerfiles/ci check

# Docker CI環境でより詳細なテストを実行（高速版、E2E除く）
make -C dockerfiles/ci quality-gate-fast
```

**`make -C dockerfiles/ci check`の実行内容**:
1. Ruff linting
2. コードフォーマットチェック
3. mypy型チェック

**`make -C dockerfiles/ci quality-gate-fast`の実行内容**:
1. Ruff linting
2. コードフォーマットチェック
3. pytestテスト実行（E2E除く）

**CI Dockerイメージの直接使用**:

```bash
# CI専用イメージのビルド
docker build -f dockerfiles/ci/Dockerfile -t mixseek-core-ci:latest .

# 個別チェックの実行
docker run --rm -v $(pwd):/app -w /app mixseek-core-ci:latest uv run ruff check .
docker run --rm -v $(pwd):/app -w /app mixseek-core-ci:latest uv run mypy src tests
docker run --rm -v $(pwd):/app -w /app mixseek-core-ci:latest uv run pytest -m "not e2e"
```

詳細は `../dockerfiles/ci/README.md` を参照してください。

### AI開発ツールの使用

開発環境には3つのAIコーディングアシスタントが含まれています：

```bash
# Claude Code（Anthropic）
make -C dockerfiles/dev claude-code ARG="analyze src/main.py"

# OpenAI Codex
make -C dockerfiles/dev codex ARG="generate function to parse JSON"

# Google Gemini CLI
make -C dockerfiles/dev gemini ARG="review src/main.py"
```

### デバッグ

```bash
# デバッグモードでスクリプトを実行
make -C dockerfiles/dev debug ARG="src/main.py"

# ポート5678でデバッガーがリッスン
```

### Streamlit UIの開発

Docker環境でStreamlit UIを開発する場合は、以下のドキュメントを参照してください：
- [Mixseek UIガイド](ui-guide.md) - UI操作方法と機能詳細
- [Docker + Streamlit UI統合](ui-docker.md) - Docker環境でのStreamlit起動とデプロイ

## トラブルシューティング

### よくある問題

1. **インポートエラー**: `pip install -e .`でパッケージがインストールされていることを確認
2. **権限エラー**: 対象ディレクトリの読み書き権限を確認
3. **テスト失敗**: 詳細な出力には`pytest -x -vv`を実行

### デバッグモード

```bash
# デバッグログを有効化
export MIXSEEK_DEBUG=1
mixseek command --option /path/to/target

# デバッグ出力付きでテストを実行
pytest -s --log-cli-level=DEBUG
```

### Docker関連の問題

Docker環境での問題については、以下を参照してください：
- [docker-setup.md](docker-setup.md) - セットアップとトラブルシューティング
- `../dockerfiles/README.ja.md` - 詳細な使用方法

## コントリビューション

### コードスタイル

- **行の長さ**: 119文字（ruff設定）
- **インポート**: ruffによる自動ソート
- **型ヒント**: すべての関数・メソッド・変数で必須（mypy strict準拠）
- **型チェック**: mypyエラーゼロが必須、`Any`型の使用を避ける
- **docstring**: Google形式

### プルリクエストチェックリスト

- [ ] すべてのテストが通る（`pytest`）
- [ ] コード品質チェックが通る（`ruff check && mypy src/`）
- [ ] mypy strict モードでエラーゼロ（`mypy --strict src/`）
- [ ] 新機能にテストがある
- [ ] ドキュメントが更新されている
- [ ] 新しいコードに型ヒントが追加されている
- [ ] `Any`型の使用を避け、具体的な型を指定している
- [ ] 型注釈がdocstringの記述と一致している

### リリースプロセス

1. `pyproject.toml`でバージョンを更新（`src/mixseek/__init__.py`は自動取得）
2. 完全なテストスイートを実行
3. CHANGELOG.mdを更新
4. リリースタグを作成
5. PyPIにビルド・公開

**Note**: バージョン番号は`pyproject.toml`の`version`フィールドで管理されます。`src/mixseek/__init__.py`では`importlib.metadata.version("mixseek-core")`を使用して自動取得します。

## 参照

追加の技術仕様と設計ドキュメントについては、プロジェクト仕様を参照してください：

- 機能仕様: `specs/005-command/spec.md`
- 実装計画: `specs/005-command/plan.md`
- クイックスタートガイド: `specs/005-command/quickstart.md`
- CLI仕様: `specs/005-command/contracts/cli-interface.md`
- データモデル: `specs/005-command/data-model.md`

Docker関連のドキュメント：

- Dockerセットアップガイド: [docker-setup.md](docker-setup.md)
- Docker開発環境詳細: `../dockerfiles/README.ja.md`