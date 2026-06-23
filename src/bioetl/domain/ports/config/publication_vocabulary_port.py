"""Port for loading publication controlled-vocabulary registries."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
)

__all__ = ["PublicationVocabularyPort"]


@runtime_checkable
class PublicationVocabularyPort(Protocol):
    """Load provider-facing publication controlled-vocabulary registries."""

    def load(self) -> PublicationControlledVocabularyRegistry:
        """Load the normalized publication controlled-vocabulary registry."""
        ...
