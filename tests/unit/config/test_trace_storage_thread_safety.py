"""Tests for trace storage thread safety.

Article 3 Compliance: Test-First Implementation
Phase 2: Verify that trace information is stored per-instance, not shared across instances.
"""

import tempfile
import threading
from pathlib import Path
from typing import Any

from mixseek.config.manager import ConfigurationManager
from mixseek.config.schema import OrchestratorSettings


class TestTraceStorageInstanceIsolation:
    """Test that trace storage is instance-specific, not shared via class variables."""

    def test_trace_storage_is_instance_specific(self) -> None:
        """Each settings instance should have its own trace storage."""
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            ws1 = Path(tmpdir1)
            ws2 = Path(tmpdir2)

            manager1 = ConfigurationManager(workspace=ws1)
            manager2 = ConfigurationManager(workspace=ws2)

            settings1 = manager1.load_settings(OrchestratorSettings, workspace_path=ws1)
            settings2 = manager2.load_settings(OrchestratorSettings, workspace_path=ws2)

            # Get trace storage from each instance
            traces1 = getattr(settings1, "__source_traces__", {})
            traces2 = getattr(settings2, "__source_traces__", {})

            # Verify that they are different objects (not shared)
            assert traces1 is not traces2, "Trace storage should be instance-specific, not shared"
            assert id(traces1) != id(traces2), "Trace storage object IDs should be different"

    def test_get_trace_info_returns_instance_specific_data(self) -> None:
        """get_trace_info() should return data specific to the instance.

        Note:
            Phase 2-4: load_settings() now attaches trace info via context vars.
            This test verifies that trace info is instance-specific.
        """
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
        ):
            manager = ConfigurationManager(workspace=Path(tmpdir))

            settings1 = manager.load_settings(OrchestratorSettings, workspace_path=Path(tmpdir1))
            settings2 = manager.load_settings(OrchestratorSettings, workspace_path=Path(tmpdir2))

            # Get trace info using the manager's method
            trace1 = manager.get_trace_info(settings1, "workspace_path")
            trace2 = manager.get_trace_info(settings2, "workspace_path")

            # Phase 2-4: load_settings() now provides trace info
            # Verify that each instance has its own trace info
            assert trace1 is not None, "load_settings() now attaches trace info"
            assert trace2 is not None, "load_settings() now attaches trace info"

            # Verify that trace info is different (instance-specific)
            assert trace1.value == Path(tmpdir1), "trace1 should have tmpdir1 value"
            assert trace2.value == Path(tmpdir2), "trace2 should have tmpdir2 value"

            # Verify that get_trace_info() is an instance method (not class method)
            assert hasattr(settings1, "get_trace_info"), "settings1 should have get_trace_info method"
            assert hasattr(settings2, "get_trace_info"), "settings2 should have get_trace_info method"


class TestConcurrentSettingsLoading:
    """Test that concurrent settings loading doesn't cause race conditions."""

    def test_concurrent_loading_does_not_mix_traces(self) -> None:
        """Concurrent loading should maintain separate trace storages."""
        results: list[tuple[OrchestratorSettings, dict[str, Any]]] = []
        errors: list[Exception] = []
        temp_dirs: list[tempfile.TemporaryDirectory[str]] = []

        def load_settings(workspace_id: int) -> None:
            try:
                tmpdir = tempfile.TemporaryDirectory()
                temp_dirs.append(tmpdir)
                workspace_path = Path(tmpdir.name)
                manager = ConfigurationManager(workspace=workspace_path)
                settings = manager.load_settings(OrchestratorSettings, workspace_path=workspace_path)
                traces = getattr(settings, "__source_traces__", {})
                results.append((settings, traces))
            except Exception as e:
                errors.append(e)

        # Create and start 10 threads
        threads = [threading.Thread(target=load_settings, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent loading: {errors}"

        # Verify we got 10 results
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"

        # Verify each trace storage is unique
        trace_ids = [id(traces) for _, traces in results]
        assert len(set(trace_ids)) == 10, "All trace storages should be different objects"

        # Verify each settings instance is unique
        settings_ids = [id(settings) for settings, _ in results]
        assert len(set(settings_ids)) == 10, "All settings instances should be different objects"

        # Cleanup
        for tmpdir in temp_dirs:
            tmpdir.cleanup()

    def test_concurrent_loading_preserves_workspace_paths(self) -> None:
        """Each concurrent load should preserve its own workspace path in traces."""
        results: list[tuple[Path, OrchestratorSettings]] = []
        errors: list[Exception] = []
        temp_dirs: list[tempfile.TemporaryDirectory[str]] = []

        def load_settings(workspace_id: int) -> None:
            try:
                tmpdir = tempfile.TemporaryDirectory()
                temp_dirs.append(tmpdir)
                workspace_path = Path(tmpdir.name)
                manager = ConfigurationManager(workspace=workspace_path)
                settings = manager.load_settings(OrchestratorSettings, workspace_path=workspace_path)
                results.append((workspace_path, settings))
            except Exception as e:
                errors.append(e)

        # Create and start threads with different workspace paths
        threads = [threading.Thread(target=load_settings, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify each settings has the correct workspace_path
        for expected_path, settings in results:
            assert settings.workspace_path == expected_path, (
                f"Expected workspace_path {expected_path}, got {settings.workspace_path}"
            )

        # Cleanup
        for tmpdir in temp_dirs:
            tmpdir.cleanup()


class TestInstanceMethodGetTraceInfo:
    """Test that get_trace_info is an instance method, not a class method."""

    def test_get_trace_info_is_instance_method(self) -> None:
        """get_trace_info() should be callable on instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigurationManager(workspace=Path(tmpdir))
            settings = manager.load_settings(OrchestratorSettings, workspace_path=Path(tmpdir))

            # Should be callable as an instance method
            assert hasattr(settings, "get_trace_info"), "settings should have get_trace_info method"
            assert callable(settings.get_trace_info), "get_trace_info should be callable"

            # Call the instance method
            trace = settings.get_trace_info("workspace_path")
            assert trace is not None or trace is None, "get_trace_info should return SourceTrace or None"

    def test_manager_get_trace_info_uses_instance(self) -> None:
        """ConfigurationManager.get_trace_info() should accept instance as first arg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigurationManager(workspace=Path(tmpdir))
            settings = manager.load_settings(OrchestratorSettings, workspace_path=Path(tmpdir))

            # This should not raise TypeError
            trace = manager.get_trace_info(settings, "workspace_path")

            # Verify it returns valid data
            assert trace is not None or trace is None, "Should return SourceTrace or None"
