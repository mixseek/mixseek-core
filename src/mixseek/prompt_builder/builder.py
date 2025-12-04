"""UserPromptBuilder class for prompt formatting.

Feature: 092-user-prompt-builder-team
Date: 2025-11-19
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

if TYPE_CHECKING:
    from mixseek.config.schema import PromptBuilderSettings
    from mixseek.storage.aggregation_store import AggregationStore

from mixseek.prompt_builder.formatters import (
    format_ranking_table,
    format_submission_history,
    generate_position_message,
    get_current_datetime_with_timezone,
)
from mixseek.prompt_builder.models import EvaluatorPromptContext, RoundPromptContext


class UserPromptBuilder:
    """Component for formatting user prompts.

    Uses Jinja2 template engine and receives PromptBuilderSettings from ConfigurationManager.
    Includes Leader Board ranking retrieval functionality.

    Args:
        settings: PromptBuilder configuration (obtained via ConfigurationManager)
        store: DuckDB store (for Leader Board retrieval). None if ranking info unavailable

    Raises:
        ValidationError: If settings validation fails

    Note:
        ConfigurationManager integration provides traceability and unified configuration management.
        Settings are obtained from the calling context (RoundController, Evaluator, etc.).
    """

    def __init__(
        self,
        settings: PromptBuilderSettings,
        store: AggregationStore | None = None,
    ) -> None:
        """Initialize UserPromptBuilder instance.

        Args:
            settings: PromptBuilder configuration (from ConfigurationManager)
            store: DuckDB store (for Leader Board retrieval). None if ranking info unavailable

        Raises:
            ValidationError: If settings validation fails
        """
        self.settings = settings
        self.store = store

        # Initialize Jinja2 environment with StrictUndefined to catch undefined variables
        self.jinja_env = Environment(autoescape=False, undefined=StrictUndefined)

    async def build_team_prompt(self, context: RoundPromptContext) -> str:
        """Format Team user prompt.

        Args:
            context: Context for prompt generation

        Returns:
            Formatted prompt string

        Raises:
            ValidationError: If context validation fails
            TemplateError: If Jinja2 template syntax error
            ValueError: If TZ environment variable is invalid
        """
        # Prepare template variables
        template_vars = await self._prepare_round_template_variables(context)

        # Render template
        return self._render_prompt(self.settings.team_user_prompt, template_vars)

    def _render_prompt(self, template_string: str, template_vars: dict[str, str | int]) -> str:
        """Render the prompt template with the given variables.

        Args:
            template_string: Jinja2 template string to render
            template_vars: Dictionary of template variables

        Returns:
            Rendered prompt string

        Raises:
            RuntimeError: If Jinja2 template syntax error occurs
        """
        try:
            template = self.jinja_env.from_string(template_string)
            return template.render(template_vars)
        except (TemplateSyntaxError, UndefinedError) as e:
            msg = f"Jinja2 template error: {e}"
            raise RuntimeError(msg) from e

    async def _prepare_round_template_variables(self, context: RoundPromptContext) -> dict[str, str | int]:
        """Prepare template variables for Jinja2 rendering.

        Args:
            context: Context for prompt generation

        Returns:
            Dictionary of template variables
        """
        template_vars: dict[str, str | int] = {
            "user_prompt": context.user_prompt,
            "round_number": context.round_number,
            "current_datetime": get_current_datetime_with_timezone(),
        }

        # Format submission history (always call formatters, which handles empty history)
        template_vars["submission_history"] = format_submission_history(context.round_history)

        # Fetch ranking data (if store is available and round > 1)
        ranking = None
        current_team_position = None
        total_teams = None

        if context.round_number > 1 and context.store is not None:
            ranking = await context.store.get_leader_board_ranking(context.execution_id)
            if ranking:
                current_team_position = next(
                    (idx for idx, team in enumerate(ranking, start=1) if team["team_id"] == context.team_id),
                    None,
                )
                total_teams = len(ranking)

        # Format ranking info (always call formatters, which handle None gracefully)
        template_vars["ranking_table"] = format_ranking_table(ranking, context.team_id)
        template_vars["team_position_message"] = generate_position_message(current_team_position, total_teams)

        return template_vars

    def build_evaluator_prompt(self, context: EvaluatorPromptContext) -> str:
        """Format Evaluator user prompt for metrics evaluation.

        Args:
            context: Context for Evaluator prompt generation

        Returns:
            Formatted prompt string

        Raises:
            ValidationError: If context validation fails
            RuntimeError: If Jinja2 template syntax error occurs

        Example:
            ```python
            from pathlib import Path
            from mixseek.prompt_builder import UserPromptBuilder, EvaluatorPromptContext

            workspace = Path("/path/to/workspace")
            builder = UserPromptBuilder(workspace=workspace)

            context = EvaluatorPromptContext(
                user_query="Pythonとは何ですか？",
                submission="Pythonはプログラミング言語です..."
            )

            prompt = builder.build_evaluator_prompt(context)
            ```
        """
        # Prepare template variables
        template_vars: dict[str, str | int] = {
            "user_prompt": context.user_query,
            "submission": context.submission,
            "current_datetime": get_current_datetime_with_timezone(),
        }

        # Render template
        return self._render_prompt(self.settings.evaluator_user_prompt, template_vars)

    async def build_judgment_prompt(self, context: RoundPromptContext) -> str:
        """Format JudgementClient user prompt for improvement judgement.

        Args:
            context: Context for JudgementClient prompt generation (RoundPromptContext)

        Returns:
            Formatted prompt string

        Raises:
            ValidationError: If context validation fails
            RuntimeError: If Jinja2 template syntax error occurs

        Example:
            ```python
            from pathlib import Path
            from mixseek.prompt_builder import UserPromptBuilder, RoundPromptContext

            workspace = Path("/path/to/workspace")
            builder = UserPromptBuilder(workspace=workspace, store=None)

            context = RoundPromptContext(
                user_prompt="データ分析レポートを作成",
                round_number=3,
                round_history=[...],
                team_id="team-001",
                team_name="Team Alpha",
                execution_id="exec-123",
                store=None
            )

            prompt = await builder.build_judgment_prompt(context)
            ```
        """
        # Prepare template variables (reuse the same logic as build_team_prompt)
        template_vars = await self._prepare_round_template_variables(context)

        # Render template with judgment-specific template
        return self._render_prompt(self.settings.judgment_user_prompt, template_vars)
