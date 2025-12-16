"""Protocol definitions for pipeline callbacks.

These protocols define the interfaces for transform and filter callbacks
used by the pipeline executor and record processor.
"""

from collections.abc import Awaitable
from typing import Any, Protocol

from bioetl.domain.context import PipelineContext


class TransformCallback(Protocol):
    """Protocol for Bronze to Silver transformation callback."""

    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Awaitable[dict[str, Any] | None]: ...


class GoldFilterCallback(Protocol):
    """Protocol for Gold layer filtering callback."""

    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool: ...
