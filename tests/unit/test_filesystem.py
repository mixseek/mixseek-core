"""Unit tests for filesystem utilities."""

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest import MonkeyPatch

from mixseek.utils.filesystem import (
    resolve_symlinks,
    validate_parent_exists,
    validate_safe_path,
    validate_write_permission,
)


class TestValidateParentExists:
    """Test validate_parent_exists function."""

    def test_validate_parent_exists_success(self, tmp_path: Path) -> None:
        """Test validation passes when parent directory exists."""
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        test_path = parent_dir / "child"

        # Should not raise
        validate_parent_exists(test_path)

    def test_validate_parent_exists_raises_when_parent_missing(self, tmp_path: Path) -> None:
        """Test ValueError is raised when parent directory doesn't exist."""
        nonexistent_parent = tmp_path / "nonexistent"
        test_path = nonexistent_parent / "child"

        with pytest.raises(ValueError) as exc_info:
            validate_parent_exists(test_path)

        assert "Parent directory does not exist" in str(exc_info.value)
        assert str(nonexistent_parent) in str(exc_info.value)

    def test_validate_parent_exists_with_nested_path(self, tmp_path: Path) -> None:
        """Test validation with deeply nested path structure."""
        nested_parent = tmp_path / "level1" / "level2" / "level3"
        nested_parent.mkdir(parents=True)
        test_path = nested_parent / "child"

        # Should not raise
        validate_parent_exists(test_path)

    def test_validate_parent_exists_absolute_path(self, tmp_path: Path) -> None:
        """Test validation with absolute path."""
        test_path = tmp_path / "child"  # tmp_path is absolute

        # Should not raise since tmp_path exists
        validate_parent_exists(test_path)


class TestValidateWritePermission:
    """Test validate_write_permission function."""

    def test_validate_write_permission_success(self, tmp_path: Path) -> None:
        """Test validation passes when write permission exists."""
        test_path = tmp_path / "child"

        # Should not raise
        validate_write_permission(test_path)

    def test_validate_write_permission_raises_on_no_permission(self, tmp_path: Path) -> None:
        """Test PermissionError is raised when no write permission."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        try:
            # Make directory read-only
            readonly_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
            test_path = readonly_dir / "child"

            with pytest.raises(PermissionError) as exc_info:
                validate_write_permission(test_path)

            assert "No write permission" in str(exc_info.value)
            assert str(readonly_dir) in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

    @patch("os.access")
    def test_validate_write_permission_with_mocked_access(self, mock_access: MagicMock, tmp_path: Path) -> None:
        """Test validation using mocked os.access."""
        test_path = tmp_path / "child"

        # Mock os.access to return False (no write permission)
        mock_access.return_value = False

        with pytest.raises(PermissionError):
            validate_write_permission(test_path)

        # Verify os.access was called with correct parameters
        mock_access.assert_called_once_with(test_path.parent, os.W_OK)

    @patch("os.access")
    def test_validate_write_permission_success_with_mock(self, mock_access: MagicMock, tmp_path: Path) -> None:
        """Test successful validation using mocked os.access."""
        test_path = tmp_path / "child"

        # Mock os.access to return True (write permission exists)
        mock_access.return_value = True

        # Should not raise
        validate_write_permission(test_path)

        mock_access.assert_called_once_with(test_path.parent, os.W_OK)


class TestResolveSymlinks:
    """Test resolve_symlinks function."""

    def test_resolve_symlinks_regular_path(self, tmp_path: Path) -> None:
        """Test resolving regular path without symlinks."""
        test_path = tmp_path / "regular"
        test_path.mkdir()

        resolved = resolve_symlinks(test_path)

        assert resolved == test_path.resolve()
        assert resolved.is_absolute()

    def test_resolve_symlinks_with_symlink(self, tmp_path: Path) -> None:
        """Test resolving path with symbolic link."""
        # Create real directory
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        # Create symlink
        symlink = tmp_path / "symlink"
        symlink.symlink_to(real_dir)

        resolved = resolve_symlinks(symlink)

        assert resolved == real_dir.resolve()
        assert resolved.is_absolute()

    def test_resolve_symlinks_relative_path(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test resolving relative path."""
        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Create subdirectory
        subdir = Path("subdir")
        (tmp_path / subdir).mkdir()

        resolved = resolve_symlinks(subdir)

        assert resolved.is_absolute()
        assert resolved == (tmp_path / subdir).resolve()

    def test_resolve_symlinks_nested_symlinks(self, tmp_path: Path) -> None:
        """Test resolving nested symbolic links."""
        # Create real directory
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        # Create first symlink
        symlink1 = tmp_path / "symlink1"
        symlink1.symlink_to(real_dir)

        # Create second symlink pointing to first symlink
        symlink2 = tmp_path / "symlink2"
        symlink2.symlink_to(symlink1)

        resolved = resolve_symlinks(symlink2)

        assert resolved == real_dir.resolve()
        assert resolved.is_absolute()

    def test_resolve_symlinks_current_directory(self) -> None:
        """Test resolving current directory."""
        current = Path(".")

        resolved = resolve_symlinks(current)

        assert resolved.is_absolute()
        assert resolved == current.resolve()

    def test_resolve_symlinks_parent_directory(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test resolving parent directory reference."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        parent_ref = Path("..")

        resolved = resolve_symlinks(parent_ref)

        assert resolved.is_absolute()
        assert resolved == tmp_path.resolve()


class TestValidateSafePath:
    """Test validate_safe_path function."""

    def test_validate_safe_path_success(self, tmp_path: Path) -> None:
        """Test validation passes with safe path."""
        safe_path = tmp_path / "safe" / "path"
        safe_path.parent.mkdir(parents=True)

        result = validate_safe_path(safe_path)

        assert result.is_absolute()
        assert result == safe_path.resolve()

    def test_validate_safe_path_with_string_input(self, tmp_path: Path) -> None:
        """Test validation accepts string input."""
        safe_path = tmp_path / "safe"
        safe_path.mkdir()

        result = validate_safe_path(safe_path)

        assert result.is_absolute()
        assert result == safe_path.resolve()

    def test_validate_safe_path_detects_parent_traversal(self, tmp_path: Path) -> None:
        """Test detection of .. in path components."""
        # Direct parent reference
        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(Path("..") / "etc" / "passwd")
        assert "Path traversal detected" in str(exc_info.value)

    def test_validate_safe_path_detects_mid_path_traversal(self, tmp_path: Path) -> None:
        """Test detection of .. in middle of path."""
        traversal_path = tmp_path / "foo" / ".." / "bar"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(traversal_path)
        assert "Path traversal detected" in str(exc_info.value)

    def test_validate_safe_path_allows_double_dots_in_filename(self, tmp_path: Path) -> None:
        """Test that filenames containing .. (but not as a component) are allowed."""
        # Create a directory with .. in the name
        safe_dir = tmp_path / "my..project"
        safe_dir.mkdir()

        # This should succeed because ".." is not a path component
        result = validate_safe_path(safe_dir)

        assert result.is_absolute()
        assert result == safe_dir.resolve()

    def test_validate_safe_path_allows_double_dots_in_middle_of_name(self, tmp_path: Path) -> None:
        """Test filenames with .. in the middle are allowed."""
        safe_file = tmp_path / "file..name.txt"
        safe_file.parent.mkdir(parents=True, exist_ok=True)

        result = validate_safe_path(safe_file)

        assert result.is_absolute()
        assert "file..name.txt" in str(result)

    def test_validate_safe_path_detects_pipe_character(self, tmp_path: Path) -> None:
        """Test detection of pipe character."""
        dangerous_path = tmp_path / "file|command"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(dangerous_path)
        assert "Dangerous character '|' detected" in str(exc_info.value)

    def test_validate_safe_path_detects_semicolon(self, tmp_path: Path) -> None:
        """Test detection of semicolon character."""
        dangerous_path = tmp_path / "file;rm -rf"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(dangerous_path)
        assert "Dangerous character ';' detected" in str(exc_info.value)

    def test_validate_safe_path_detects_backtick(self, tmp_path: Path) -> None:
        """Test detection of backtick character."""
        dangerous_path = tmp_path / "file`whoami`"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(dangerous_path)
        assert "Dangerous character '`' detected" in str(exc_info.value)

    def test_validate_safe_path_detects_dollar_sign(self, tmp_path: Path) -> None:
        """Test detection of dollar sign character."""
        dangerous_path = tmp_path / "file$USER"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(dangerous_path)
        assert "Dangerous character '$' detected" in str(exc_info.value)

    def test_validate_safe_path_detects_ampersand(self, tmp_path: Path) -> None:
        """Test detection of ampersand character."""
        dangerous_path = tmp_path / "file&command"

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(dangerous_path)
        assert "Dangerous character '&' detected" in str(exc_info.value)

    def test_validate_safe_path_blocks_etc_directory(self) -> None:
        """Test blocking access to /etc directory."""
        sensitive_path = Path("/etc/passwd")

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(sensitive_path)
        assert "Access to sensitive system path not allowed" in str(exc_info.value)

    def test_validate_safe_path_blocks_proc_directory(self) -> None:
        """Test blocking access to /proc directory."""
        sensitive_path = Path("/proc/self/environ")

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(sensitive_path)
        assert "Access to sensitive system path not allowed" in str(exc_info.value)

    def test_validate_safe_path_blocks_sys_directory(self) -> None:
        """Test blocking access to /sys directory."""
        sensitive_path = Path("/sys/kernel")

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(sensitive_path)
        assert "Access to sensitive system path not allowed" in str(exc_info.value)

    def test_validate_safe_path_blocks_root_directory(self) -> None:
        """Test blocking access to /root directory."""
        sensitive_path = Path("/root/.ssh/id_rsa")

        with pytest.raises(ValueError) as exc_info:
            validate_safe_path(sensitive_path)
        assert "Access to sensitive system path not allowed" in str(exc_info.value)

    def test_validate_safe_path_resolves_symlinks(self, tmp_path: Path) -> None:
        """Test that symbolic links are resolved."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        real_file = real_dir / "file.txt"

        symlink = tmp_path / "link"
        symlink.symlink_to(real_dir)
        symlink_file = symlink / "file.txt"

        result = validate_safe_path(symlink_file)

        assert result.is_absolute()
        assert result == real_file.resolve()
        # Ensure symlink is resolved (no 'link' in path)
        assert "link" not in result.parts or result.parts[-2] == "real"
