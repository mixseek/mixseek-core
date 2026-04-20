"""Result models for CLI operations."""

from pathlib import Path

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
        # Why: cli.output は observability 経由で config/models を再帰的に import するため、
        # module-level import にすると mixseek.models.__init__ → result → cli.output の循環になる。
        # 呼び出し時 import で循環を回避する。
        from mixseek.cli.output import cli_echo

        if self.success:
            cli_echo(
                self.message,
                event="init.result_success",
                workspace_path=str(self.workspace_path),
                created_dir_count=len(self.created_dirs),
                created_file_count=len(self.created_files),
            )
            cli_echo(
                f"Created directories: {len(self.created_dirs)}",
                event="init.result_dirs",
                created_dir_count=len(self.created_dirs),
            )
            cli_echo(
                f"Created files: {len(self.created_files)}",
                event="init.result_files",
                created_file_count=len(self.created_files),
            )
        else:
            cli_echo(
                self.message,
                err=True,
                event="init.result_error",
                workspace_path=str(self.workspace_path),
                error=self.error,
            )
