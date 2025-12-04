"""Unit tests for UserPromptBuilder.build_evaluator_prompt method.

Feature: 140-user-prompt-builder-evaluator-judgement
Task: T015
Date: 2025-11-25
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from mixseek.config.schema import PromptBuilderSettings
from mixseek.prompt_builder import UserPromptBuilder
from mixseek.prompt_builder.models import EvaluatorPromptContext


class TestBuildEvaluatorPrompt:
    """Tests for UserPromptBuilder.build_evaluator_prompt method."""

    def test_build_evaluator_prompt_default_template(self, tmp_path: Path) -> None:
        """Test prompt formatting with default template."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(
            user_query="What is Python?", submission="Python is a programming language..."
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T14:30:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        assert "What is Python?" in prompt
        assert "Python is a programming language..." in prompt
        assert "2025-11-25T14:30:00+09:00" in prompt
        assert "ユーザプロンプト" in prompt
        assert "提出内容" in prompt

    def test_build_evaluator_prompt_custom_template(self, tmp_path: Path) -> None:
        """Test prompt formatting with custom template."""
        custom_template = """Custom Evaluator Prompt:
User Query: {{ user_prompt }}
Submission: {{ submission }}
DateTime: {{ current_datetime }}"""

        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.evaluator_user_prompt = custom_template

        context = EvaluatorPromptContext(
            user_query="Explain machine learning", submission="Machine learning is a subset of AI..."
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T15:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        assert "Custom Evaluator Prompt:" in prompt
        assert "User Query: Explain machine learning" in prompt
        assert "Submission: Machine learning is a subset of AI..." in prompt
        assert "DateTime: 2025-11-25T15:00:00+09:00" in prompt

    def test_build_evaluator_prompt_placeholder_validation(self, tmp_path: Path) -> None:
        """Test that all required placeholder variables are embedded."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(
            user_query="Test query with special chars: @#$%",
            submission="Test submission with newlines\nLine 2\nLine 3",
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T16:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        # Verify placeholder variables are replaced
        assert "{{ user_prompt }}" not in prompt
        assert "{{ submission }}" not in prompt
        assert "{{ current_datetime }}" not in prompt

        # Verify actual values are present
        assert "Test query with special chars: @#$%" in prompt
        assert "Test submission with newlines" in prompt
        assert "Line 2" in prompt
        assert "Line 3" in prompt
        assert "2025-11-25T16:00:00+09:00" in prompt

    def test_build_evaluator_prompt_template_syntax_error(self, tmp_path: Path) -> None:
        """Test that Jinja2 syntax errors raise RuntimeError."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.evaluator_user_prompt = "{{ invalid syntax"  # Missing closing braces

        context = EvaluatorPromptContext(user_query="Test", submission="Test")

        with pytest.raises(RuntimeError, match="Jinja2 template error"):
            builder.build_evaluator_prompt(context)

    def test_build_evaluator_prompt_undefined_variable_error(self, tmp_path: Path) -> None:
        """Test that undefined variables raise RuntimeError."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        builder.settings.evaluator_user_prompt = "{{ undefined_variable }}"

        context = EvaluatorPromptContext(user_query="Test", submission="Test")

        with pytest.raises(RuntimeError, match="Jinja2 template error"):
            builder.build_evaluator_prompt(context)

    def test_build_evaluator_prompt_current_datetime_format(self, tmp_path: Path) -> None:
        """Test that current_datetime is in ISO 8601 format with timezone."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(user_query="Test", submission="Test")

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T17:30:45+09:00"
            prompt = builder.build_evaluator_prompt(context)

        # Verify ISO 8601 format with timezone
        assert "2025-11-25T17:30:45+09:00" in prompt
        # Verify get_current_datetime_with_timezone was called
        mock_dt.assert_called_once()

    def test_build_evaluator_prompt_multiline_user_query(self, tmp_path: Path) -> None:
        """Test that multiline user_query is correctly embedded."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(
            user_query="Question 1: What is Python?\nQuestion 2: How does it work?\nQuestion 3: Why use it?",
            submission="Answer 1: Python is a language.\nAnswer 2: It interprets code.\nAnswer 3: It's easy.",
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T18:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        assert "Question 1: What is Python?" in prompt
        assert "Question 2: How does it work?" in prompt
        assert "Question 3: Why use it?" in prompt
        assert "Answer 1: Python is a language." in prompt
        assert "Answer 2: It interprets code." in prompt
        assert "Answer 3: It's easy." in prompt

    def test_build_evaluator_prompt_special_characters(self, tmp_path: Path) -> None:
        """Test that special characters are handled correctly."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(
            user_query="Query with symbols: < > & \" ' @#$%^&*()",
            submission="Submission with symbols: < > & \" ' @#$%^&*()",
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T19:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        # Jinja2 autoescape=False should preserve special characters
        assert "< > & \" ' @#$%^&*()" in prompt

    def test_build_evaluator_prompt_empty_template_after_validation(self, tmp_path: Path) -> None:
        """Test that post-validation empty template handling works correctly."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        # Template that becomes empty after rendering (edge case)
        builder.settings.evaluator_user_prompt = "{% if false %}Never rendered{% endif %}"

        context = EvaluatorPromptContext(user_query="Test", submission="Test")

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T20:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        # Should return empty string without error
        assert prompt == ""

    def test_build_evaluator_prompt_long_submission(self, tmp_path: Path) -> None:
        """Test that long submissions are handled correctly."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        long_submission = "This is a very long submission. " * 100  # 3200 characters

        context = EvaluatorPromptContext(user_query="Summarize this", submission=long_submission)

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T21:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        assert long_submission in prompt
        assert len(prompt) > 3000

    def test_build_evaluator_prompt_unicode_characters(self, tmp_path: Path) -> None:
        """Test that Unicode characters (Japanese, emoji, etc.) are handled correctly."""
        settings = PromptBuilderSettings()
        builder = UserPromptBuilder(settings=settings, store=None)
        context = EvaluatorPromptContext(
            user_query="日本語のクエリ: Pythonとは何ですか？ 😀",
            submission="日本語の回答: Pythonはプログラミング言語です。 🐍",
        )

        with patch("mixseek.prompt_builder.builder.get_current_datetime_with_timezone") as mock_dt:
            mock_dt.return_value = "2025-11-25T22:00:00+09:00"
            prompt = builder.build_evaluator_prompt(context)

        assert "日本語のクエリ: Pythonとは何ですか？ 😀" in prompt
        assert "日本語の回答: Pythonはプログラミング言語です。 🐍" in prompt
