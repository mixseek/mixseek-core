"""Tests for TeeWriter multi-destination output utility.

This module tests the TeeWriter class that enables simultaneous writing
to multiple output destinations (console, file, etc.).
"""

from io import StringIO

import pytest

from mixseek.observability.tee_writer import TeeWriter


class TestTeeWriterSingleOutput:
    """Test TeeWriter with a single output destination."""

    def test_single_writer_write(self) -> None:
        """Test writing to a single output destination."""
        output = StringIO()
        tee = TeeWriter([output])

        tee.write("Hello, World!")

        assert output.getvalue() == "Hello, World!"

    def test_single_writer_write_returns_length(self) -> None:
        """Test that write returns the number of characters written."""
        output = StringIO()
        tee = TeeWriter([output])

        result = tee.write("Hello")

        assert result == 5

    def test_single_writer_flush(self) -> None:
        """Test flushing a single output destination."""
        output = StringIO()
        tee = TeeWriter([output])

        tee.write("Test")
        tee.flush()

        # StringIO.flush() should not raise, just verify it works
        assert output.getvalue() == "Test"


class TestTeeWriterMultipleOutputs:
    """Test TeeWriter with multiple output destinations."""

    def test_two_writers(self) -> None:
        """Test writing to two output destinations simultaneously."""
        output1 = StringIO()
        output2 = StringIO()
        tee = TeeWriter([output1, output2])

        tee.write("Dual output")

        assert output1.getvalue() == "Dual output"
        assert output2.getvalue() == "Dual output"

    def test_three_writers(self) -> None:
        """Test writing to three output destinations simultaneously."""
        output1 = StringIO()
        output2 = StringIO()
        output3 = StringIO()
        tee = TeeWriter([output1, output2, output3])

        tee.write("Triple output")

        assert output1.getvalue() == "Triple output"
        assert output2.getvalue() == "Triple output"
        assert output3.getvalue() == "Triple output"

    def test_multiple_writes(self) -> None:
        """Test multiple sequential writes to multiple outputs."""
        output1 = StringIO()
        output2 = StringIO()
        tee = TeeWriter([output1, output2])

        tee.write("Line 1\n")
        tee.write("Line 2\n")

        expected = "Line 1\nLine 2\n"
        assert output1.getvalue() == expected
        assert output2.getvalue() == expected

    def test_flush_all_writers(self) -> None:
        """Test that flush() flushes all output destinations."""
        output1 = StringIO()
        output2 = StringIO()
        tee = TeeWriter([output1, output2])

        tee.write("Flush test")
        tee.flush()

        # Both should have the data
        assert output1.getvalue() == "Flush test"
        assert output2.getvalue() == "Flush test"


class TestTeeWriterEdgeCases:
    """Test TeeWriter edge cases and error handling."""

    def test_empty_writers_list_raises_error(self) -> None:
        """Test that empty writers list raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TeeWriter([])

        assert "at least one writer" in str(exc_info.value).lower()

    def test_write_empty_string(self) -> None:
        """Test writing an empty string."""
        output = StringIO()
        tee = TeeWriter([output])

        result = tee.write("")

        assert result == 0
        assert output.getvalue() == ""

    def test_write_unicode(self) -> None:
        """Test writing unicode characters."""
        output = StringIO()
        tee = TeeWriter([output])

        tee.write("日本語テスト 🚀")

        assert output.getvalue() == "日本語テスト 🚀"

    def test_write_newlines(self) -> None:
        """Test writing strings with various newline characters."""
        output = StringIO()
        tee = TeeWriter([output])

        tee.write("Line1\nLine2\r\nLine3")

        assert output.getvalue() == "Line1\nLine2\r\nLine3"


class TestTeeWriterInterface:
    """Test TeeWriter implements TextIO-like interface."""

    def test_has_write_method(self) -> None:
        """Test that TeeWriter has write method."""
        output = StringIO()
        tee = TeeWriter([output])

        assert hasattr(tee, "write")
        assert callable(tee.write)

    def test_has_flush_method(self) -> None:
        """Test that TeeWriter has flush method."""
        output = StringIO()
        tee = TeeWriter([output])

        assert hasattr(tee, "flush")
        assert callable(tee.flush)
