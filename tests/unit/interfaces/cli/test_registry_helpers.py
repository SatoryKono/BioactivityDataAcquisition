"""Tests for CLI registry helper compatibility wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.cli.registry_helpers import build_cli_registry


@pytest.mark.unit
def test_create_registry_delegates_to_composition_registry() -> None:
    """CLI registry helper should lazily delegate registry creation."""
    import bioetl.interfaces.cli.registry_helpers as registry_helpers

    registry = MagicMock()

    with patch(
        "bioetl.composition.registry.create_registry",
        return_value=registry,
    ) as mock_create_registry:
        result = registry_helpers.create_registry()

    assert result is registry
    mock_create_registry.assert_called_once_with()


@pytest.mark.unit
def test_register_all_pipelines_delegates_to_composition_registry() -> None:
    """CLI registry helper should lazily delegate pipeline registration."""
    import bioetl.interfaces.cli.registry_helpers as registry_helpers

    registry = MagicMock()

    with patch(
        "bioetl.composition.factories.pipeline.registry.register_all_pipelines",
    ) as mock_register_all_pipelines:
        registry_helpers.register_all_pipelines(registry=registry)

    mock_register_all_pipelines.assert_called_once_with(registry=registry)


@pytest.mark.unit
def test_build_cli_registry_uses_local_patch_points() -> None:
    """Registry builder should keep using module-level collaborator seams."""
    registry = MagicMock()

    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.create_registry",
            return_value=registry,
        ) as mock_create_registry,
        patch(
            "bioetl.interfaces.cli.registry_helpers.register_all_pipelines",
        ) as mock_register_all_pipelines,
    ):
        result = build_cli_registry()

    assert result is registry
    mock_create_registry.assert_called_once_with()
    mock_register_all_pipelines.assert_called_once_with(registry=registry)
