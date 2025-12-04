"""Tests for app.py entrypoint."""

from pathlib import Path

import pytest


def test_app_entrypoint_exists() -> None:
    """Test that app.py exists in mixseek_ui directory."""
    app_path = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "app.py"
    assert app_path.exists(), "app.py should exist as the Streamlit entrypoint"


def test_app_validates_workspace_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that app.py validates MIXSEEK_WORKSPACE environment variable."""
    monkeypatch.delenv("MIXSEEK_WORKSPACE", raising=False)

    app_path = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "app.py"
    with open(app_path) as f:
        content = f.read()

    # Verify that app imports workspace utilities
    assert "from mixseek.ui.utils.workspace import" in content or "import mixseek.ui.utils.workspace" in content


def test_app_defines_pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that app.py defines st.Page objects for navigation."""
    # Set up environment
    monkeypatch.setenv("MIXSEEK_WORKSPACE", str(tmp_path))
    (tmp_path / "configs").mkdir()
    (tmp_path / "duckdb").mkdir()

    app_path = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "app.py"
    with open(app_path) as f:
        content = f.read()

    # Verify page definitions
    assert "st.Page(" in content, "app.py should define pages using st.Page()"
    assert "st.navigation(" in content, "app.py should use st.navigation() for routing"
    assert "pages/1_execution.py" in content, "Execution page should be defined"
    assert "pages/2_results.py" in content, "Results page should be defined"
    assert "pages/3_history.py" in content, "History page should be defined"
