"""ADK Runner wrapper for session management.

This module provides a wrapper for Google ADK's InMemoryRunner to manage
agent execution and session lifecycle.
"""

import asyncio
import logging
import uuid
from typing import Any

from google.adk import Runner
from google.adk.agents import BaseAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)


class ADKRunnerWrapper:
    """Wrapper for Google ADK Runner with session lifecycle management.

    This class manages the InMemoryRunner and session service to provide
    a simplified interface for executing ADK agents.

    Attributes:
        agent: The ADK agent to run.
        app_name: Application name for session management.
        runner: The ADK Runner instance.
        session_service: The session service for managing sessions.
    """

    def __init__(self, agent: BaseAgent, app_name: str, timeout_seconds: float = 30.0) -> None:
        """Initialize the ADK runner wrapper.

        Args:
            agent: ADK Agent instance to run.
            app_name: Application name for session identification.
            timeout_seconds: Maximum time allowed for execution (default: 30s).
        """
        self.agent = agent
        self.app_name = app_name
        self.timeout_seconds = timeout_seconds
        self.session_service: InMemorySessionService = InMemorySessionService()  # type: ignore[no-untyped-call]
        self.runner = Runner(
            app_name=app_name,
            agent=agent,
            session_service=self.session_service,
        )
        self._active_sessions: dict[str, str] = {}  # user_id -> session_id

    async def run(self, user_id: str, message: str, debug_mode: bool = False) -> dict[str, Any]:
        """Execute the agent with session management.

        Creates or reuses a session for the user and executes the agent
        with the given message.

        Args:
            user_id: Unique identifier for the user.
            message: User message/query to process.
            debug_mode: Enable debug mode to capture detailed event information.

        Returns:
            Dictionary containing:
                - content: Agent response text
                - events: List of raw events from the agent
                - session_id: Session identifier used
                - grounding_metadata: List of grounding metadata from tool calls
                - debug_info: (debug_mode only) Detailed event and grounding data

        Raises:
            TimeoutError: If execution exceeds timeout_seconds.
        """
        # Get or create session for user
        session_id = self._active_sessions.get(user_id)

        if session_id is None:
            # Create new session
            session = await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
            )
            session_id = session.id
            self._active_sessions[user_id] = session_id
            logger.debug(f"Created new session {session_id} for user {user_id}")

        # Create message content
        content = types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )

        # Collect events, response, and grounding metadata
        events: list[Any] = []
        response_text = ""
        grounding_metadata: list[dict[str, Any]] = []
        debug_events: list[dict[str, Any]] = []  # Debug mode: event structure dumps

        try:
            async with asyncio.timeout(self.timeout_seconds):
                async for event in self.runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content,
                ):
                    events.append(event)

                    # Debug mode: capture event structure
                    if debug_mode:
                        debug_events.append(self._dump_event_structure(event))
                        has_grounding = hasattr(event, "grounding_metadata") and bool(event.grounding_metadata)
                        logger.debug(
                            f"Event received: type={type(event).__name__}, "
                            f"has_content={bool(event.content)}, has_grounding_metadata={has_grounding}"
                        )

                    # Extract text from event content
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text

                    # Extract grounding metadata from tool responses (FR-004)
                    if hasattr(event, "grounding_metadata") and event.grounding_metadata:
                        logger.debug("Found grounding_metadata on event")
                        grounding_metadata.append(self._extract_grounding(event.grounding_metadata))
                    # Also check for search_entry_point in grounding chunks
                    if hasattr(event, "candidates"):
                        for candidate in event.candidates or []:
                            if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                                logger.debug("Found grounding_metadata in candidate")
                                grounding_metadata.append(self._extract_grounding(candidate.grounding_metadata))

        except TimeoutError:
            logger.error(f"Execution timed out after {self.timeout_seconds} seconds")
            raise TimeoutError(f"Request timed out after {self.timeout_seconds} seconds")

        # Try to get grounding metadata from session state (ADK may store it there)
        session_state_keys: list[str] = []
        try:
            retrieved_session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id,
            )
            if retrieved_session and hasattr(retrieved_session, "state") and retrieved_session.state:
                session_state_keys = list(retrieved_session.state.keys())
                if debug_mode:
                    logger.debug(f"Session state keys: {session_state_keys}")

                # Check for grounding metadata in session state
                temp_grounding = retrieved_session.state.get("temp:_adk_grounding_metadata")
                if temp_grounding:
                    logger.debug("Found grounding_metadata in session state (temp:_adk_grounding_metadata)")
                    grounding_metadata.append(self._extract_grounding(temp_grounding))
        except Exception as e:
            logger.warning(f"Failed to get session state: {e}")

        result: dict[str, Any] = {
            "content": response_text,
            "events": events,
            "session_id": session_id,
            "grounding_metadata": grounding_metadata,
        }

        # Add debug info if debug mode enabled
        if debug_mode:
            result["debug_info"] = {
                "event_count": len(events),
                "event_dump": debug_events,
                "session_state_keys": session_state_keys,
                "grounding_metadata_count": len(grounding_metadata),
                # Include actual grounding_metadata contents for debugging
                "grounding_metadata_contents": grounding_metadata,
            }

        return result

    def _dump_event_structure(self, event: Any) -> dict[str, Any]:
        """Dump event object structure for debugging.

        Args:
            event: ADK event object.

        Returns:
            Dictionary with event type and serialized attributes.
        """
        dump: dict[str, Any] = {
            "type": type(event).__name__,
            "attributes": {},
        }

        # Extract key attributes safely
        for attr in ["author", "content", "grounding_metadata", "candidates", "actions"]:
            if hasattr(event, attr):
                value = getattr(event, attr)
                dump["attributes"][attr] = self._safe_serialize(value)

        return dump

    def _safe_serialize(self, obj: Any) -> Any:
        """Safely serialize object to JSON-compatible format.

        Args:
            obj: Object to serialize.

        Returns:
            JSON-serializable representation of the object.
        """
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._safe_serialize(item) for item in obj[:10]]  # Limit list size
        if hasattr(obj, "model_dump"):  # Pydantic model
            try:
                return obj.model_dump()
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            return {
                "__class__": type(obj).__name__,
                "__attrs__": {
                    k: self._safe_serialize(v)
                    for k, v in list(vars(obj).items())[:20]  # Limit attribute count
                    if not k.startswith("_")
                },
            }
        return str(obj)[:500]  # Truncate long strings

    def _extract_grounding(self, grounding: Any) -> dict[str, Any]:
        """Extract structured data from grounding metadata.

        Handles multiple data structures:
        1. grounding_chunks.web (legacy/standard)
        2. search_entry_point (current ADK)
        3. web_search_queries
        4. Direct URL attributes (fallback)

        Args:
            grounding: Grounding metadata from ADK response.

        Returns:
            Dictionary with extracted source information.
        """
        result: dict[str, Any] = {"sources": []}

        # Log grounding object structure for debugging
        grounding_type = type(grounding).__name__
        available_attrs = [a for a in dir(grounding) if not a.startswith("_")]
        logger.debug(f"Grounding type: {grounding_type}, attrs: {available_attrs}")

        # Extract from grounding_chunks (search results)
        if hasattr(grounding, "grounding_chunks"):
            chunks = grounding.grounding_chunks or []
            logger.debug(f"Found {len(chunks)} grounding_chunks")
            for i, chunk in enumerate(chunks):
                if hasattr(chunk, "web") and chunk.web:
                    # Try both 'uri' and 'url' attributes
                    url = getattr(chunk.web, "uri", "") or getattr(chunk.web, "url", "")
                    source = {
                        "url": url,
                        "title": getattr(chunk.web, "title", ""),
                    }
                    logger.debug(f"Chunk[{i}]: url={source['url'][:50] if source['url'] else '(empty)'}")
                    if source["url"]:
                        result["sources"].append(source)

        # Extract from search_entry_point
        if hasattr(grounding, "search_entry_point") and grounding.search_entry_point:
            sep = grounding.search_entry_point
            if hasattr(sep, "rendered_content"):
                result["rendered_content"] = sep.rendered_content
            if hasattr(sep, "sdk_blob"):
                result["sdk_blob_preview"] = str(sep.sdk_blob)[:200]
            logger.debug(f"Found search_entry_point: has_rendered_content={hasattr(sep, 'rendered_content')}")

        # Extract web search queries
        if hasattr(grounding, "web_search_queries"):
            queries = list(grounding.web_search_queries or [])
            result["queries"] = queries
            logger.debug(f"Found {len(queries)} web_search_queries")

        # Fallback: try to find URL-like attributes directly
        if not result["sources"]:
            for attr_name in available_attrs:
                try:
                    attr = getattr(grounding, attr_name, None)
                    if isinstance(attr, str) and attr.startswith("http"):
                        result["sources"].append({"url": attr, "title": ""})
                        logger.debug(f"Found URL in attribute '{attr_name}': {attr[:50]}")
                except Exception:
                    pass

        # Log extraction results
        source_count = len(result["sources"])
        if source_count > 0:
            logger.debug(f"Extracted {source_count} sources from grounding_metadata")
        else:
            logger.debug("No sources extracted from grounding_metadata")
        return result

    async def run_once(self, message: str, debug_mode: bool = False) -> dict[str, Any]:
        """Execute the agent with a one-time session.

        Creates a unique user_id and session for a single execution.
        Useful for stateless operations.

        Args:
            message: User message/query to process.
            debug_mode: Enable debug mode to capture detailed event information.

        Returns:
            Dictionary containing response content and events.
        """
        unique_user_id = f"user_{uuid.uuid4().hex[:8]}"
        return await self.run(unique_user_id, message, debug_mode=debug_mode)

    async def cleanup(self) -> None:
        """Clean up session resources.

        Clears all active sessions tracked by this wrapper.
        Note: InMemorySessionService sessions are automatically cleaned
        when the service is garbage collected.
        """
        session_count = len(self._active_sessions)
        self._active_sessions.clear()
        logger.debug(f"Cleaned up {session_count} active sessions")

    def get_session_id(self, user_id: str) -> str | None:
        """Get the active session ID for a user.

        Args:
            user_id: User identifier.

        Returns:
            Session ID if exists, None otherwise.
        """
        return self._active_sessions.get(user_id)


__all__ = ["ADKRunnerWrapper"]
