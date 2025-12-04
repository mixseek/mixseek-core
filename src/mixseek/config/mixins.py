"""Configuration mixins for reusable validation logic.

This module provides mixin classes for common validation patterns
to eliminate code duplication across settings classes (Article 10: DRY).
"""

from pathlib import Path

from pydantic import field_validator


class WorkspaceValidatorMixin:
    """ワークスペースパスのバリデーションを提供するミックスイン。

    このミックスインは workspace_path フィールドのバリデーションロジックを提供します。
    OrchestratorSettings と UISettings で重複していたコード（100%一致）を統合します。

    Constitution Compliance:
        - Article 10 (DRY): 重複コードの削減
        - Article 9 (Data Accuracy): 明示的なエラー伝播
        - Article 8 (Code Quality): 型安全性の維持

    Example:
        >>> from pydantic import BaseSettings, Field
        >>> class MySettings(WorkspaceValidatorMixin, BaseSettings):
        ...     workspace_path: Path = Field(..., description="Workspace directory")
        >>> settings = MySettings(workspace_path=Path("/tmp"))
        >>> # workspace_path の存在とディレクトリチェックが自動的に実行される
    """

    @field_validator("workspace_path")
    @classmethod
    def validate_workspace(cls, v: Path) -> Path:
        """ワークスペースパスの存在チェック。

        Args:
            v: ワークスペースパス

        Returns:
            バリデーション済みのパス

        Raises:
            ValueError: パスが存在しない、またはディレクトリでない場合
        """
        if not v.exists():
            raise ValueError(f"Workspace path does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Workspace path is not a directory: {v}")
        return v
