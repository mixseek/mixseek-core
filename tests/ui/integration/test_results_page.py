"""Integration tests for results page."""

from pathlib import Path


def test_results_page_exists() -> None:
    """Test that results page file exists."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "2_results.py"
    assert page_path.exists()


def test_results_page_imports() -> None:
    """Test that results page has required imports."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "2_results.py"
    with open(page_path) as f:
        content = f.read()

    # Check required imports
    assert "import streamlit as st" in content
    assert "from mixseek.ui.components.leaderboard_table import render_leaderboard_table" in content
    assert "fetch_leaderboard" in content
    assert "fetch_top_submission" in content
    assert "fetch_team_submission" in content


def test_results_page_has_required_ui_elements() -> None:
    """Test that results page defines required UI elements."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "2_results.py"
    with open(page_path) as f:
        content = f.read()

    # Check UI element definitions
    assert "st.title(" in content
    assert "fetch_leaderboard(" in content
    assert "fetch_top_submission(" in content
    assert "render_leaderboard_table(" in content
