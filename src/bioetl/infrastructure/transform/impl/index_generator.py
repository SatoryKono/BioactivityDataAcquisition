"""Infrastructure implementation of IndexGenerator."""

from __future__ import annotations

from bioetl.domain.transform.contracts import IndexGeneratorABC


class SequentialIndexGenerator(IndexGeneratorABC):
    """Sequential index generator.

    Stateful: maintains counter value between calls.
    Used for assigning unique indices to data rows.
    """

    def __init__(self, start: int = 0) -> None:
        """Initialize generator.

        Args:
            start: Initial counter value (default 0).
        """
        self._start = start
        self._counter = start

    def next_index(self) -> int:
        """Return next index and increment counter."""
        idx = self._counter
        self._counter += 1
        return idx

    def reset(self) -> None:
        """Reset counter to initial state."""
        self._counter = self._start

    def generate_range(self, count: int) -> list[int]:
        """Generate index range for batch operations.

        Args:
            count: Number of indices to generate.

        Returns:
            List of sequential indices.
        """
        start = self._counter
        self._counter += count
        return list(range(start, start + count))


__all__ = ["SequentialIndexGenerator"]
