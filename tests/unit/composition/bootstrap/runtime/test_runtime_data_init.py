"""Tests for cached runtime bootstrap data initialization helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
    initialize_chembl_policy_registry,
)


@pytest.mark.unit
def test_initialize_chembl_policy_registry_caches_loader_per_configs_root() -> None:
    """Repeated runtime bootstraps should reuse the same loaded policy payload."""
    initialize_chembl_policy_registry.__globals__[
        "_load_chembl_policy_registry_data"
    ].cache_clear()
    data = MagicMock()

    with (
        patch(
            "bioetl.infrastructure.config.chembl_policy_registry_loader.ChemblPolicyRegistryLoader.load",
            return_value=data,
        ) as mock_load,
        patch(
            "bioetl.domain.normalization.profiles.chembl_policy_registry.initialize_chembl_policy_registry"
        ) as mock_initialize_domain,
    ):
        initialize_chembl_policy_registry(Path("configs"))
        initialize_chembl_policy_registry(Path("configs"))

    mock_load.assert_called_once_with()
    assert mock_initialize_domain.call_count == 2
    mock_initialize_domain.assert_called_with(data)


@pytest.mark.unit
def test_initialize_publication_type_classification_caches_loader_per_configs_root() -> (
    None
):
    """Repeated runtime bootstraps should reuse the same classification payload."""
    initialize_publication_type_classification.__globals__[
        "_load_publication_type_classification_data"
    ].cache_clear()
    data = MagicMock()

    with (
        patch(
            "bioetl.infrastructure.config.publication_type_classification_loader.PublicationTypeClassificationLoader.load",
            return_value=data,
        ) as mock_load,
        patch(
            "bioetl.domain.mapping.publication_type_classification.initialize_classification"
        ) as mock_initialize_domain,
    ):
        initialize_publication_type_classification(Path("configs"))
        initialize_publication_type_classification(Path("configs"))

    mock_load.assert_called_once_with()
    assert mock_initialize_domain.call_count == 2
    mock_initialize_domain.assert_called_with(data)


@pytest.mark.unit
def test_runtime_data_caches_are_scoped_by_configs_root() -> None:
    """Different config roots should keep independent cached payloads."""
    initialize_chembl_policy_registry.__globals__[
        "_load_chembl_policy_registry_data"
    ].cache_clear()
    initialize_publication_type_classification.__globals__[
        "_load_publication_type_classification_data"
    ].cache_clear()

    with (
        patch(
            "bioetl.infrastructure.config.chembl_policy_registry_loader.ChemblPolicyRegistryLoader.load",
            side_effect=[MagicMock(name="chembl-a"), MagicMock(name="chembl-b")],
        ) as mock_chembl_load,
        patch(
            "bioetl.infrastructure.config.publication_type_classification_loader.PublicationTypeClassificationLoader.load",
            side_effect=[
                MagicMock(name="classification-a"),
                MagicMock(name="classification-b"),
            ],
        ) as mock_classification_load,
        patch(
            "bioetl.domain.normalization.profiles.chembl_policy_registry.initialize_chembl_policy_registry"
        ),
        patch(
            "bioetl.domain.mapping.publication_type_classification.initialize_classification"
        ),
    ):
        initialize_chembl_policy_registry(Path("configs"))
        initialize_chembl_policy_registry(Path("/tmp/other-configs"))
        initialize_publication_type_classification(Path("configs"))
        initialize_publication_type_classification(Path("/tmp/other-configs"))

    assert mock_chembl_load.call_count == 2
    assert mock_classification_load.call_count == 2
