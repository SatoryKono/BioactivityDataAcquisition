"""Bootstrap helpers for config-backed normalization policy overrides."""

from __future__ import annotations

from pathlib import Path


def initialize_chembl_policy_registry(configs_root: Path) -> None:
    """Load ChEMBL policy registries from configs and inject them into domain state."""
    from bioetl.domain.normalization.profiles._chembl_policy_registry import (
        initialize_chembl_policy_registry as initialize_domain_chembl_policy_registry,
    )
    from bioetl.infrastructure.config.chembl_policy_registry_loader import (
        ChemblPolicyRegistryLoader,
    )

    loader = ChemblPolicyRegistryLoader(configs_root)
    initialize_domain_chembl_policy_registry(loader.load())
