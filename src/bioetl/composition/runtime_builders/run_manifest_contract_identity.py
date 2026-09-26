"""Composition facade for contract-identity resolution (#11250)."""

from __future__ import annotations

from bioetl.composition.runtime_builders._run_manifest_identity_ref_values import (
    build_contract_identity_field_values,
)
from bioetl.infrastructure.config.contract_identity_resolution import (
    RunManifestContractIdentity,
    ensure_complete_contract_identity,
    resolve_contract_identity,
)

__all__ = [
    "RunManifestContractIdentity",
    "build_contract_identity_field_values",
    "ensure_complete_contract_identity",
    "resolve_contract_identity",
]
