"""Integration tests for execution page."""

from pathlib import Path


def test_execution_page_exists() -> None:
    """Test that execution page file exists."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "1_execution.py"
    assert page_path.exists()


def test_execution_page_imports() -> None:
    """Test that execution page has required imports."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "1_execution.py"
    with open(page_path) as f:
        content = f.read()

    # Check required imports
    assert "import streamlit as st" in content
    assert "from mixseek.ui.components.orchestration_selector import render_orchestration_selector" in content
    assert "from mixseek.ui.services.execution_service import" in content
    assert "run_orchestration_in_background" in content


def test_execution_page_has_required_ui_elements() -> None:
    """Test that execution page defines required UI elements."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "1_execution.py"
    with open(page_path) as f:
        content = f.read()

    # Check UI element definitions
    assert "st.title(" in content
    assert "render_orchestration_selector()" in content
    assert "st.text_area(" in content
    assert "st.button(" in content
    assert "run_orchestration_in_background(" in content
