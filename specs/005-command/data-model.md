# Data Model: mixseekコマンド初期化機能

**Date**: 2025-10-16 (Updated: 2025-10-16)
**Feature**: mixseek init command
**Purpose**: このドキュメントは、機能仕様から抽出されたエンティティ、フィールド、関係性、検証ルールを定義します。

**Data Modeling Framework**: Pydantic v2 (BaseModel)

## Entities

### 1. WorkspacePath

**Description**: ワークスペースディレクトリのパスを表すエンティティ

**Fields**:
- `raw_path: str` - ユーザー指定の元のパス（環境変数またはCLIオプションから）
- `resolved_path: Path` - シンボリックリンクと相対パスを解決した絶対パス
- `source: Literal["cli", "env"]` - パスのソース（CLI引数または環境変数）

**Validation Rules**:
1. `raw_path` は空文字列であってはならない
2. `resolved_path` の親ディレクトリが存在しなければならない
3. `resolved_path` の親ディレクトリに書き込み権限がなければならない
4. シンボリックリンクの場合、解決可能でなければならない

**State Transitions**:
```
[User Input] → [Validation] → [Resolution] → [Verified Path]
                     ↓
                  [Error]
```

**Implementation**:
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
    
    @classmethod
    def from_cli(cls, path: str) -> "WorkspacePath":
        """Create WorkspacePath from CLI argument."""
        return cls(
            raw_path=path,
            resolved_path=Path(path).resolve(),
            source="cli"
        )
    
    @classmethod
    def from_env(cls, path: str) -> "WorkspacePath":
        """Create WorkspacePath from environment variable."""
        return cls(
            raw_path=path,
            resolved_path=Path(path).resolve(),
            source="env"
        )
```

---

### 2. WorkspaceStructure

**Description**: ワークスペースのディレクトリ構造を表すエンティティ

**Fields**:
- `root: Path` - ワークスペースのルートディレクトリ
- `logs_dir: Path` - ログディレクトリ (root / "logs")
- `configs_dir: Path` - 設定ディレクトリ (root / "configs")
- `templates_dir: Path` - テンプレートディレクトリ (root / "templates")
- `exists: bool` - ワークスペースが既に存在するかどうか

**Validation Rules**:
1. すべてのサブディレクトリは `root` の子でなければならない
2. `root` が存在する場合、`exists = True` でなければならない
3. 既存のワークスペースを上書きする場合、ユーザー確認が必要

**State Transitions**:
```
[New] → [Creating] → [Created]
           ↓
        [Error]

[Existing] → [Confirm Overwrite?] → [Yes] → [Re-creating] → [Created]
                      ↓
                    [No] → [Aborted]
```

**Implementation**:
```python
from pathlib import Path
from pydantic import BaseModel, field_validator

class WorkspaceStructure(BaseModel):
    root: Path
    logs_dir: Path
    configs_dir: Path
    templates_dir: Path
    exists: bool
    
    @field_validator("logs_dir", "configs_dir", "templates_dir")
    @classmethod
    def validate_subdirectory(cls, v: Path, info) -> Path:
        """Validate subdirectory is a child of root."""
        root = info.data.get("root")
        if root and not str(v).startswith(str(root)):
            raise ValueError(f"Subdirectory {v} must be child of root {root}")
        return v
    
    @classmethod
    def create(cls, root: Path) -> "WorkspaceStructure":
        """Create workspace structure from root path."""
        return cls(
            root=root,
            logs_dir=root / "logs",
            configs_dir=root / "configs",
            templates_dir=root / "templates",
            exists=root.exists()
        )
    
    def create_directories(self) -> None:
        """Create all workspace directories."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.configs_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
```

---

### 3. ProjectConfig

**Description**: TOMLファイルに格納されるプロジェクト設定を表すエンティティ

**Fields**:
- `project_name: str` - プロジェクト名（デフォルト: "mixseek-project"）
- `workspace_path: str` - ワークスペースの絶対パス
- `log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` - ログレベル
- `log_format: str` - ログフォーマット

**Validation Rules**:
1. `project_name` は空文字列であってはならない
2. `workspace_path` は絶対パスでなければならない
3. `log_level` は ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] のいずれかでなければならない

**Relationships**:
- `WorkspaceStructure` の `configs_dir` に保存される

**Implementation**:
```python
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, field_validator
import tomli_w

class ProjectConfig(BaseModel):
    project_name: str
    workspace_path: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Validate project_name is not empty."""
        if not v or v.strip() == "":
            raise ValueError("project_name cannot be empty")
        return v
    
    @field_validator("workspace_path")
    @classmethod
    def validate_workspace_path(cls, v: str) -> str:
        """Validate workspace_path is absolute."""
        path = Path(v)
        if not path.is_absolute():
            raise ValueError(f"workspace_path must be absolute: {v}")
        return v
    
    @classmethod
    def create_default(cls, workspace_path: Path) -> "ProjectConfig":
        """Create default project configuration."""
        return cls(
            project_name="mixseek-project",
            workspace_path=str(workspace_path.resolve())
        )
    
    def to_toml_dict(self) -> dict:
        """Convert to TOML-compatible dictionary."""
        return {
            "project": {
                "name": self.project_name,
                "workspace": self.workspace_path
            },
            "logging": {
                "level": self.log_level,
                "format": self.log_format
            }
        }
    
    def save(self, config_dir: Path) -> None:
        """Save configuration to TOML file."""
        config_file = config_dir / "config.toml"
        with open(config_file, "wb") as f:
            tomli_w.dump(self.to_toml_dict(), f)
```

---

### 4. InitResult

**Description**: `mixseek init` コマンドの実行結果を表すエンティティ

**Fields**:
- `success: bool` - 初期化が成功したかどうか
- `workspace_path: Path` - 作成されたワークスペースのパス
- `created_dirs: list[Path]` - 作成されたディレクトリのリスト
- `created_files: list[Path]` - 作成されたファイルのリスト
- `message: str` - ユーザーへのメッセージ
- `error: str | None` - エラーメッセージ（エラー時のみ）

**State Transitions**:
```
[Initializing] → [Success] → success=True, message="Workspace created"
                   ↓
                [Failure] → success=False, error="Error message"
```

**Implementation**:
```python
from pathlib import Path
from pydantic import BaseModel, Field
import typer

class InitResult(BaseModel):
    success: bool
    workspace_path: Path
    created_dirs: list[Path] = Field(default_factory=list)
    created_files: list[Path] = Field(default_factory=list)
    message: str = ""
    error: str | None = None
    
    @classmethod
    def success_result(
        cls,
        workspace_path: Path,
        created_dirs: list[Path],
        created_files: list[Path]
    ) -> "InitResult":
        """Create successful initialization result."""
        return cls(
            success=True,
            workspace_path=workspace_path,
            created_dirs=created_dirs,
            created_files=created_files,
            message=f"Workspace initialized successfully at: {workspace_path}"
        )
    
    @classmethod
    def error_result(cls, workspace_path: Path, error: str) -> "InitResult":
        """Create error initialization result."""
        return cls(
            success=False,
            workspace_path=workspace_path,
            error=error,
            message=f"Failed to initialize workspace: {error}"
        )
    
    def print_result(self) -> None:
        """Print result to stdout/stderr."""
        if self.success:
            typer.echo(self.message)
            typer.echo(f"Created directories: {len(self.created_dirs)}")
            typer.echo(f"Created files: {len(self.created_files)}")
        else:
            typer.echo(self.message, err=True)
```

---

## Entity Relationships

```
WorkspacePath
     ↓ (validates and resolves)
WorkspaceStructure
     ↓ (creates directories)
     ├─→ logs/
     ├─→ configs/
     │      ↓ (contains)
     │   ProjectConfig (config.toml)
     └─→ templates/
     
     ↓ (returns)
InitResult
```

## Validation Summary

| Entity | Key Validations | Pydantic Feature Used |
|--------|----------------|----------------------|
| WorkspacePath | Parent exists, Write permission, Symlink resolution | `@field_validator`, `@model_validator` |
| WorkspaceStructure | Subdirs are children of root, Overwrite confirmation | `@field_validator` |
| ProjectConfig | Non-empty name, Absolute path, Valid log level | `@field_validator`, `Literal` type |
| InitResult | Success/failure state consistency | `Field(default_factory=list)` |

## Pydantic v2 Benefits

1. **Runtime Validation**: すべてのフィールドが初期化時に自動検証される
2. **Type Safety**: Article 16（Type Checking Imperative）に完全準拠
3. **Auto Documentation**: `model_json_schema()` でJSONスキーマを自動生成
4. **Serialization**: `model_dump()` と `model_dump_json()` で簡単にシリアライズ
5. **Performance**: Pydantic v2はRust実装により高速化
6. **Immutability Option**: `frozen=True` で不変オブジェクトを作成可能

すべてのエンティティはPydantic v2の `BaseModel` を使用し、Article 16（Type Checking Imperative）に準拠します。
