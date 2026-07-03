"""Pure runtime value objects for contract rollout semantics."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ContractRolloutPolicy", "VersionedContractTarget"]

_ALLOWED_ROLLOUT_MODES = frozenset(
    {"single", "dual_read", "dual_write", "dual_read_write"}
)


def _require_non_empty(value: str, field_name: str) -> None:
    """Validate that a rollout field is present."""
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _require_member(
    version: str,
    versions: tuple[str, ...],
    collection_name: str,
) -> None:
    """Validate that the active version appears in a version collection."""
    if version not in versions:
        raise ValueError(f"active_version must be present in {collection_name}")


def _require_unique(versions: tuple[str, ...], collection_name: str) -> None:
    """Validate that rollout versions do not contain duplicates."""
    if len(versions) != len(set(versions)):
        raise ValueError(f"{collection_name} must not contain duplicate versions")


def _validate_rollout_mode(mode: str) -> None:
    """Validate that the configured rollout mode is supported."""
    if mode in _ALLOWED_ROLLOUT_MODES:
        return
    allowed = ", ".join(sorted(_ALLOWED_ROLLOUT_MODES))
    raise ValueError(f"mode must be one of {allowed}, got {mode!r}")


def _validate_single_mode(
    mode: str,
    active_version: str,
    read_order: tuple[str, ...],
    write_versions: tuple[str, ...],
) -> None:
    """Validate the stricter invariants for single-version rollout mode."""
    if mode != "single":
        return
    expected = (active_version,)
    if read_order != expected:
        raise ValueError("single mode requires read_order == (active_version,)")
    if write_versions != expected:
        raise ValueError("single mode requires write_versions == (active_version,)")


def _build_version_targets(
    *,
    logical_name: str,
    contract_ref: str,
    active_version: str,
    versions: tuple[str, ...],
) -> tuple[VersionedContractTarget, ...]:
    """Build semantic contract targets for read or write execution."""
    return tuple(
        VersionedContractTarget(
            logical_name=logical_name,
            contract_ref=contract_ref,
            contract_version=version,
            is_active=version == active_version,
        )
        for version in versions
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
        _require_non_empty(self.contract_ref, "contract_ref")
        _require_non_empty(self.active_version, "active_version")
        _validate_rollout_mode(self.mode)
        _require_member(self.active_version, self.read_order, "read_order")
        _require_member(self.active_version, self.write_versions, "write_versions")
        _require_unique(self.read_order, "read_order")
        _require_unique(self.write_versions, "write_versions")
        _validate_single_mode(
            self.mode,
            self.active_version,
            self.read_order,
            self.write_versions,
        )

    def read_targets(self, logical_name: str) -> tuple[VersionedContractTarget, ...]:
        """Return semantic read targets in fallback order."""
        return _build_version_targets(
            logical_name=logical_name,
            contract_ref=self.contract_ref,
            active_version=self.active_version,
            versions=self.read_order,
        )

    def write_targets(self, logical_name: str) -> tuple[VersionedContractTarget, ...]:
        """Return semantic write targets in required write order."""
        return _build_version_targets(
            logical_name=logical_name,
            contract_ref=self.contract_ref,
            active_version=self.active_version,
            versions=self.write_versions,
        )
