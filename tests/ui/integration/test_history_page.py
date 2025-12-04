"""Integration tests for history page."""

from pathlib import Path


def test_history_page_exists() -> None:
    """Test that history page file exists."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    assert page_path.exists()


def test_history_page_imports() -> None:
    """Test that history page has required imports."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    with open(page_path) as f:
        content = f.read()

    # Check required imports
    assert "import streamlit as st" in content
    assert "from mixseek.ui.components.history_table import render_history_table" in content
    assert "from mixseek.ui.services.history_service import fetch_execution_detail, fetch_history" in content
    assert "from mixseek.ui.services.leaderboard_service import fetch_top_submission" in content


def test_history_page_has_required_ui_elements() -> None:
    """Test that history page defines required UI elements."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    with open(page_path) as f:
        content = f.read()

    # Check UI element definitions
    assert "st.title(" in content
    assert "fetch_history(" in content
    assert "render_history_table(" in content
    assert "st.selectbox(" in content  # Filter/Sort controls
    assert "st.button(" in content  # Pagination buttons


def test_history_page_has_detail_view() -> None:
    """Test that history page has detail view functionality (FR-017)."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    with open(page_path) as f:
        content = f.read()

    # Check detail view elements (FR-017)
    assert "fetch_execution_detail(" in content
    assert "selected_execution_id" in content
    assert "実行詳細" in content
    assert "st.text_area(" in content  # For displaying full prompt


def test_history_page_has_top_submission_display() -> None:
    """Test that history page displays top submission in detail view."""
    page_path = Path(__file__).parent.parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    with open(page_path) as f:
        content = f.read()

    # Check top submission display elements
    assert "fetch_top_submission(" in content
    assert "top_submission" in content
    assert "最高スコアサブミッション" in content
    assert "サブミッション内容" in content
    assert "st.expander(" in content  # For collapsible submission content
