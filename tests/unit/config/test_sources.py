"""Unit tests for configuration sources: SourceTrace and TracingSourceWrapper."""

from datetime import UTC, datetime

import pytest

from mixseek.config.sources.tracing_source import SourceTrace, TracingSourceWrapper


class TestSourceTrace:
    """SourceTraceデータクラスのテスト"""

    def test_creation_with_all_fields(self) -> None:
        """Test SourceTrace creation with all fields"""
        now = datetime.now(UTC)
        trace = SourceTrace(
            value="openai:gpt-4o",
            source_name="environment_variables",
            source_type="env",
            field_name="model",
            timestamp=now,
        )

        assert trace.value == "openai:gpt-4o"
        assert trace.source_name == "environment_variables"
        assert trace.source_type == "env"
        assert trace.field_name == "model"
        assert trace.timestamp == now

    def test_immutability(self) -> None:
        """Test SourceTrace immutability (dataclass frozen)"""
        trace = SourceTrace(
            value="test",
            source_name="test_source",
            source_type="test",
            field_name="test_field",
            timestamp=datetime.now(UTC),
        )

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            trace.value = "new_value"  # type: ignore

    def test_timestamp_is_utc_datetime(self) -> None:
        """Test timestamp is UTC datetime"""
        now = datetime.now(UTC)
        trace = SourceTrace(
            value="test",
            source_name="test",
            source_type="test",
            field_name="test",
            timestamp=now,
        )

        assert isinstance(trace.timestamp, datetime)
        assert trace.timestamp.tzinfo is not None
        assert trace.timestamp.tzinfo == UTC

    def test_various_source_types(self) -> None:
        """Test various source types"""
        source_types = ["cli", "env", "toml", "dotenv", "secrets"]
        now = datetime.now(UTC)

        for source_type in source_types:
            trace = SourceTrace(
                value="test_value",
                source_name=f"test_{source_type}",
                source_type=source_type,
                field_name="test_field",
                timestamp=now,
            )
            assert trace.source_type == source_type

    def test_various_value_types(self) -> None:
        """Test various value types"""
        now = datetime.now(UTC)

        # String value
        trace_str = SourceTrace(
            value="string_value",
            source_name="test",
            source_type="env",
            field_name="field",
            timestamp=now,
        )
        assert trace_str.value == "string_value"

        # Integer value
        trace_int = SourceTrace(
            value=300,
            source_name="test",
            source_type="env",
            field_name="field",
            timestamp=now,
        )
        assert trace_int.value == 300

        # Float value
        trace_float = SourceTrace(
            value=0.7,
            source_name="test",
            source_type="env",
            field_name="field",
            timestamp=now,
        )
        assert trace_float.value == 0.7

        # None value
        trace_none = SourceTrace(
            value=None,
            source_name="test",
            source_type="env",
            field_name="field",
            timestamp=now,
        )
        assert trace_none.value is None


class TestTracingSourceWrapper:
    """TracingSourceWrapperのテスト"""

    def test_wraps_source_and_records_trace(self) -> None:
        """Test that wrapper records trace information when values are found"""
        from unittest.mock import MagicMock

        from pydantic import Field
        from pydantic_settings import BaseSettings

        # Create a simple settings class
        class TestSettings(BaseSettings):
            test_field: str = Field(default="default_value")

        # Create a mock source that returns a value
        mock_source = MagicMock()
        mock_source.return_value = {"test_field": "mock_value"}

        # Create trace storage
        trace_storage: dict[str, SourceTrace] = {}

        # Create TracingSourceWrapper
        wrapper = TracingSourceWrapper(
            settings_cls=TestSettings,
            wrapped_source=mock_source,
            source_name="test_source",
            source_type="test",
            trace_storage=trace_storage,
        )

        # Call the wrapper
        result = wrapper()

        # Verify the wrapper called the wrapped source
        mock_source.assert_called_once()

        # Verify the result is correct
        assert result == {"test_field": "mock_value"}

        # Verify trace information is recorded
        assert "test_field" in trace_storage
        trace = trace_storage["test_field"]
        assert trace.value == "mock_value"
        assert trace.source_name == "test_source"
        assert trace.source_type == "test"
        assert trace.field_name == "test_field"
        assert isinstance(trace.timestamp, datetime)

    def test_wrapper_with_empty_source(self) -> None:
        """Test wrapper with source that returns no values"""
        from unittest.mock import MagicMock

        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            test_field: str = Field(default="default_value")

        # Create a mock source that returns empty dict
        mock_source = MagicMock()
        mock_source.return_value = {}

        trace_storage: dict[str, SourceTrace] = {}

        wrapper = TracingSourceWrapper(
            settings_cls=TestSettings,
            wrapped_source=mock_source,
            source_name="empty_source",
            source_type="test",
            trace_storage=trace_storage,
        )

        result = wrapper()

        # Verify empty result
        assert result == {}

        # Verify no trace information is recorded
        assert len(trace_storage) == 0

    def test_wrapper_preserves_source_name_and_type(self) -> None:
        """Test that wrapper preserves source name and type in traces"""
        from unittest.mock import MagicMock

        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            field1: str = Field(default="default1")
            field2: int = Field(default=42)

        mock_source = MagicMock()
        mock_source.return_value = {"field1": "value1", "field2": 100}

        trace_storage: dict[str, SourceTrace] = {}

        wrapper = TracingSourceWrapper(
            settings_cls=TestSettings,
            wrapped_source=mock_source,
            source_name="custom_source.toml",
            source_type="toml",
            trace_storage=trace_storage,
        )

        wrapper()

        # Verify both fields have correct source info
        assert trace_storage["field1"].source_name == "custom_source.toml"
        assert trace_storage["field1"].source_type == "toml"
        assert trace_storage["field2"].source_name == "custom_source.toml"
        assert trace_storage["field2"].source_type == "toml"
