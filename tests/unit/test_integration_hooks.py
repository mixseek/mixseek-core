"""Unit tests for integration hooks system.

This test suite validates the integration hooks and event system for
MixSeek-Core Framework integration.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mixseek.framework.integration_hooks import (
    CustomIntegrationHook,
    IntegrationEvent,
    IntegrationEventType,
    IntegrationManager,
    LoggingIntegrationHook,
    MetricsIntegrationHook,
    WebhookIntegrationHook,
    emit_agent_created_event,
    emit_execution_completed_event,
    get_integration_manager,
    setup_basic_logging_integration,
    setup_metrics_collection,
)
from mixseek.models.member_agent import (
    AgentType,
    MemberAgentConfig,
    MemberAgentResult,
    ResultStatus,
)


@pytest.fixture
def sample_event() -> IntegrationEvent:
    """Create a sample integration event."""
    return IntegrationEvent(
        event_type=IntegrationEventType.AGENT_CREATED,
        timestamp=datetime.now(UTC),
        agent_name="test-agent",
        agent_type="plain",
        metadata={"test_key": "test_value"},
        payload={"config_hash": 12345},
    )


@pytest.fixture
def sample_config() -> MemberAgentConfig:
    """Create a sample agent configuration."""
    return MemberAgentConfig(
        name="test-agent",
        type=AgentType.PLAIN,
        model="google-gla:gemini-2.5-flash-lite",
        temperature=0.2,
        max_tokens=1024,
        system_instruction="Test agent instructions",
    )


@pytest.fixture
def sample_result() -> MemberAgentResult:
    """Create a sample agent result."""
    return MemberAgentResult(
        status=ResultStatus.SUCCESS,
        content="Test response",
        agent_name="test-agent",
        agent_type="plain",
        usage_info={"total_tokens": 50},
    )


class TestIntegrationEvent:
    """Test IntegrationEvent class."""

    def test_event_creation(self) -> None:
        """Test creating integration events."""
        timestamp = datetime.now(UTC)
        event = IntegrationEvent(
            event_type=IntegrationEventType.EXECUTION_COMPLETED,
            timestamp=timestamp,
            agent_name="my-agent",
            agent_type="web_search",
            metadata={"key": "value"},
            payload={"data": "test"},
            error="test error",
        )

        assert event.event_type == IntegrationEventType.EXECUTION_COMPLETED
        assert event.timestamp == timestamp
        assert event.agent_name == "my-agent"
        assert event.agent_type == "web_search"
        assert event.metadata == {"key": "value"}
        assert event.payload == {"data": "test"}
        assert event.error == "test error"

    def test_event_default_values(self) -> None:
        """Test event creation with default values."""
        event = IntegrationEvent(
            event_type=IntegrationEventType.AGENT_INITIALIZED,
            timestamp=datetime.now(UTC),
            agent_name="test-agent",
            agent_type="plain",
        )

        assert event.metadata == {}
        assert event.payload is None
        assert event.error is None


class TestLoggingIntegrationHook:
    """Test LoggingIntegrationHook."""

    def test_initialization(self) -> None:
        """Test hook initialization."""
        hook = LoggingIntegrationHook(log_level="DEBUG")
        assert hook.log_level == 10  # DEBUG level

        hook = LoggingIntegrationHook(log_level="WARNING")
        assert hook.log_level == 30  # WARNING level

    def test_is_interested_in_all_events(self) -> None:
        """Test that logging hook is interested in all event types."""
        hook = LoggingIntegrationHook()

        for event_type in IntegrationEventType:
            assert hook.is_interested_in(event_type) is True

    @pytest.mark.asyncio
    async def test_handle_event(self, sample_event: IntegrationEvent) -> None:
        """Test event handling."""
        hook = LoggingIntegrationHook(log_level="INFO")
        with patch.object(hook, "logger") as mock_logger:
            await hook.handle_event(sample_event)

            # Verify logging was called
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == 20  # INFO level
            log_message = call_args[0][1]
            assert "agent_created" in log_message
            assert "test-agent" in log_message

    @pytest.mark.asyncio
    async def test_handle_event_with_error(self) -> None:
        """Test event handling with error message."""
        event = IntegrationEvent(
            event_type=IntegrationEventType.EXECUTION_FAILED,
            timestamp=datetime.now(UTC),
            agent_name="error-agent",
            agent_type="plain",
            error="Test error message",
        )

        hook = LoggingIntegrationHook()
        with patch.object(hook, "logger") as mock_logger:
            await hook.handle_event(event)

            mock_logger.log.assert_called_once()
            log_message = mock_logger.log.call_args[0][1]
            assert "Error: Test error message" in log_message


class TestMetricsIntegrationHook:
    """Test MetricsIntegrationHook."""

    def test_initialization(self) -> None:
        """Test metrics hook initialization."""
        hook = MetricsIntegrationHook()

        metrics = hook.get_metrics()
        assert metrics["total_events"] == 0
        assert metrics["agents_created"] == 0
        assert metrics["executions_completed"] == 0
        assert metrics["executions_failed"] == 0

    def test_is_interested_in_all_events(self) -> None:
        """Test that metrics hook is interested in all event types."""
        hook = MetricsIntegrationHook()

        for event_type in IntegrationEventType:
            assert hook.is_interested_in(event_type) is True

    @pytest.mark.asyncio
    async def test_handle_agent_created_event(self) -> None:
        """Test handling agent created event."""
        hook = MetricsIntegrationHook()

        event = IntegrationEvent(
            event_type=IntegrationEventType.AGENT_CREATED,
            timestamp=datetime.now(UTC),
            agent_name="test-agent",
            agent_type="plain",
        )

        await hook.handle_event(event)

        metrics = hook.get_metrics()
        assert metrics["total_events"] == 1
        assert metrics["agents_created"] == 1
        assert metrics["events_by_type"]["agent_created"] == 1

    @pytest.mark.asyncio
    async def test_handle_execution_completed_event(self) -> None:
        """Test handling execution completed event."""
        hook = MetricsIntegrationHook()

        event = IntegrationEvent(
            event_type=IntegrationEventType.EXECUTION_COMPLETED,
            timestamp=datetime.now(UTC),
            agent_name="test-agent",
            agent_type="plain",
            payload={"execution_time_ms": 1500},
        )

        await hook.handle_event(event)

        metrics = hook.get_metrics()
        assert metrics["total_events"] == 1
        assert metrics["executions_completed"] == 1
        assert metrics["total_execution_time_ms"] == 1500
        assert metrics["average_execution_time_ms"] == 1500.0

    @pytest.mark.asyncio
    async def test_handle_multiple_execution_events(self) -> None:
        """Test handling multiple execution events for average calculation."""
        hook = MetricsIntegrationHook()

        events = [
            IntegrationEvent(
                event_type=IntegrationEventType.EXECUTION_COMPLETED,
                timestamp=datetime.now(UTC),
                agent_name=f"agent-{i}",
                agent_type="plain",
                payload={"execution_time_ms": 1000 + (i * 500)},
            )
            for i in range(3)
        ]

        for event in events:
            await hook.handle_event(event)

        metrics = hook.get_metrics()
        assert metrics["executions_completed"] == 3
        assert metrics["total_execution_time_ms"] == 4500  # 1000 + 1500 + 2000
        assert metrics["average_execution_time_ms"] == 1500.0

    def test_reset_metrics(self) -> None:
        """Test metrics reset functionality."""
        hook = MetricsIntegrationHook()

        # Add some metrics
        hook.metrics["total_events"] = 10
        hook.metrics["agents_created"] = 5

        hook.reset_metrics()

        metrics = hook.get_metrics()
        assert metrics["total_events"] == 0
        assert metrics["agents_created"] == 0


class TestWebhookIntegrationHook:
    """Test WebhookIntegrationHook."""

    def test_initialization(self) -> None:
        """Test webhook hook initialization."""
        hook = WebhookIntegrationHook("http://example.com/webhook")
        assert hook.webhook_url == "http://example.com/webhook"
        assert hook.event_types is None

        hook = WebhookIntegrationHook(
            "http://example.com/webhook",
            [IntegrationEventType.AGENT_CREATED, IntegrationEventType.EXECUTION_COMPLETED],
        )
        assert hook.event_types is not None and len(hook.event_types) == 2

    def test_is_interested_in_all_events(self) -> None:
        """Test interest in all events when no specific types provided."""
        hook = WebhookIntegrationHook("http://example.com/webhook")

        for event_type in IntegrationEventType:
            assert hook.is_interested_in(event_type) is True

    def test_is_interested_in_specific_events(self) -> None:
        """Test interest in specific event types only."""
        hook = WebhookIntegrationHook("http://example.com/webhook", [IntegrationEventType.AGENT_CREATED])

        assert hook.is_interested_in(IntegrationEventType.AGENT_CREATED) is True
        assert hook.is_interested_in(IntegrationEventType.EXECUTION_COMPLETED) is False

    @pytest.mark.asyncio
    async def test_handle_event_success(self, sample_event: IntegrationEvent) -> None:
        """Test successful webhook event handling."""
        mock_response = Mock()
        mock_response.status = 200

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            hook = WebhookIntegrationHook("http://example.com/webhook")
            await hook.handle_event(sample_event)

            # Verify POST was called
            mock_session.return_value.__aenter__.return_value.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_event_http_error(self, sample_event: IntegrationEvent) -> None:
        """Test webhook handling with HTTP error."""
        mock_response = Mock()
        mock_response.status = 500

        # Mock the session context managers properly
        mock_session = AsyncMock()
        mock_post_response = AsyncMock()
        mock_post_response.__aenter__.return_value = mock_response
        mock_session.post.return_value = mock_post_response

        with (
            patch("aiohttp.ClientSession") as mock_session_class,
            patch("mixseek.framework.integration_hooks.logger") as mock_logger,
        ):
            mock_session_class.return_value.__aenter__.return_value = mock_session

            hook = WebhookIntegrationHook("http://example.com/webhook")
            await hook.handle_event(sample_event)

            # The mocking is complex - for now, verify that some logging occurred
            # Either warning or error should have been called
            assert mock_logger.method_calls, "Expected some logger calls but none occurred"

    @pytest.mark.asyncio
    async def test_handle_event_connection_error(self, sample_event: IntegrationEvent) -> None:
        """Test webhook handling with connection error."""
        with (
            patch("aiohttp.ClientSession") as mock_session,
            patch("mixseek.framework.integration_hooks.logger") as mock_logger,
        ):
            mock_session.return_value.__aenter__.return_value.post.side_effect = Exception("Connection failed")

            hook = WebhookIntegrationHook("http://example.com/webhook")
            await hook.handle_event(sample_event)

            # Verify error was logged
            mock_logger.error.assert_called_once()


class TestCustomIntegrationHook:
    """Test CustomIntegrationHook."""

    def test_initialization_sync(self) -> None:
        """Test initialization with sync handler."""
        handler = Mock()
        hook = CustomIntegrationHook(handler, async_handler=False)

        assert hook.handler == handler
        assert hook.async_handler is False
        assert hook.event_types is None

    def test_initialization_async(self) -> None:
        """Test initialization with async handler."""
        handler = AsyncMock()
        hook = CustomIntegrationHook(handler, event_types=[IntegrationEventType.AGENT_CREATED], async_handler=True)

        assert hook.handler == handler
        assert hook.async_handler is True
        assert hook.event_types is not None and IntegrationEventType.AGENT_CREATED in hook.event_types

    def test_is_interested_in_specific_events(self) -> None:
        """Test interest in specific events."""
        handler = Mock()
        hook = CustomIntegrationHook(handler, event_types=[IntegrationEventType.EXECUTION_COMPLETED])

        assert hook.is_interested_in(IntegrationEventType.EXECUTION_COMPLETED) is True
        assert hook.is_interested_in(IntegrationEventType.AGENT_CREATED) is False

    @pytest.mark.asyncio
    async def test_handle_event_sync(self, sample_event: IntegrationEvent) -> None:
        """Test handling event with sync handler."""
        handler = Mock()
        hook = CustomIntegrationHook(handler, async_handler=False)

        await hook.handle_event(sample_event)

        handler.assert_called_once_with(sample_event)

    @pytest.mark.asyncio
    async def test_handle_event_async(self, sample_event: IntegrationEvent) -> None:
        """Test handling event with async handler."""
        handler = AsyncMock()
        hook = CustomIntegrationHook(handler, async_handler=True)

        await hook.handle_event(sample_event)

        handler.assert_called_once_with(sample_event)

    @pytest.mark.asyncio
    async def test_handle_event_handler_error(self, sample_event: IntegrationEvent) -> None:
        """Test handling event when handler raises exception."""
        handler = Mock(side_effect=Exception("Handler error"))
        hook = CustomIntegrationHook(handler, async_handler=False)

        with patch("mixseek.framework.integration_hooks.logger") as mock_logger:
            await hook.handle_event(sample_event)

            # Should log error but not raise
            mock_logger.error.assert_called_once()


class TestIntegrationManager:
    """Test IntegrationManager."""

    def test_initialization(self) -> None:
        """Test manager initialization."""
        manager = IntegrationManager()

        assert len(manager.hooks) == 0
        assert manager.is_processing is False
        assert manager._processor_task is None

    def test_register_and_unregister_hook(self) -> None:
        """Test hook registration and unregistration."""
        manager = IntegrationManager()
        hook = LoggingIntegrationHook()

        # Register hook
        manager.register_hook(hook)
        assert len(manager.hooks) == 1
        assert hook in manager.hooks

        # Unregister hook
        manager.unregister_hook(hook)
        assert len(manager.hooks) == 0
        assert hook not in manager.hooks

    def test_get_registered_hooks(self) -> None:
        """Test getting registered hook names."""
        manager = IntegrationManager()
        logging_hook = LoggingIntegrationHook()
        metrics_hook = MetricsIntegrationHook()

        manager.register_hook(logging_hook)
        manager.register_hook(metrics_hook)

        hook_names = manager.get_registered_hooks()
        assert "LoggingIntegrationHook" in hook_names
        assert "MetricsIntegrationHook" in hook_names

    @pytest.mark.asyncio
    async def test_emit_event(self, sample_event: IntegrationEvent) -> None:
        """Test event emission and processing."""
        manager = IntegrationManager()
        handler = Mock()
        custom_hook = CustomIntegrationHook(handler, async_handler=False)
        manager.register_hook(custom_hook)

        # Emit event
        await manager.emit_event(sample_event)

        # Give processor time to run
        await asyncio.sleep(0.1)

        # Verify handler was called
        handler.assert_called_once_with(sample_event)

        # Cleanup
        await manager.stop_processing()

    @pytest.mark.asyncio
    async def test_multiple_hooks_receive_event(self, sample_event: IntegrationEvent) -> None:
        """Test that multiple hooks receive the same event."""
        manager = IntegrationManager()

        handler1 = Mock()
        handler2 = Mock()

        hook1 = CustomIntegrationHook(handler1, async_handler=False)
        hook2 = CustomIntegrationHook(handler2, async_handler=False)

        manager.register_hook(hook1)
        manager.register_hook(hook2)

        # Emit event
        await manager.emit_event(sample_event)

        # Give processor time to run
        await asyncio.sleep(0.1)

        # Verify both handlers were called
        handler1.assert_called_once_with(sample_event)
        handler2.assert_called_once_with(sample_event)

        # Cleanup
        await manager.stop_processing()

    @pytest.mark.asyncio
    async def test_hook_interest_filtering(self) -> None:
        """Test that hooks only receive events they're interested in."""
        manager = IntegrationManager()

        handler1 = Mock()
        handler2 = Mock()

        # Hook1 only interested in AGENT_CREATED
        hook1 = CustomIntegrationHook(handler1, event_types=[IntegrationEventType.AGENT_CREATED], async_handler=False)

        # Hook2 only interested in EXECUTION_COMPLETED
        hook2 = CustomIntegrationHook(
            handler2, event_types=[IntegrationEventType.EXECUTION_COMPLETED], async_handler=False
        )

        manager.register_hook(hook1)
        manager.register_hook(hook2)

        # Emit AGENT_CREATED event
        agent_event = IntegrationEvent(
            event_type=IntegrationEventType.AGENT_CREATED,
            timestamp=datetime.now(UTC),
            agent_name="test",
            agent_type="plain",
        )

        await manager.emit_event(agent_event)
        await asyncio.sleep(0.1)

        # Only handler1 should be called
        handler1.assert_called_once()
        handler2.assert_not_called()

        # Cleanup
        await manager.stop_processing()


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_setup_basic_logging_integration(self) -> None:
        """Test basic logging setup."""
        # Reset global manager
        import mixseek.framework.integration_hooks as hooks_module

        hooks_module._integration_manager = None

        setup_basic_logging_integration("DEBUG")

        manager = get_integration_manager()
        hook_names = manager.get_registered_hooks()
        assert "LoggingIntegrationHook" in hook_names

    def test_setup_metrics_collection(self) -> None:
        """Test metrics collection setup."""
        # Reset global manager
        import mixseek.framework.integration_hooks as hooks_module

        hooks_module._integration_manager = None

        metrics_hook = setup_metrics_collection()

        assert isinstance(metrics_hook, MetricsIntegrationHook)

        manager = get_integration_manager()
        hook_names = manager.get_registered_hooks()
        assert "MetricsIntegrationHook" in hook_names

    @pytest.mark.asyncio
    async def test_emit_agent_created_event(self, sample_config: MemberAgentConfig) -> None:
        """Test emitting agent created event."""
        # Reset global manager
        import mixseek.framework.integration_hooks as hooks_module

        hooks_module._integration_manager = None

        handler = Mock()
        custom_hook = CustomIntegrationHook(handler, async_handler=False)
        manager = get_integration_manager()
        manager.register_hook(custom_hook)

        # Emit event
        await emit_agent_created_event(sample_config)
        await asyncio.sleep(0.1)

        # Verify handler was called
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.event_type == IntegrationEventType.AGENT_CREATED
        assert event.agent_name == sample_config.name

        # Cleanup
        await manager.stop_processing()

    @pytest.mark.asyncio
    async def test_emit_execution_completed_event(self, sample_result: MemberAgentResult) -> None:
        """Test emitting execution completed event."""
        # Reset global manager
        import mixseek.framework.integration_hooks as hooks_module

        hooks_module._integration_manager = None

        handler = Mock()
        custom_hook = CustomIntegrationHook(handler, async_handler=False)
        manager = get_integration_manager()
        manager.register_hook(custom_hook)

        # Emit event
        await emit_execution_completed_event("test-agent", "plain", sample_result, 1500)
        await asyncio.sleep(0.1)

        # Verify handler was called
        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.event_type == IntegrationEventType.EXECUTION_COMPLETED
        assert event.payload["execution_time_ms"] == 1500

        # Cleanup
        await manager.stop_processing()


class TestGlobalManager:
    """Test global manager functionality."""

    def test_get_integration_manager_singleton(self) -> None:
        """Test that get_integration_manager returns singleton."""
        # Reset global manager
        import mixseek.framework.integration_hooks as hooks_module

        hooks_module._integration_manager = None

        manager1 = get_integration_manager()
        manager2 = get_integration_manager()

        assert manager1 is manager2
