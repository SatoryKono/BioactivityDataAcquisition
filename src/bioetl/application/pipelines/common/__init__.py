"""Common pipeline components.

This package contains shared base classes for publication transformers
that reduce code duplication across providers.

Main Components:
- BasePublicationTransformer: Template Method base for publication transformers
"""

from __future__ import annotations

from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)

__all__ = [
    "BasePublicationTransformer",
]
