"""Google ADK Research Agent implementation.

This module provides a custom Member Agent implementation using Google ADK
(Agent Development Kit) to demonstrate integration of external AI frameworks
with MixSeek-Core's BaseMemberAgent interface.

Features:
- Single search query with google_search tool (User Story 1)
- Deep Research pipeline with ParallelAgent + SequentialAgent (User Story 2)
- Structured error handling with LLM-interpreted messages (FR-005, FR-006)
- Source tracking in metadata (FR-004)
- Debug mode with file output (logs ADK events and grounding data)
"""

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search  # type: ignore[attr-defined]
from google.genai import types as genai_types
from pydantic import ValidationError

from examples.custom_agents.adk_research.models import (
    ADKAgentConfig,
    ADKErrorCode,
    ResearchReportSchema,
    SearchResult,
)
from examples.custom_agents.adk_research.runner import ADKRunnerWrapper
from mixseek.agents.member.base import BaseMemberAgent
from mixseek.models.member_agent import AgentType, MemberAgentConfig, MemberAgentResult, ResultStatus

logger = logging.getLogger(__name__)


class ADKResearchAgent(BaseMemberAgent):
    """Google ADK Research Agent wrapping ADK multi-agent system.

    This agent demonstrates how to integrate Google ADK's multi-agent
    capabilities within the MixSeek-Core framework.

    Features:
        - Single search: Quick web search and summary (default mode)
        - Deep Research: Parallel search + synthesis pipeline

    Example:
        >>> config = MemberAgentConfig(...)  # Load from TOML
        >>> agent = ADKResearchAgent(config)
        >>> result = await agent.execute("What are the latest AI trends?")
        >>> print(result.content)  # Markdown summary with sources
    """

    def __init__(self, config: MemberAgentConfig) -> None:
        """Initialize the ADK Research Agent.

        Args:
            config: MemberAgentConfig loaded from TOML file.

        Raises:
            ValueError: If adk_research settings are missing from config.
        """
        super().__init__(config)

        # Extract ADK-specific settings from metadata
        adk_settings = config.metadata.get("tool_settings", {}).get("adk_research", {})
        if not adk_settings:
            raise ValueError(
                "Missing [agent.metadata.tool_settings.adk_research] configuration in TOML. "
                "Please ensure the TOML file contains ADK Research settings."
            )

        # Validate and store ADK config
        self.adk_config = ADKAgentConfig.model_validate(adk_settings)
        logger.info(f"Initialized ADKResearchAgent with model: {self.adk_config.gemini_model}")

        # Runner will be created on first execute
        self._runner: ADKRunnerWrapper | None = None

    def _create_researcher(self, name: str = "researcher", focus: str = "") -> LlmAgent:
        """Create a single research LlmAgent with google_search tool.

        Args:
            name: Name for the researcher agent.
            focus: Optional focus area for research instructions.

        Returns:
            Configured LlmAgent with google_search tool.
        """
        instruction = (
            "You are a research assistant. Search for relevant information and provide "
            "comprehensive analysis. Include source URLs in your response.\n\n"
        )
        if focus:
            instruction += f"Focus your research on: {focus}\n\n"

        instruction += (
            "Guidelines:\n"
            "- Search for authoritative and recent sources\n"
            "- Extract key facts, statistics, and insights\n"
            "- Note the URLs of sources you reference\n"
            "- Provide balanced and objective analysis\n"
            "- Format your findings clearly with bullet points"
        )

        # Apply configuration parameters (Article 9 compliance)
        generate_content_config = genai_types.GenerateContentConfig(
            temperature=self.adk_config.temperature,
            max_output_tokens=self.adk_config.max_output_tokens,
        )

        return LlmAgent(
            name=name,
            model=self.adk_config.gemini_model,
            instruction=instruction,
            tools=[google_search],
            output_key=f"{name}_result",
            generate_content_config=generate_content_config,
        )

    def _create_summarizer(self) -> LlmAgent:
        """Create summarizer agent with JSON mode for structured output.

        Uses LlmAgent.output_schema for Gemini JSON mode to ensure
        reliable structured output without regex parsing.

        Returns:
            Configured LlmAgent with output_schema enabled.
        """
        instruction = """You are a research synthesizer. Analyze the research results and
create a comprehensive summary report in JSON format.

Your JSON output must contain:
- executive_summary: Brief overview of key findings (3-5 sentences)
- key_findings: Array of main discoveries (strings)
- patterns: Array of common themes and trends (strings)
- recommendations: Array of actionable insights (strings)

Guidelines:
- Synthesize information from all provided research
- Identify patterns and contradictions
- Be concise but comprehensive
- Focus on factual findings, not speculation"""

        # JSON mode configuration (temperature and token limit only)
        # Note: response_schema must be set via LlmAgent.output_schema parameter
        generate_content_config = genai_types.GenerateContentConfig(
            temperature=0.3,  # Lower for consistent JSON output
            max_output_tokens=self.adk_config.max_output_tokens,
        )

        return LlmAgent(
            name="summarizer",
            model=self.adk_config.gemini_model,
            instruction=instruction,
            output_key="final_report",
            output_schema=ResearchReportSchema,
            generate_content_config=generate_content_config,
        )

    def _build_pipeline(self) -> SequentialAgent:
        """Build Deep Research pipeline with parallel researchers + summarizer.

        Creates a pipeline with:
        - N parallel researcher agents with different focus areas (up to 5)
        - 1 summarizer agent that synthesizes results

        Returns:
            SequentialAgent containing the full pipeline.
        """
        # Define focus areas for up to 5 researchers (FR-003 compliance)
        focus_areas = [
            "technical aspects and implementation details",
            "market trends and industry analysis",
            "challenges, limitations, and future directions",
            "use cases, applications, and real-world examples",
            "competitive landscape and alternative approaches",
        ]

        # Honor researcher_count from config (up to 5)
        researcher_count = min(self.adk_config.researcher_count, len(focus_areas))

        researchers: list[BaseAgent] = []
        for i in range(researcher_count):
            researcher = self._create_researcher(
                name=f"researcher_{i + 1}",
                focus=focus_areas[i],
            )
            researchers.append(researcher)

        logger.info(f"Created {len(researchers)} parallel researchers for Deep Research")

        # Create parallel agent for concurrent research
        parallel_research = ParallelAgent(
            name="parallel_research",
            description="Parallel research from multiple perspectives",
            sub_agents=researchers,
        )

        # Create summarizer
        summarizer = self._create_summarizer()

        # Combine into sequential pipeline
        pipeline = SequentialAgent(
            name="deep_research_pipeline",
            description="Deep Research: parallel search + synthesis",
            sub_agents=[parallel_research, summarizer],
        )

        return pipeline

    def _parse_sources(self, response: dict[str, Any]) -> list[SearchResult]:
        """Extract source URLs/titles from ADK grounding metadata (FR-004/SC-004).

        Parses the grounding metadata from ADK tool responses to extract
        structured source information. Falls back to URL extraction from
        content only if grounding metadata is unavailable.

        Args:
            response: Response dictionary from ADKRunnerWrapper containing
                grounding_metadata from google_search tool calls.

        Returns:
            List of SearchResult objects for MemberAgentResult.metadata.
        """
        sources: list[SearchResult] = []
        seen_urls: set[str] = set()

        # Primary source: Extract from grounding metadata (Article 9 compliance)
        grounding_metadata = response.get("grounding_metadata", [])
        for grounding in grounding_metadata:
            for source_data in grounding.get("sources", []):
                url = source_data.get("url", "")
                title = source_data.get("title", "")

                if url and url not in seen_urls:
                    seen_urls.add(url)
                    source = SearchResult(
                        url=url,
                        title=title if title else "",
                        snippet="",  # Snippet from grounding if available
                        timestamp=datetime.now(UTC),
                    )
                    sources.append(source)

                    if len(sources) >= self.adk_config.search_result_limit:
                        break

            if len(sources) >= self.adk_config.search_result_limit:
                break

        # Log extraction results
        if sources:
            logger.debug(f"Parsed {len(sources)} sources from grounding_metadata")
        else:
            # If no sources from grounding metadata, log diagnostic info
            # Note: Empty sources can be normal for some queries, so use info level
            grounding_count = len(response.get("grounding_metadata", []))
            logger.info(
                f"No sources parsed from grounding_metadata (grounding_metadata contained {grounding_count} entries)"
            )

        return sources

    def _classify_error(self, error: Exception) -> tuple[ADKErrorCode, str]:
        """Classify error and return error code with base message.

        Args:
            error: The exception that occurred.

        Returns:
            Tuple of (error_code, base_message).
        """
        error_str = str(error).lower()

        if "authentication" in error_str or "api key" in error_str or "401" in error_str:
            return "AUTH_ERROR", "Authentication failed. Please check your GOOGLE_API_KEY."

        if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
            return "RATE_LIMIT", "Rate limit exceeded. Please wait before retrying."

        if "timeout" in error_str or "timed out" in error_str:
            return "TIMEOUT", "Request timed out. Consider increasing timeout_seconds."

        if "network" in error_str or "connection" in error_str:
            return "NETWORK_ERROR", "Network error. Please check your internet connection."

        if "no results" in error_str or "empty" in error_str:
            return "SEARCH_NO_RESULTS", "No search results found. Try refining your query."

        if "pipeline" in error_str or "agent" in error_str:
            return "PIPELINE_ERROR", "Pipeline execution failed. Check agent configuration."

        if "config" in error_str or "validation" in error_str:
            return "CONFIG_ERROR", "Configuration error. Please check your TOML settings."

        return "UNKNOWN_ERROR", f"An unexpected error occurred: {error}"

    async def _handle_error(self, error: Exception) -> MemberAgentResult:
        """Generate structured error result with LLM-interpreted message (FR-006).

        Creates a MemberAgentResult with:
        - Structured metadata (error_code, message, timestamp)
        - Natural-language Markdown explanation in content
        - Troubleshooting guidance for users

        Args:
            error: The exception that occurred.

        Returns:
            MemberAgentResult with error status, content, and metadata.
        """
        error_code, base_message = self._classify_error(error)
        timestamp = datetime.now(UTC).isoformat()

        # Generate Markdown error content (FR-006 requires content explanation)
        error_content = f"""## Error: {error_code}

{base_message}

### Details

- **Error Code**: `{error_code}`
- **Timestamp**: {timestamp}

### Troubleshooting

"""
        # Add error-specific troubleshooting
        if error_code == "AUTH_ERROR":
            error_content += (
                "1. Verify `GOOGLE_API_KEY` environment variable is set\n"
                "2. Ensure the API key has Gemini API access enabled\n"
                "3. Check if the API key has expired or been revoked\n"
            )
        elif error_code == "RATE_LIMIT":
            error_content += (
                "1. Wait a few minutes before retrying\n"
                "2. Consider reducing request frequency\n"
                "3. Check your API quota in Google Cloud Console\n"
            )
        elif error_code == "TIMEOUT":
            error_content += (
                "1. Increase `timeout_seconds` in TOML configuration\n"
                "2. Simplify your query to reduce processing time\n"
                "3. Check network latency to Google API servers\n"
            )
        elif error_code == "NETWORK_ERROR":
            error_content += (
                "1. Check your internet connection\n"
                "2. Verify firewall allows HTTPS to Google APIs\n"
                "3. Try again in a few moments\n"
            )
        elif error_code == "SEARCH_NO_RESULTS":
            error_content += (
                "1. Try different keywords or phrasing\n"
                "2. Use more general terms\n"
                "3. Verify the topic has publicly available information\n"
            )
        else:
            error_content += f"Original error: {error}\n"

        # Return MemberAgentResult with both content and metadata (FR-006 compliance)
        # Note: Using direct construction instead of .error() to include content
        return MemberAgentResult(
            status=ResultStatus.ERROR,
            content=error_content,
            agent_name=self.config.name,
            agent_type=str(AgentType.CUSTOM),
            error_code=error_code,
            metadata={
                "error_code": error_code,
                "error_message": str(error),
                "timestamp": timestamp,
            },
        )

    def _extract_structured_report(self, content: str, sources: list[SearchResult]) -> dict[str, Any]:
        """Extract structured report from JSON content.

        Parses the JSON response from the summarizer agent using Gemini JSON mode.

        Args:
            content: JSON string from summarizer agent.
            sources: List of SearchResult from grounding metadata.

        Returns:
            Dictionary with ResearchReport fields.
        """
        # Default structure with sources
        report: dict[str, Any] = {
            "executive_summary": "",
            "key_findings": [],
            "patterns": [],
            "recommendations": [],
            "sources": [s.model_dump() for s in sources],
        }

        try:
            # Parse JSON from LLM output
            parsed = json.loads(content)

            # Validate with Pydantic schema
            schema = ResearchReportSchema.model_validate(parsed)

            # Update report with validated data
            report["executive_summary"] = schema.executive_summary
            report["key_findings"] = schema.key_findings
            report["patterns"] = schema.patterns
            report["recommendations"] = schema.recommendations

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Failed to parse structured report: {e}")
            # Return default structure with sources only

        return report

    def _format_sources_section(self, sources: list[SearchResult]) -> str:
        """Format sources as markdown section for content injection.

        This method implements a dependency injection pattern - appending
        source references to the markdown content so they appear in the UI
        without requiring src/ modifications.

        Args:
            sources: List of SearchResult objects from grounding metadata.

        Returns:
            Markdown-formatted sources section string.
        """
        if not sources:
            return ""

        lines = [
            "",
            "---",
            "",
            "## 参照元 / Sources",
            "",
        ]

        for i, source in enumerate(sources, 1):
            title = source.title or "Unknown"
            url = source.url
            lines.append(f"{i}. [{title}]({url})")

        lines.append("")
        return "\n".join(lines)

    def _persist_metadata(
        self,
        metadata: dict[str, Any],
        task: str,
        execution_id: str | None = None,
        team_id: str | None = None,
        round_number: int | None = None,
    ) -> Path:
        """Persist metadata to JSON file for team/orchestration access.

        File naming convention:
        - Team execution: {execution_id}_{team_id}_{round}.json
        - Single execution: adk_research_{timestamp}.json

        Args:
            metadata: Metadata dictionary to persist (sources, structured_report, etc.).
            task: Original task/query string.
            execution_id: Execution identifier (from team/orchestration context).
            team_id: Team identifier (from team/orchestration context).
            round_number: Round number (from team/orchestration context).

        Returns:
            Path to the persisted JSON file.
        """
        workspace = os.environ.get("MIXSEEK_WORKSPACE")
        if not workspace:
            logger.warning(
                "MIXSEEK_WORKSPACE environment variable not set. Metadata will be saved to current directory."
            )
            workspace = "."
        metadata_dir = Path(workspace) / "logs" / "adk_research"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on context
        if execution_id and team_id and round_number is not None:
            # Team/orchestration execution
            filename = f"{execution_id}_{team_id}_{round_number}.json"
        else:
            # Single execution
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
            filename = f"adk_research_{timestamp}.json"

        metadata_file = metadata_dir / filename

        # Build persistence record
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "execution_id": execution_id,
            "team_id": team_id,
            "round_number": round_number,
            "task": task[:500],  # Truncate long tasks
            **metadata,  # Include all metadata fields
        }

        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Metadata persisted to: {metadata_file}")
        except OSError as e:
            logger.warning(f"Failed to persist metadata to {metadata_file}: {e}")

        return metadata_file

    @staticmethod
    def load_metadata(
        workspace: Path,
        execution_id: str,
        team_id: str,
        round_number: int,
    ) -> dict[str, Any] | None:
        """Load persisted metadata from JSON file.

        Utility method for team/orchestration samples to access metadata
        that was persisted during ADK Research Agent execution.

        Args:
            workspace: Workspace directory path ($MIXSEEK_WORKSPACE).
            execution_id: Execution identifier.
            team_id: Team identifier.
            round_number: Round number.

        Returns:
            Metadata dictionary if file exists, None otherwise.

        Example:
            >>> metadata = ADKResearchAgent.load_metadata(
            ...     workspace=Path("/path/to/workspace"),
            ...     execution_id="exec-123",
            ...     team_id="team-1",
            ...     round_number=1,
            ... )
            >>> if metadata:
            ...     sources = metadata.get("sources", [])
        """
        metadata_file = workspace / "logs" / "adk_research" / f"{execution_id}_{team_id}_{round_number}.json"

        if not metadata_file.exists():
            logger.debug(f"Metadata file not found: {metadata_file}")
            return None

        try:
            with open(metadata_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
            return None

    async def execute(self, task: str, context: dict[str, Any] | None = None, **kwargs: Any) -> MemberAgentResult:
        """Execute research task using ADK pipeline.

        Supports two modes:
        - Single search: Quick web search and summary
        - Deep Research (default): Parallel search + synthesis

        Args:
            task: Research query or topic.
            context: Optional execution context.
            **kwargs: Additional parameters.
                - deep_research (bool): Override Deep Research mode setting.

        Returns:
            MemberAgentResult with research findings, sources, and structured report.
        """
        start_time = time.time()

        # Check for deep_research mode (config default, then context/kwargs override)
        deep_research = self.adk_config.deep_research_default
        if "deep_research" in kwargs:
            deep_research = kwargs["deep_research"]
        elif context and "deep_research" in context:
            deep_research = context["deep_research"]

        try:
            # Create appropriate agent
            adk_agent: BaseAgent
            if deep_research:
                logger.info(f"Starting Deep Research pipeline for: {task[:50]}...")
                adk_agent = self._build_pipeline()
            else:
                logger.info(f"Starting single search for: {task[:50]}...")
                adk_agent = self._create_researcher()

            # Create runner with timeout from config (FR-005 compliance)
            runner = ADKRunnerWrapper(
                agent=adk_agent,
                app_name="adk_research",
                timeout_seconds=self.adk_config.timeout_seconds,
            )

            try:
                # Execute with debug mode if enabled
                response = await runner.run_once(task, debug_mode=self.adk_config.debug_mode)

                # Write debug log if debug mode is enabled (via standard logging)
                if self.adk_config.debug_mode and response.get("debug_info"):
                    debug_info = response["debug_info"]
                    logger.debug(
                        "ADK debug info: task=%s, events=%d, grounding=%d",
                        task[:100],
                        len(debug_info.get("events", [])),
                        len(debug_info.get("grounding_metadata", [])),
                    )
            finally:
                # Clean up runner (ensures cleanup even on exception)
                await runner.cleanup()

            # Extract content
            content = response.get("content", "")
            if not content:
                return await self._handle_error(ValueError("No content returned from ADK agent"))

            # Parse sources from response
            sources = self._parse_sources(response)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Build metadata
            metadata: dict[str, Any] = {
                "mode": "deep_research" if deep_research else "single_search",
                "model": self.adk_config.gemini_model,
                "sources": [s.model_dump() for s in sources],
                "source_count": len(sources),
            }

            # Add structured report if enabled
            if self.adk_config.structured_output:
                structured_report = self._extract_structured_report(content, sources)
                metadata["structured_report"] = structured_report

            # Append sources section to content for UI visibility (dependency injection pattern)
            if self.adk_config.append_sources_to_content and sources:
                sources_section = self._format_sources_section(sources)
                content = content + sources_section
                logger.debug(f"Appended {len(sources)} sources to content")

            # Persist metadata to JSON if enabled (for team/orchestration access)
            if self.adk_config.persist_metadata:
                context = context or {}
                metadata_path = self._persist_metadata(
                    metadata=metadata,
                    task=task,
                    execution_id=context.get("execution_id"),
                    team_id=context.get("team_id"),
                    round_number=context.get("round_number"),
                )
                metadata["metadata_file"] = str(metadata_path)

            return MemberAgentResult(
                status=ResultStatus.SUCCESS,
                content=content,
                agent_name=self.config.name,
                agent_type=str(AgentType.CUSTOM),
                execution_time_ms=execution_time_ms,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error executing ADK Research Agent: {e}")
            return await self._handle_error(e)

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        await super().cleanup()


__all__ = ["ADKResearchAgent"]
