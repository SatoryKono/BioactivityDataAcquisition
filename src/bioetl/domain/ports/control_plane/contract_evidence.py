"""Port for immutable manifest contract-evidence sidecars."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

__all__ = ["ContractEvidenceRecorderPort"]


@runtime_checkable
class ContractEvidenceRecorderPort(Protocol):
    """Persist one forensic contract-evidence sidecar per manifest."""

    def record(self, manifest_id: str, evidence: Mapping[str, object]) -> None:
        """Write one deterministic sidecar for manifest_id."""
        ...
