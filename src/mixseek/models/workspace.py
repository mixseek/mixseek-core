"""Workspace-related Pydantic models."""

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator

from mixseek.exceptions import ParentDirectoryNotFoundError, WorkspacePermissionError
from mixseek.utils.filesystem import validate_disk_space, validate_safe_path


class WorkspacePath(BaseModel):
    """
    Entity representing a workspace directory path.

    Validates path existence, permissions, and resolves symlinks.
    """

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
        # Security: Validate path for security issues
        try:
            secure_path = validate_safe_path(self.resolved_path)
            # Update resolved_path with the security-validated path
            self.resolved_path = secure_path
        except ValueError as e:
            raise ValueError(f"Security validation failed: {e}")

        # Check parent directory exists
        if not self.resolved_path.parent.exists():
            raise ParentDirectoryNotFoundError(str(self.resolved_path.parent))

        # Check write permissions
        if not os.access(self.resolved_path.parent, os.W_OK):
            raise WorkspacePermissionError(str(self.resolved_path.parent))

        # Security: Check disk space availability
        try:
            validate_disk_space(self.resolved_path, required_mb=10)
        except OSError as e:
            raise OSError(f"Disk space validation failed: {e}")

        return self

    @classmethod
    def from_cli(cls, path: str) -> "WorkspacePath":
        """Create WorkspacePath from CLI argument."""
        return cls(
            raw_path=path,
            resolved_path=Path(path).resolve(),
            source="cli",
        )

    @classmethod
    def from_env(cls, path: str) -> "WorkspacePath":
        """Create WorkspacePath from environment variable."""
        return cls(
            raw_path=path,
            resolved_path=Path(path).resolve(),
            source="env",
        )


class WorkspaceStructure(BaseModel):
    """
    Entity representing workspace directory structure.

    Manages workspace root and subdirectories (logs, configs, templates).
    """

    root: Path
    logs_dir: Path
    configs_dir: Path
    templates_dir: Path
    exists: bool

    @field_validator("logs_dir", "configs_dir", "templates_dir")
    @classmethod
    def validate_subdirectory(cls, v: Path, info: Any) -> Path:
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
            exists=root.exists(),
        )

    def create_directories(self) -> None:
        """Create all workspace directories."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.configs_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
