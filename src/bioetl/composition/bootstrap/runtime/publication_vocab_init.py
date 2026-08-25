"""Bootstrap initializer for publication controlled-vocabulary registries."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
)

from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)


@cache
def _load_publication_controlled_vocabulary_data(
    configs_root_key: str,
) -> PublicationControlledVocabularyRegistry:
    """Load publication controlled vocabulary once per configs root key."""

    loader = PublicationControlledVocabularyLoader(Path(configs_root_key))
    return loader.load()


def initialize_publication_controlled_vocabulary(configs_root: Path) -> None:
    """Load publication controlled vocabulary and initialize the domain registry."""
    from bioetl.domain.mapping.publication_controlled_vocabulary import (
        initialize_publication_controlled_vocabulary as initialize_registry,
    )

    initialize_registry(_load_publication_controlled_vocabulary_data(str(configs_root)))
