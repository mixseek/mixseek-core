"""Filesystem utilities for path validation and operations."""

import ctypes
import os
import platform
import re
from pathlib import Path


def validate_parent_exists(path: Path) -> None:
    """
    Validate that parent directory exists.

    Args:
        path: Path to validate

    Raises:
        ValueError: If parent directory does not exist
    """
    if not path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {path.parent}")


def validate_write_permission(path: Path) -> None:
    """
    Validate write permission on parent directory.

    Args:
        path: Path to validate

    Raises:
        PermissionError: If no write permission on parent directory
    """
    if not os.access(path.parent, os.W_OK):
        raise PermissionError(f"No write permission: {path.parent}")


def resolve_symlinks(path: Path) -> Path:
    """
    Resolve symbolic links and return absolute path.

    Args:
        path: Path that may contain symbolic links

    Returns:
        Resolved absolute path
    """
    return path.resolve()


def validate_safe_path(path: Path) -> Path:
    """
    Validate path for security issues and return resolved safe path.

    Performs multiple security checks:
    - Path traversal prevention (.. components)
    - Dangerous character filtering
    - Symbolic link resolution
    - Absolute path enforcement

    Args:
        path: Path to validate and secure

    Returns:
        Resolved absolute path that passed security checks

    Raises:
        ValueError: If path contains security risks
    """
    # Convert to Path object if string
    if isinstance(path, str):
        path = Path(path)

    # Check for path traversal attempts before resolving
    if ".." in path.parts:
        raise ValueError(f"Path traversal detected in path: {path}")

    # Resolve symbolic links and make absolute
    resolved_path = path.resolve()
    path_str = str(resolved_path)

    # Check for dangerous characters that could be used for injection
    dangerous_chars = ["|", "&", ";", "$", "`", "(", ")", "[", "]", "{", "}", "\\x00"]
    for char in dangerous_chars:
        if char in path_str:
            raise ValueError(f"Dangerous character '{char}' detected in path: {path}")

    # Ensure path doesn't try to access sensitive system locations
    sensitive_paths = [
        "/etc",
        "/proc",
        "/sys",
        "/dev",
        "/root",
        "/boot",
        "C:\\Windows",
        "C:\\System32",
        "C:\\Users\\Administrator",
    ]

    path_lower = path_str.lower()
    for sensitive in sensitive_paths:
        if path_lower.startswith(sensitive.lower()):
            raise ValueError(f"Access to sensitive system path not allowed: {path}")

    return resolved_path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem operations

    Raises:
        ValueError: If filename is empty after sanitization
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")

    # Remove or replace dangerous characters
    # Keep only alphanumeric, dots, hyphens, underscores, and spaces
    sanitized = re.sub(r"[^\w\s\-_\.]", "", filename)

    # Remove multiple spaces and trim
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    # Ensure filename isn't empty after sanitization
    if not sanitized:
        raise ValueError("Filename contains only invalid characters")

    # Prevent reserved names on Windows
    reserved_names = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]

    name_without_ext = sanitized.split(".")[0].upper()
    if name_without_ext in reserved_names:
        sanitized = f"_{sanitized}"

    # Limit length (most filesystems support 255 chars)
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        max_name_len = 255 - len(ext)
        sanitized = name[:max_name_len] + ext

    return sanitized


def validate_disk_space(path: Path, required_mb: int = 10) -> None:
    """
    Validate that sufficient disk space is available.

    This function uses platform-specific methods for disk space checking:
    - Unix/Linux/macOS: os.statvfs
    - Windows: GetDiskFreeSpaceExW via ctypes

    If disk space checking is unavailable on the platform or fails,
    the validation is silently skipped to ensure cross-platform compatibility.

    Args:
        path: Path to check disk space for
        required_mb: Required space in megabytes

    Raises:
        OSError: If insufficient disk space available
    """
    try:
        # Get parent directory for space check
        check_path = path.parent if not path.exists() else path
        if not check_path.exists():
            check_path = Path.cwd()

        available_bytes = None

        # Unix-like systems (Linux, macOS, BSD, etc.)
        if hasattr(os, "statvfs"):
            stat = os.statvfs(check_path)
            available_bytes = stat.f_bavail * stat.f_frsize

        # Windows systems
        elif platform.system() == "Windows" and hasattr(ctypes, "windll"):
            free_bytes = ctypes.c_ulonglong(0)
            # Type ignore needed for Windows-only windll attribute (unused-ignore on non-Windows)
            result = ctypes.windll.kernel32.GetDiskFreeSpaceExW(  # type: ignore[attr-defined,unused-ignore]
                ctypes.c_wchar_p(str(check_path)), None, None, ctypes.pointer(free_bytes)
            )
            if result:
                available_bytes = free_bytes.value

        # Check if we successfully retrieved disk space information
        if available_bytes is not None:
            required_bytes = required_mb * 1024 * 1024

            if available_bytes < required_bytes:
                available_mb = available_bytes / (1024 * 1024)
                raise OSError(f"Insufficient disk space. Required: {required_mb}MB, Available: {available_mb:.1f}MB")

    except (OSError, AttributeError) as e:
        # On systems where disk space checking is unavailable or fails,
        # we skip the check to ensure compatibility across different platforms
        # Re-raise if it's an insufficient disk space error (not a platform compatibility issue)
        if "Insufficient disk space" in str(e):
            raise
        pass
