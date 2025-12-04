# Research: mixseekコマンド初期化機能

**Date**: 2025-10-16
**Feature**: mixseek init command implementation
**Purpose**: このドキュメントは、Technical Contextで特定された技術選択とベストプラクティスの調査結果をまとめます。

## 1. CLI Framework Selection: Typer

### Decision
**Typer** (https://typer.tiangolo.com/) を採用

### Rationale
1. **Type Hints Native**: Python 3.6+の型ヒントを完全サポートし、Article 16（Type Checking Imperative）に準拠
2. **Intuitive API**: 関数ベースの宣言的インターフェースでコード量を削減
3. **Auto Documentation**: 型ヒントとdocstringから自動的に`--help`を生成
4. **Click Based**: 実績のあるClickライブラリ上に構築され、安定性が高い
5. **Validation**: Pydanticとの統合により、入力検証が容易

### Alternatives Considered
- **Click**: より低レベルだが冗長、型ヒントサポートが限定的
- **argparse**: 標準ライブラリだが、冗長でモダンなAPIではない
- **Fire**: 自動CLIだが、制御が限定的で、明示的なインターフェース設計が困難

### Implementation Pattern
```python
import typer
from pathlib import Path
from typing import Optional

app = typer.Typer()

@app.command()
def init(
    workspace: Optional[Path] = typer.Option(
        None,
        "--workspace", "-w",
        help="Workspace directory path"
    )
) -> None:
    """Initialize MixSeek workspace."""
    # Implementation
```

## 2. TOML File Generation

### Decision
**tomli_w** (https://github.com/hukkin/tomli_w) を採用

### Rationale
1. **TOML 1.0.0 Compliant**: 最新のTOML仕様に準拠
2. **Write-Only Focus**: ファイル書き込みに特化し、軽量
3. **Type Safe**: Pythonの dict/list から TOML への変換が型安全
4. **Standard Library Alignment**: Python 3.11+ の tomllib（読み取り専用）と互換性あり

### Alternatives Considered
- **toml**: 古い実装、TOML 0.5仕様、メンテナンス終了
- **tomlkit**: 高機能だがオーバーキル、コメント保持機能は不要
- **tomli**: 読み取り専用、書き込みには tomli_w が必要

### Implementation Pattern
```python
import tomli_w
from pathlib import Path

def generate_sample_config(workspace_path: Path, project_name: str) -> None:
    config = {
        "project": {
            "name": project_name,
            "workspace": str(workspace_path.resolve())
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    config_file = workspace_path / "configs" / "config.toml"
    with open(config_file, "wb") as f:
        tomli_w.dump(config, f)
```

## 3. Data Validation Framework: Pydantic v2

### Decision
**Pydantic v2** (https://docs.pydantic.dev/latest/) を採用

### Rationale
1. **Runtime Validation**: フィールド初期化時に自動的にバリデーションを実行
2. **Type Safety**: Article 16（Type Checking Imperative）に完全準拠、mypy互換
3. **Declarative Validators**: `@field_validator` と `@model_validator` でバリデーションロジックを明示的に定義
4. **Rich Error Messages**: バリデーションエラー時に詳細なエラーメッセージを自動生成
5. **Serialization**: `model_dump()` / `model_dump_json()` で簡単にシリアライズ
6. **Performance**: Rust実装により、従来のPydantic v1より高速
7. **JSON Schema Generation**: `model_json_schema()` でAPIドキュメント自動生成

### Alternatives Considered
- **dataclass**: 標準ライブラリだがランタイムバリデーションなし、手動検証が必要
- **attrs**: 軽量だが型ヒントサポートが限定的、Pydanticほど豊富な機能がない
- **marshmallow**: シリアライゼーション特化、型ヒントネイティブでない

### Why Not Dataclass?
データクラスは軽量だが、以下の課題がある：
1. **バリデーション不足**: `__post_init__` で手動検証が必要、エラーハンドリングが煩雑
2. **型変換なし**: 文字列から `Path` への自動変換なし
3. **エラーメッセージ**: 詳細なバリデーションエラーを手動で実装する必要がある
4. **ネストされた検証**: 複数フィールド間の検証ロジックが複雑化

Pydantic v2は、これらの課題をすべて解決し、Article 8（Code Quality Standards）とArticle 16（Type Checking Imperative）に準拠します。

### Implementation Pattern
```python
from pathlib import Path
from typing import Literal
import os
from pydantic import BaseModel, field_validator, model_validator

class WorkspacePath(BaseModel):
    raw_path: str
    resolved_path: Path
    source: Literal["cli", "env"]

    @field_validator("raw_path")
    @classmethod
    def validate_raw_path(cls, v: str) -> str:
        """Validate raw_path is not empty."""
        if not v or v.strip() == "":
            raise ValueError("raw_path cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_path(self) -> "WorkspacePath":
        """Validate workspace path after initialization."""
        if not self.resolved_path.parent.exists():
            raise ValueError(f"Parent directory does not exist: {self.resolved_path.parent}")

        if not os.access(self.resolved_path.parent, os.W_OK):
            raise PermissionError(f"No write permission: {self.resolved_path.parent}")

        return self
```

### Key Features Used
1. **Field Validators**: 個別フィールドの検証（例: `raw_path` の空文字チェック）
2. **Model Validators**: 複数フィールド間の検証（例: パスの存在確認と権限チェック）
3. **Literal Types**: 型安全な列挙値（例: `source: Literal["cli", "env"]`）
4. **Factory Methods**: `@classmethod` でインスタンス生成パターンを提供（例: `from_cli()`, `from_env()`）

## 4. Cross-Platform Path Handling

### Decision
**pathlib.Path** (標準ライブラリ) を使用

### Rationale
1. **OS Agnostic**: Linux/macOS/Windowsで自動的にパス区切り文字を処理
2. **Type Safe**: Pathオブジェクトにより、文字列操作のエラーを防ぐ
3. **Rich API**: exists(), resolve(), mkdir() など豊富なメソッド
4. **Standard Library**: 外部依存なし

### Key Operations
1. **Path Resolution**: `Path.resolve()` でシンボリックリンクと相対パスを解決
2. **Directory Creation**: `Path.mkdir(parents=True, exist_ok=True)` で安全に作成
3. **Permission Check**: `os.access(path, os.W_OK)` で書き込み権限確認

### Implementation Pattern
```python
from pathlib import Path
import os

def create_workspace(workspace_path: str) -> Path:
    # Resolve symbolic links and make absolute
    path = Path(workspace_path).resolve()
    
    # Check parent exists
    if not path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {path.parent}")
    
    # Check write permission
    if not os.access(path.parent, os.W_OK):
        raise PermissionError(f"No write permission: {path.parent}")
    
    # Create workspace and subdirectories
    path.mkdir(parents=True, exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    (path / "configs").mkdir(exist_ok=True)
    (path / "templates").mkdir(exist_ok=True)
    
    return path
```

## 5. Environment Variable Handling

### Decision
**os.environ** (標準ライブラリ) + **環境変数優先順位制御**

### Rationale
1. **Standard**: Python標準の環境変数アクセス
2. **Explicit Priority**: コマンドラインオプション > 環境変数 の優先順位を明示的に実装
3. **Error Handling**: 環境変数未設定時のエラーメッセージを明確化

### Priority Logic
```python
import os
from pathlib import Path
from typing import Optional

def get_workspace_path(cli_arg: Optional[Path]) -> Path:
    """
    Get workspace path with priority:
    1. CLI argument (--workspace)
    2. Environment variable (MIXSEEK_WORKSPACE)
    3. Error if neither provided
    """
    if cli_arg:
        return cli_arg
    
    env_workspace = os.environ.get("MIXSEEK_WORKSPACE")
    if env_workspace:
        return Path(env_workspace)
    
    raise ValueError(
        "Workspace path not specified. "
        "Use --workspace option or set MIXSEEK_WORKSPACE environment variable."
    )
```

## 6. Error Handling Strategy

### Decision
**明示的エラー + Rich Error Messages**

### Rationale
1. **User-Friendly**: エラーメッセージに解決策を含める（SC-004: 90%のユーザーが対処可能）
2. **Fail Fast**: エラーを早期に検出し、部分的な初期化を防ぐ
3. **Stderr Output**: Article 2に準拠し、エラーはstderrに出力

### Error Categories
1. **Path Errors**: 親ディレクトリ不在、書き込み権限なし
2. **Workspace Conflicts**: 既存ディレクトリの上書き確認
3. **File I/O Errors**: TOML生成失敗、ディスク容量不足

### Implementation Pattern
```python
import sys
import typer

def handle_error(error: Exception) -> None:
    """Handle errors with user-friendly messages."""
    if isinstance(error, PermissionError):
        typer.echo(
            f"Error: {error}\n"
            f"Solution: Check directory permissions or choose a different path.",
            err=True
        )
    elif isinstance(error, FileExistsError):
        typer.echo(
            f"Error: Workspace already exists: {error}\n"
            f"Solution: Use a different path or remove the existing workspace.",
            err=True
        )
    else:
        typer.echo(f"Error: {error}", err=True)
    
    sys.exit(1)
```

## 7. Testing Strategy

### Decision
**pytest + pytest-mock + 実ファイルシステム統合テスト**

### Rationale
1. **Integration-First**: Article 7に従い、実ファイルシステムを使用
2. **Contract Tests**: CLI インターフェース契約をテスト
3. **Unit Tests**: Utils層の単体テスト
4. **Mock Sparingly**: 環境変数とユーザー入力のみモック

### Test Structure
```
tests/
├── contract/
│   └── test_init_contract.py    # CLI exit codes, stdout/stderr
├── integration/
│   └── test_init_integration.py # Real filesystem operations
└── unit/
    ├── test_filesystem.py       # Path handling logic
    ├── test_env.py               # Environment variable priority
    └── test_templates.py         # TOML generation
```

### Sample Test
```python
import pytest
from pathlib import Path
from typer.testing import CliRunner
from mixseek.cli.main import app

runner = CliRunner()

def test_init_creates_workspace(tmp_path: Path):
    """Test workspace creation with all subdirectories."""
    workspace = tmp_path / "test-workspace"
    
    result = runner.invoke(app, ["init", "--workspace", str(workspace)])
    
    assert result.exit_code == 0
    assert workspace.exists()
    assert (workspace / "logs").is_dir()
    assert (workspace / "configs").is_dir()
    assert (workspace / "templates").is_dir()
    assert (workspace / "configs" / "config.toml").is_file()
```

## 8. Configuration File Template

### Decision
**プロジェクト名フィールド + コメント付きTOML**

### Sample Config Structure
```toml
# MixSeek Project Configuration
# Generated by: mixseek init

[project]
# Project name - edit this to match your project
name = "mixseek-project"

# Workspace directory path
workspace = "/path/to/workspace"

[logging]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Log message format
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Additional configuration sections can be added here
```

### Rationale
1. **Editable**: ユーザーが簡単に編集可能
2. **Self-Documenting**: コメントで各設定項目を説明
3. **Extensible**: 将来の設定項目追加が容易

## Summary

| Decision Area | Selected Technology | Key Benefit |
|---------------|---------------------|-------------|
| CLI Framework | Typer | Type safety + auto help generation |
| TOML Generation | tomli_w | TOML 1.0 compliance + lightweight |
| Data Validation | Pydantic v2 | Runtime validation + type safety |
| Path Handling | pathlib.Path | Cross-platform + type safe |
| Environment Variables | os.environ | Standard + explicit priority |
| Testing | pytest + real FS | Integration-first approach |
| Error Handling | Rich messages | 90% user self-service (SC-004) |

すべての技術選択は、Constitution（Article 1-15）とSuccess Criteria（SC-001からSC-006）に準拠しています。
