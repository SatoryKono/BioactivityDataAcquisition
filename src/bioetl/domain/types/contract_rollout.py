"""Pure runtime value objects for contract rollout semantics."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ContractRolloutPolicy", "VersionedContractTarget"]

_ALLOWED_ROLLOUT_MODES = frozenset(
    {"single", "dual_read", "dual_write", "dual_read_write"}
)


@dataclass(frozen=True, slots=True)
class VersionedContractTarget:
    """Semantic target representing one logical contract version."""

    logical_name: str
    contract_ref: str
    contract_version: str
    is_active: bool = False


@dataclass(frozen=True, slots=True)
class ContractRolloutPolicy:
    """Pure rollout policy detached from storage/path concerns."""

    contract_ref: str
    active_version: str
    mode: str = "single"
    read_order: tuple[str, ...] = ()
    write_versions: tuple[str, ...] = ()
    affects_hash: bool = False

    def __post_init__(self) -> None:
        """Validate core rollout invariants."""
        if not self.contract_ref.strip():
            raise ValueError("contract_ref cannot be empty")
        if not self.active_version.strip():
            raise ValueError("active_version cannot be empty")
        if self.mode not in _ALLOWED_ROLLOUT_MODES:
            allowed = ", ".join(sorted(_ALLOWED_ROLLOUT_MODES))
            raise ValueError(f"mode must be one of {allowed}, got {self.mode!r}")
        if self.active_version not in self.read_order:
            raise ValueError("active_version must be present in read_order")
        if self.active_version not in self.write_versions:
            raise ValueError("active_version must be present in write_versions")
        if len(self.read_order) != len(set(self.read_order)):
            raise ValueError("read_order must not contain duplicate versions")
        if len(self.write_versions) != len(set(self.write_versions)):
            raise ValueError("write_versions must not contain duplicate versions")
        if self.mode == "single":
            if self.read_order != (self.active_version,):
                raise ValueError(
                    "single mode requires read_order == (active_version,)"
                )
            if self.write_versions != (self.active_version,):
                raise ValueError(
                    "single mode requires write_versions == (active_version,)"
                )

    def read_targets(self, logical_name: str) -> tuple[VersionedContractTarget, ...]:
        """Return semantic read targets in fallback order."""
        return tuple(
            VersionedContractTarget(
                logical_name=logical_name,
                contract_ref=self.contract_ref,
                contract_version=version,
                is_active=version == self.active_version,
            )
            for version in self.read_order
        )

    def write_targets(self, logical_name: str) -> tuple[VersionedContractTarget, ...]:
        """Return semantic write targets in required write order."""
        return tuple(
            VersionedContractTarget(
                logical_name=logical_name,
                contract_ref=self.contract_ref,
                contract_version=version,
                is_active=version == self.active_version,
            )
            for version in self.write_versions
        )
