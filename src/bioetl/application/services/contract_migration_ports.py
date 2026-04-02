"""Port contracts for contract migration planning workflows."""

from __future__ import annotations

from typing import Protocol

from bioetl.application.services.config_service import PipelineInfo

__all__ = [
    "ContractPolicyLoaderPort",
    "ContractPolicyPort",
    "PipelineInfoLoaderPort",
    "RegistryEntriesLoaderPort",
]


class ContractPolicyPort(Protocol):
    """Minimal contract policy surface required by migration planning."""

    @property
    def contract_ref(self) -> str:
        """Return the canonical contract reference."""
        ...

    @property
    def active_version(self) -> str:
        """Return the currently active contract version."""
        ...

    @property
    def rollout_mode(self) -> str:
        """Return the rollout mode."""
        ...

    @property
    def read_order(self) -> list[str]:
        """Return ordered read versions."""
        ...

    @property
    def write_versions(self) -> list[str]:
        """Return ordered write target versions."""
        ...

    @property
    def affects_hash(self) -> bool:
        """Return whether the rollout changes record hash semantics."""
        ...


class PipelineInfoLoaderPort(Protocol):
    """Callable contract for pipeline identity resolution."""

    def __call__(self, pipeline_name: str) -> PipelineInfo:
        """Resolve provider/entity metadata for one pipeline."""
        ...


class ContractPolicyLoaderPort(Protocol):
    """Callable contract for loading contract policy by provider/entity."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyPort:
        """Load the typed contract policy."""
        ...


class RegistryEntriesLoaderPort(Protocol):
    """Callable contract for retrieving raw registry entries."""

    def __call__(self) -> dict[str, dict[str, object]]:
        """Load registry entries keyed by contract ref."""
        ...
