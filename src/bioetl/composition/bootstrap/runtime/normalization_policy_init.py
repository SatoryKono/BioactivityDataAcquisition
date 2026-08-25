"""Bootstrap helpers for config-backed normalization policy overrides."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from bioetl.domain.normalization.profiles.chembl_policy_registry_data import (
    ChemblPolicyRegistryData,
)

from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
)


@cache
def _load_chembl_policy_registry_data(
    configs_root_key: str,
) -> ChemblPolicyRegistryData:
    """Load immutable ChEMBL policy registry data once per configs root key."""

    loader = ChemblPolicyRegistryLoader(Path(configs_root_key))
    return loader.load()


def initialize_chembl_policy_registry(configs_root: Path) -> None:
    """Load ChEMBL policy registries from configs and inject them into domain state.

    The config payload is cached per ``configs_root`` within the current process
    to avoid repeated filesystem scans during sequential runtime bootstraps.
    """
    from bioetl.domain.normalization.profiles.chembl_policy_registry import (
        initialize_chembl_policy_registry as initialize_domain_chembl_policy_registry,
    )

    initialize_domain_chembl_policy_registry(
        _load_chembl_policy_registry_data(str(configs_root))
    )
