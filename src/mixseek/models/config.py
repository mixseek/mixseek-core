"""Configuration model for MixSeek projects."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

from mixseek.config.constants import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL, DEFAULT_PROJECT_NAME


class ProjectConfig(BaseModel):
    """
    Entity representing project configuration stored in TOML file.

    Contains project name, workspace path, and logging settings.
    """

    project_name: str
    workspace_path: str
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = DEFAULT_LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT

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
            project_name=DEFAULT_PROJECT_NAME,
            workspace_path=str(workspace_path.resolve()),
        )
