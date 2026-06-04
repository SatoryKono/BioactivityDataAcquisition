"""Tests for contract_registry facade exports."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.contract_registry import (
    ContractRegistry,
    ContractRegistryEntry,
    RegistryValidationError,
    RegistryValidationIssue,
    RegistryValidationResult,
    RegistryValidationSeverity,
)

pytestmark = pytest.mark.unit


def test_contract_registry_exports() -> None:
    """Test that contract_registry module exports expected classes."""
    assert ContractRegistry is not None
    assert ContractRegistryEntry is not None
    assert RegistryValidationError is not None
    assert RegistryValidationIssue is not None
    assert RegistryValidationResult is not None
    assert RegistryValidationSeverity is not None