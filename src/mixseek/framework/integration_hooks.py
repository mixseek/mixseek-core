"""MixSeek-Core Framework Integration Hooks.

This module provides integration hooks and interfaces for connecting
Member Agents with the broader MixSeek-Core framework and Leader Agent system.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from mixseek.models.member_agent import MemberAgentConfig, MemberAgentResult

logger = logging.getLogger(__name__)


class IntegrationEventType(Enum):
    """Types of integration events."""

    AGENT_CREATED = "agent_created"
    AGENT_INITIALIZED = "agent_initialized"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    RESULT_FORMATTED = "result_formatted"
    ERROR_RECOVERED = "error_recovered"
    CONFIGURATION_VALIDATED = "configuration_validated"


@dataclass
class IntegrationEvent:
    """Integration event data structure."""

    event_type: IntegrationEventType
    timestamp: datetime
    agent_name: str
    agent_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] | None = None
    error: str | None = None


class IntegrationHook(ABC):
    """Base class for integration hooks."""

    @abstractmethod
    async def handle_event(self, event: IntegrationEvent) -> None:
        """Handle an integration event.

        Args:
            event: The integration event to handle
        """
        pass

    @abstractmethod
    def is_interested_in(self, event_type: IntegrationEventType) -> bool:
        """Check if this hook is interested in the given event type.

        Args:
            event_type: The event type to check

        Returns:
            True if the hook should handle this event type
        """
        pass


class LoggingIntegrationHook(IntegrationHook):
    """Integration hook that logs all events."""

    def __init__(self, log_level: str = "INFO"):
        """Initialize logging hook.

        Args:
            log_level: Logging level for integration events
        """
        self.logger = logging.getLogger(f"{__name__}.integration")
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

    async def handle_event(self, event: IntegrationEvent) -> None:
        """Log the integration event."""
        message = (
            f"Integration Event: {event.event_type.value} | "
            f"Agent: {event.agent_name} ({event.agent_type}) | "
            f"Timestamp: {event.timestamp.isoformat()}"
        )

        if event.error:
            message += f" | Error: {event.error}"

        if event.metadata:
            message += f" | Metadata: {json.dumps(event.metadata)}"

        self.logger.log(self.log_level, message)

    def is_interested_in(self, event_type: IntegrationEventType) -> bool:
        """Log all event types."""
        return True


class MetricsIntegrationHook(IntegrationHook):
    """Integration hook that collects metrics."""

    def __init__(self) -> None:
        """Initialize metrics collection."""
        self.metrics: dict[str, Any] = {
            "total_events": 0,
            "events_by_type": {},
            "agents_created": 0,
            "executions_completed": 0,
            "executions_failed": 0,
            "errors_recovered": 0,
            "total_execution_time_ms": 0,
            "average_execution_time_ms": 0.0,
        }
        self._execution_times: list[float] = []

    async def handle_event(self, event: IntegrationEvent) -> None:
        """Collect metrics from the integration event."""
        self.metrics["total_events"] += 1

        # Count by event type
        event_type_key = event.event_type.value
        self.metrics["events_by_type"][event_type_key] = self.metrics["events_by_type"].get(event_type_key, 0) + 1

        # Specific metrics by event type
        if event.event_type == IntegrationEventType.AGENT_CREATED:
            self.metrics["agents_created"] += 1

        elif event.event_type == IntegrationEventType.EXECUTION_COMPLETED:
            self.metrics["executions_completed"] += 1

            # Track execution time if available
            if event.payload and "execution_time_ms" in event.payload:
                exec_time = event.payload["execution_time_ms"]
                self.metrics["total_execution_time_ms"] += exec_time
                self._execution_times.append(exec_time)

                # Update average
                if self._execution_times:
                    self.metrics["average_execution_time_ms"] = sum(self._execution_times) / len(self._execution_times)

        elif event.event_type == IntegrationEventType.EXECUTION_FAILED:
            self.metrics["executions_failed"] += 1

        elif event.event_type == IntegrationEventType.ERROR_RECOVERED:
            self.metrics["errors_recovered"] += 1

    def is_interested_in(self, event_type: IntegrationEventType) -> bool:
        """Collect metrics for all event types."""
        return True

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = {
            "total_events": 0,
            "events_by_type": {},
            "agents_created": 0,
            "executions_completed": 0,
            "executions_failed": 0,
            "errors_recovered": 0,
            "total_execution_time_ms": 0,
            "average_execution_time_ms": 0.0,
        }
        self._execution_times.clear()


class WebhookIntegrationHook(IntegrationHook):
    """Integration hook that sends events to external webhooks."""

    def __init__(self, webhook_url: str, event_types: list[IntegrationEventType] | None = None):
        """Initialize webhook integration.

        Args:
            webhook_url: URL to send webhook events to
            event_types: List of event types to send (None = all events)
        """
        self.webhook_url = webhook_url
        self.event_types = set(event_types) if event_types else None

    async def handle_event(self, event: IntegrationEvent) -> None:
        """Send event to webhook."""
        try:
            import aiohttp

            payload = {
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "agent_name": event.agent_name,
                "agent_type": event.agent_type,
                "metadata": event.metadata,
                "payload": event.payload,
                "error": event.error,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status >= 400:
                        logger.warning(f"Webhook returned {response.status} for event {event.event_type.value}")

        except Exception as e:
            logger.error(f"Failed to send webhook for event {event.event_type.value}: {e}")

    def is_interested_in(self, event_type: IntegrationEventType) -> bool:
        """Check if this event type should be sent to webhook."""
        if self.event_types is None:
            return True
        return event_type in self.event_types


class CustomIntegrationHook(IntegrationHook):
    """Integration hook with custom handler functions."""

    def __init__(
        self,
        handler: Callable[[IntegrationEvent], None],
        event_types: list[IntegrationEventType] | None = None,
        async_handler: bool = False,
    ):
        """Initialize custom integration hook.

        Args:
            handler: Custom handler function
            event_types: List of event types to handle (None = all events)
            async_handler: Whether the handler is async
        """
        self.handler = handler
        self.event_types = set(event_types) if event_types else None
        self.async_handler = async_handler

    async def handle_event(self, event: IntegrationEvent) -> None:
        """Handle event with custom function."""
        try:
            if self.async_handler:
                # Type ignore because we know the handler is async based on the flag
                await self.handler(event)  # type: ignore[misc]
            else:
                self.handler(event)
        except Exception as e:
            logger.error(f"Custom integration handler failed for event {event.event_type.value}: {e}")

    def is_interested_in(self, event_type: IntegrationEventType) -> bool:
        """Check if this event type should be handled."""
        if self.event_types is None:
            return True
        return event_type in self.event_types


class IntegrationManager:
    """Manager for integration hooks and events."""

    def __init__(self) -> None:
        """Initialize integration manager."""
        self.hooks: list[IntegrationHook] = []
        self.event_queue: asyncio.Queue[IntegrationEvent] | None = None
        self.is_processing = False
        self._processor_task: asyncio.Task[None] | None = None
        self._current_loop: asyncio.AbstractEventLoop | None = None

    def _ensure_queue(self) -> asyncio.Queue[IntegrationEvent]:
        """Ensure queue exists in current event loop.

        Returns:
            asyncio.Queue: Event queue bound to current event loop

        Note:
            If the event loop has changed, the old queue and processor task are discarded
            and a new queue is created for the current event loop.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - should not happen in async context
            logger.warning("No running event loop in _ensure_queue()")
            if self.event_queue is None:
                self.event_queue = asyncio.Queue()
            return self.event_queue

        # Check if event loop has changed
        if self._current_loop is not None and self._current_loop is not current_loop:
            logger.debug(
                f"Event loop changed (old={id(self._current_loop)}, new={id(current_loop)}), "
                "creating new queue and canceling old processor"
            )
            # Cancel old processor task if running
            if self._processor_task and not self._processor_task.done():
                self._processor_task.cancel()
            # Reset state for new event loop
            self.event_queue = None
            self._processor_task = None
            self.is_processing = False

        # Update current loop reference
        self._current_loop = current_loop

        # Create queue if needed
        if self.event_queue is None:
            self.event_queue = asyncio.Queue()
            logger.debug(f"Created new queue for event loop {id(current_loop)}")

        return self.event_queue

    def register_hook(self, hook: IntegrationHook) -> None:
        """Register an integration hook.

        Args:
            hook: The integration hook to register
        """
        self.hooks.append(hook)
        logger.debug(f"Registered integration hook: {type(hook).__name__}")

    def unregister_hook(self, hook: IntegrationHook) -> None:
        """Unregister an integration hook.

        Args:
            hook: The integration hook to unregister
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
            logger.debug(f"Unregistered integration hook: {type(hook).__name__}")

    async def emit_event(self, event: IntegrationEvent) -> None:
        """Emit an integration event to all interested hooks.

        Args:
            event: The integration event to emit
        """
        queue = self._ensure_queue()
        await queue.put(event)

        # Start processor if not already running
        if not self.is_processing:
            self._processor_task = asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        """Process events from the queue."""
        self.is_processing = True
        queue = self._ensure_queue()

        try:
            while True:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)

                    # Send event to interested hooks
                    tasks = []
                    for hook in self.hooks:
                        if hook.is_interested_in(event.event_type):
                            tasks.append(hook.handle_event(event))

                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                    # Mark task as done
                    queue.task_done()

                except TimeoutError:
                    # No events to process, continue
                    continue
                except Exception as e:
                    logger.error(f"Error processing integration event: {e}")

        except asyncio.CancelledError:
            logger.debug("Integration event processor cancelled")
        finally:
            self.is_processing = False

    async def stop_processing(self) -> None:
        """Stop event processing."""
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        self.is_processing = False

    def get_registered_hooks(self) -> list[str]:
        """Get list of registered hook class names."""
        return [type(hook).__name__ for hook in self.hooks]


# Global integration manager instance
_integration_manager: IntegrationManager | None = None


def get_integration_manager() -> IntegrationManager:
    """Get the global integration manager instance."""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = IntegrationManager()
    return _integration_manager


async def emit_agent_created_event(config: MemberAgentConfig) -> None:
    """Emit agent created event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.AGENT_CREATED,
        timestamp=datetime.now(UTC),
        agent_name=config.name,
        agent_type=config.type,
        metadata={"model": config.model, "temperature": config.temperature, "max_tokens": config.max_tokens},
        payload={"config_hash": hash(str(config))},
    )
    await get_integration_manager().emit_event(event)


async def emit_agent_initialized_event(agent_name: str, agent_type: str) -> None:
    """Emit agent initialized event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.AGENT_INITIALIZED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
    )
    await get_integration_manager().emit_event(event)


async def emit_execution_started_event(agent_name: str, agent_type: str, prompt: str) -> None:
    """Emit execution started event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.EXECUTION_STARTED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
        metadata={"prompt_length": len(prompt)},
        payload={"prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt},
    )
    await get_integration_manager().emit_event(event)


async def emit_execution_completed_event(
    agent_name: str, agent_type: str, result: MemberAgentResult, execution_time_ms: int
) -> None:
    """Emit execution completed event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.EXECUTION_COMPLETED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
        metadata={
            "status": result.status.value,
            "content_length": len(result.content) if result.content else 0,
            "retry_count": result.retry_count or 0,
            "usage_info": result.usage_info or {},
        },
        payload={"execution_time_ms": execution_time_ms, "result_hash": hash(str(result))},
    )
    await get_integration_manager().emit_event(event)


async def emit_execution_failed_event(agent_name: str, agent_type: str, error: str, execution_time_ms: int) -> None:
    """Emit execution failed event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.EXECUTION_FAILED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
        error=error,
        payload={"execution_time_ms": execution_time_ms},
    )
    await get_integration_manager().emit_event(event)


async def emit_result_formatted_event(
    agent_name: str, agent_type: str, format_type: str, result: MemberAgentResult
) -> None:
    """Emit result formatted event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.RESULT_FORMATTED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
        metadata={
            "format_type": format_type,
            "status": result.status.value,
            "content_length": len(result.content) if result.content else 0,
        },
    )
    await get_integration_manager().emit_event(event)


async def emit_error_recovered_event(
    agent_name: str, agent_type: str, recovery_type: str, original_error: str
) -> None:
    """Emit error recovered event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.ERROR_RECOVERED,
        timestamp=datetime.now(UTC),
        agent_name=agent_name,
        agent_type=agent_type,
        metadata={"recovery_type": recovery_type},
        payload={"original_error": original_error},
    )
    await get_integration_manager().emit_event(event)


async def emit_configuration_validated_event(
    config_name: str, is_valid: bool, errors: list[str], warnings: list[str]
) -> None:
    """Emit configuration validated event."""
    event = IntegrationEvent(
        event_type=IntegrationEventType.CONFIGURATION_VALIDATED,
        timestamp=datetime.now(UTC),
        agent_name=config_name,
        agent_type="validation",
        metadata={"is_valid": is_valid, "error_count": len(errors), "warning_count": len(warnings)},
        payload={"errors": errors, "warnings": warnings},
    )
    await get_integration_manager().emit_event(event)


# Convenience functions for common integration setups
def setup_basic_logging_integration(log_level: str = "INFO") -> None:
    """Set up basic logging integration.

    Args:
        log_level: Log level for integration events
    """
    manager = get_integration_manager()
    logging_hook = LoggingIntegrationHook(log_level)
    manager.register_hook(logging_hook)


def setup_metrics_collection() -> MetricsIntegrationHook:
    """Set up metrics collection integration.

    Returns:
        The metrics hook for accessing collected metrics
    """
    manager = get_integration_manager()
    metrics_hook = MetricsIntegrationHook()
    manager.register_hook(metrics_hook)
    return metrics_hook


def setup_webhook_integration(webhook_url: str, event_types: list[IntegrationEventType] | None = None) -> None:
    """Set up webhook integration.

    Args:
        webhook_url: URL to send events to
        event_types: Event types to send (None = all)
    """
    manager = get_integration_manager()
    webhook_hook = WebhookIntegrationHook(webhook_url, event_types)
    manager.register_hook(webhook_hook)


def setup_custom_integration(
    handler: Callable[[IntegrationEvent], None],
    event_types: list[IntegrationEventType] | None = None,
    async_handler: bool = False,
) -> None:
    """Set up custom integration handler.

    Args:
        handler: Custom handler function
        event_types: Event types to handle (None = all)
        async_handler: Whether handler is async
    """
    manager = get_integration_manager()
    custom_hook = CustomIntegrationHook(handler, event_types, async_handler)
    manager.register_hook(custom_hook)
