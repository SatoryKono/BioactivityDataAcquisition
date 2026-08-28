"""Тесты policy validation реестра публикационных сущностей."""

from __future__ import annotations

import pytest

from bioetl.domain.registry.publication_data import (
    get_publication_entity_type_validation_error,
)


@pytest.mark.parametrize(
    ("entity_type", "provider"),
    [
        ("publication", "chembl"),
        ("publication_similarity", "chembl"),
        ("publication_term", "chembl"),
        ("document", "pubchem"),
        ("unknown_publication_type", "chembl"),
    ],
)
def test_publication_entity_type_validation_accepts_supported_or_non_chembl_inputs(
    entity_type: str,
    provider: str,
) -> None:
    """Разрешаются канонические типы, внешние providers и неизвестные значения."""
    assert get_publication_entity_type_validation_error(entity_type, provider) is None


def test_publication_entity_type_validation_reports_historical_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Исторический alias получает детерминированную подсказку канонического имени."""
    from bioetl.domain.registry import publication_data

    monkeypatch.setattr(
        publication_data,
        "LEGACY_PUBLICATION_ALIASES",
        frozenset({"document"}),
    )

    error = publication_data.get_publication_entity_type_validation_error(
        "document",
        "chembl",
    )

    assert error is not None
    assert "publication" in error
    assert "document" in error
