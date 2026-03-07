"""Bootstrap initializer for publication type classification data.

Loads classification data from the JSON asset via infrastructure loader
and initializes the domain classification module.
"""

from __future__ import annotations

from pathlib import Path


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Load classification data from JSON and initialize the domain module.

    Must be called once before any pipeline transformer uses
    ``classify_publication_type()``. Idempotent — repeated calls reload the
    data but do not cause errors.

    Args:
        configs_root: Root directory of the project configs tree (e.g., Path('configs')).
            The loader resolves the JSON asset path relative to this directory.
    """
    from bioetl.domain.mapping.publication_type_classification import (
        initialize_classification,
    )
    from bioetl.infrastructure.config.publication_type_classification_loader import (
        PublicationTypeClassificationLoader,
    )

    loader = PublicationTypeClassificationLoader(configs_root)
    data = loader.load()
    initialize_classification(data)
