"""Custom exceptions for MixSeek."""


class WorkspacePathNotSpecifiedError(ValueError):
    """
    Raised when workspace path is not specified via CLI or environment variable.

    This exception indicates that the user must provide a workspace path either through:
    - CLI option (--workspace)
    - Environment variable (MIXSEEK_WORKSPACE)
    """

    def __init__(self, env_var_name: str = "MIXSEEK_WORKSPACE"):
        """
        Initialize WorkspacePathNotSpecifiedError.

        Args:
            env_var_name: Name of the environment variable for workspace path
        """
        super().__init__(
            f"Workspace path not specified. Use --workspace option or set {env_var_name} environment variable."
        )
        self.env_var_name = env_var_name


class ParentDirectoryNotFoundError(ValueError):
    """
    Raised when the parent directory of the workspace does not exist.

    This exception indicates that the parent directory must be created before
    initializing the workspace, or a different location should be chosen.
    """

    def __init__(self, parent_path: str):
        """
        Initialize ParentDirectoryNotFoundError.

        Args:
            parent_path: Path to the non-existent parent directory
        """
        super().__init__(f"Parent directory does not exist: {parent_path}")
        self.parent_path = parent_path


class WorkspacePermissionError(PermissionError):
    """
    Raised when there is no write permission for the workspace parent directory.

    This exception indicates that:
    - Directory permissions should be checked
    - A different path with proper permissions should be chosen
    """

    def __init__(self, parent_path: str):
        """
        Initialize WorkspacePermissionError.

        Args:
            parent_path: Path to the directory without write permission
        """
        super().__init__(f"No write permission: {parent_path}")
        self.parent_path = parent_path
