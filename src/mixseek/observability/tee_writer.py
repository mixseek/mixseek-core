"""TeeWriter for multi-destination output (Article 9 compliant).

This module provides a TextIO-like writer that simultaneously writes
to multiple output destinations (console, file, etc.).

Used by:
- setup_logfire() for Logfire span console/file output
- setup_logging() for standard logging output
"""

from typing import TextIO


class TeeWriter:
    """Write to multiple output destinations simultaneously.

    This class implements a TextIO-like interface that forwards write operations
    to all configured output destinations. It enables simultaneous output to
    console (stderr) and file, supporting the dual-path logging architecture.

    Attributes:
        _writers: List of TextIO objects to write to

    Example:
        >>> import sys
        >>> from io import StringIO
        >>> log_file = StringIO()
        >>> tee = TeeWriter([sys.stderr, log_file])
        >>> tee.write("Message to both destinations")
        >>> tee.flush()
    """

    def __init__(self, writers: list[TextIO]) -> None:
        """Initialize TeeWriter with output destinations.

        Args:
            writers: List of TextIO objects to write to simultaneously.
                Must contain at least one writer.

        Raises:
            ValueError: If writers list is empty

        Note:
            Following Article 9, we explicitly validate input rather than
            silently accepting empty configurations.
        """
        if not writers:
            raise ValueError("TeeWriter requires at least one writer destination")
        self._writers = writers

    def write(self, data: str) -> int:
        """Write data to all output destinations.

        Args:
            data: String data to write

        Returns:
            Number of characters written (length of data)
        """
        for writer in self._writers:
            writer.write(data)
        return len(data)

    def flush(self) -> None:
        """Flush all output destinations.

        Ensures all buffered data is written to underlying streams.
        """
        for writer in self._writers:
            writer.flush()
