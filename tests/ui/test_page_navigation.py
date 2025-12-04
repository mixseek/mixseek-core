"""Tests for page navigation links."""

from pathlib import Path


def test_execution_page_has_navigation_to_history() -> None:
    """Test that execution page has navigation link to history page."""
    execution_page = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "1_execution.py"
    with open(execution_page) as f:
        content = f.read()

    # Should have link to history page
    assert "pages/3_history.py" in content or "3_history" in content


def test_results_page_has_navigation_to_execution() -> None:
    """Test that results page has navigation link to execution page."""
    results_page = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "2_results.py"
    with open(results_page) as f:
        content = f.read()

    # Should have link to execution page
    assert "pages/1_execution.py" in content or "1_execution" in content


def test_history_page_has_navigation_to_execution() -> None:
    """Test that history page has navigation link to execution page."""
    history_page = Path(__file__).parent.parent.parent / "src" / "mixseek" / "ui" / "pages" / "3_history.py"
    with open(history_page) as f:
        content = f.read()

    # Should have link to execution page
    assert "pages/1_execution.py" in content or "1_execution" in content
