"""Explicit runtime Gold disablement, distinct from contract rejection."""

from __future__ import annotations

from bioetl.domain.context import PipelineContext
from bioetl.domain.types import JsonDict


class DisabledGoldFilterService:
    """Signal that Gold is intentionally omitted for this pipeline phase."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> bool:
        return False
