"""Result models for CLI operations."""

from pathlib import Path

import typer
from pydantic import BaseModel, Field


class InitResult(BaseModel):
    """
    Entity representing the result of mixseek init command execution.

    Tracks success/failure, created files/directories, and error messages.
    """

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
        created_files: list[Path],
    ) -> "InitResult":
        """Create successful initialization result."""
        return cls(
            success=True,
            workspace_path=workspace_path,
            created_dirs=created_dirs,
            created_files=created_files,
            message=f"Workspace initialized successfully at: {workspace_path}",
        )

    @classmethod
    def error_result(cls, workspace_path: Path, error: str) -> "InitResult":
        """Create error initialization result."""
        return cls(
            success=False,
            workspace_path=workspace_path,
            error=error,
            message=f"Failed to initialize workspace: {error}",
        )

    def print_result(self) -> None:
        """Print result to stdout/stderr."""
        if self.success:
            typer.echo(self.message)
            typer.echo(f"Created directories: {len(self.created_dirs)}")
            typer.echo(f"Created files: {len(self.created_files)}")
        else:
            typer.echo(self.message, err=True)
