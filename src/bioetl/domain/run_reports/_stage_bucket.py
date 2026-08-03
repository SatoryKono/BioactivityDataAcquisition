"""Private mutable accumulator cell for stage accounting."""

from __future__ import annotations


class _StageBucket:
    """Private mutable accumulator cell (not a domain value object)."""

    __slots__ = ("instrumented", "records_in", "records_out", "removals", "samples")

    def __init__(self) -> None:
        self.records_in = 0
        self.records_out = 0
        self.removals: dict[tuple[str, str], int] = {}
        self.samples: dict[tuple[str, str], list[str]] = {}
        self.instrumented = False
