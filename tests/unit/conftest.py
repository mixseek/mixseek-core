"""Shared fixtures for unit tests.

This module provides common fixtures used across unit tests,
including workspace path setup for Agent initialization tests.
"""

import pytest


@pytest.fixture(autouse=True)
def set_workspace_env(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set MIXSEEK_WORKSPACE environment variable for tests requiring workspace path.

    This fixture automatically sets up a temporary workspace path for all unit tests,
    which is required by MemberAgentLogger during agent initialization.
    """
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
