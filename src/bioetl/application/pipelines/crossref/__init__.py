"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from __future__ import annotations

from bioetl.application.pipelines.crossref import extractors
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

__all__ = ["CrossRefPublicationTransformer", *extractors.__all__]


def __getattr__(name: str) -> object:
    if name == "CrossRefPublicationTransformer":
        return CrossRefPublicationTransformer
    return getattr(extractors, name)


def __dir__() -> list[str]:
    return sorted(__all__)
