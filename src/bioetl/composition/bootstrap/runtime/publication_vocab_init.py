"""Bootstrap initializer for publication controlled-vocabulary registries."""

from __future__ import annotations

from pathlib import Path

from bioetl.composition.factories.transformer_dependencies import (
    load_publication_controlled_vocabulary,
)
from bioetl.domain.mapping.publication_controlled_vocabulary import (
    initialize_publication_controlled_vocabulary as initialize_registry,
)


def initialize_publication_controlled_vocabulary(configs_root: Path) -> None:
    """Load publication controlled vocabulary and initialize the domain registry."""

    initialize_registry(load_publication_controlled_vocabulary(configs_root))
