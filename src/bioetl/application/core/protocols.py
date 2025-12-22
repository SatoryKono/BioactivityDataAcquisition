"""
Callback protocols for the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.context import PipelineContext


class TransformCallback(Protocol):
    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Awaitable[dict[str, Any] | None]: ...


class GoldFilterCallback(Protocol):
    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool: ...
