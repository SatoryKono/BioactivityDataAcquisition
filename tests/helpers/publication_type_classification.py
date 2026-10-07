"""Explicit test helper for publication type classification initialization."""

from __future__ import annotations

from pathlib import Path


def bind_installed_classification_data(func):  # type: ignore[no-untyped-def]
    """Pass the installed taxonomy into tests that predate the explicit argument."""

    def wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
        if "data" not in kwargs:
            from bioetl.domain.mapping.publication_type_classification import (
                classification_install,
            )

            if classification_install.data is None:
                initialize_test_publication_type_classification()
            kwargs["data"] = classification_install.data
        return func(*args, **kwargs)

    return wrapped


def initialize_test_publication_type_classification() -> None:
    """Load the published classification asset into the domain lookup tables."""
    from bioetl.domain.mapping.publication_type_classification import (
        initialize_classification,
    )
    from bioetl.infrastructure.config.publication_type_classification_loader import (
        PublicationTypeClassificationLoader,
    )

    repo_root = Path(__file__).resolve().parents[2]
    data = PublicationTypeClassificationLoader(repo_root / "configs").load()
    initialize_classification(data)
