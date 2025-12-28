"""OpenAlex pipeline components.

Provides transformers for OpenAlex entities (works, authors, etc.).
"""

from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexWorkTransformer,
)

__all__ = [
    "OpenAlexWorkTransformer",
]
