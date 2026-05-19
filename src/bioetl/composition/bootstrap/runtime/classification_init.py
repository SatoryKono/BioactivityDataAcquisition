"""Bootstrap initializer for publication type classification data.

Loads classification data from the JSON asset via infrastructure loader
and initializes the domain classification module.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bioetl.domain.mapping.classification_data import ClassificationData


@lru_cache(maxsize=None)
def _load_publication_type_classification_data(
    configs_root_key: str,
) -> ClassificationData:
    """Load classification data once per configs root key."""
    from bioetl.infrastructure.config.publication_type_classification_loader import (
        PublicationTypeClassificationLoader,
    )

    loader = PublicationTypeClassificationLoader(Path(configs_root_key))
    return loader.load()


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Load classification data from JSON and initialize the domain module.

    Must be called once before any pipeline transformer uses
    ``classify_publication_type()``. Idempotent — repeated calls re-apply the
    same cached data and do not cause errors.

    Args:
        configs_root: Root directory of the project configs tree (e.g., Path('configs')).
            The loader resolves the JSON asset path relative to this directory.
    """
    from bioetl.domain.mapping.publication_type_classification import (
        initialize_classification,
    )

    initialize_classification(
        _load_publication_type_classification_data(str(configs_root))
    )
