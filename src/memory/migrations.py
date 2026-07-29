"""Explicit, rollback-safe schema migrations for JSON memory records."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.storage import atomic_write_bytes, atomic_write_json, content_digest

MigrationTransform = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationError(RuntimeError):
    """Raised when a migration path or write cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class MigrationStep:
    """One explicit adjacent schema-version transformation."""

    from_version: int
    to_version: int
    transform: MigrationTransform

    def __post_init__(self) -> None:
        if self.to_version != self.from_version + 1:
            raise ValueError("migration steps must advance exactly one version")


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Auditable result of a dry-run or applied file migration."""

    path: Path
    from_version: int
    to_version: int
    applied: bool
    changed: bool
    original_digest: str
    migrated_digest: str
    preserved_original: Path | None


def _legacy_to_v1(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(payload)
    migrated["schema_version"] = 1
    return migrated


DEFAULT_MIGRATIONS: Mapping[int, MigrationStep] = {
    0: MigrationStep(0, 1, _legacy_to_v1),
}


def migrate_payload(
    payload: dict[str, Any],
    *,
    target_version: int,
    migrations: Mapping[int, MigrationStep] = DEFAULT_MIGRATIONS,
) -> dict[str, Any]:
    """Return a migrated copy without mutating the caller's payload."""
    migrated = copy.deepcopy(payload)
    current_version = migrated.get("schema_version", 0)
    if not isinstance(current_version, int) or isinstance(current_version, bool):
        raise MigrationError("schema_version must be an integer")
    if current_version > target_version:
        raise MigrationError("downgrade migrations are not supported")
    while current_version < target_version:
        step = migrations.get(current_version)
        if step is None or step.from_version != current_version:
            raise MigrationError(
                f"no migration step from schema version {current_version}"
            )
        migrated = step.transform(copy.deepcopy(migrated))
        if migrated.get("schema_version") != step.to_version:
            raise MigrationError(
                f"migration {step.from_version}->{step.to_version} "
                "did not set the target schema_version"
            )
        current_version = step.to_version
    return migrated


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def migrate_json_file(
    path: Path,
    *,
    target_version: int,
    apply: bool = False,
    migrations: Mapping[int, MigrationStep] = DEFAULT_MIGRATIONS,
) -> MigrationResult:
    """Dry-run or apply a migration while retaining the original bytes."""
    original_bytes = path.read_bytes()
    original_digest = content_digest(original_bytes)
    payload = json.loads(original_bytes)
    if not isinstance(payload, dict):
        raise MigrationError("memory record must be a JSON object")
    from_version = payload.get("schema_version", 0)
    if not isinstance(from_version, int) or isinstance(from_version, bool):
        raise MigrationError("schema_version must be an integer")
    migrated = migrate_payload(
        payload,
        target_version=target_version,
        migrations=migrations,
    )
    migrated_bytes = _canonical_json_bytes(migrated)
    migrated_digest = content_digest(migrated_bytes)
    changed = migrated_bytes != original_bytes
    preserved_original: Path | None = None
    if apply and changed:
        preserved_original = path.with_name(
            f"{path.name}.v{from_version}.{original_digest[:12]}.bak"
        )
        if preserved_original.exists():
            if preserved_original.read_bytes() != original_bytes:
                raise MigrationError(
                    f"preserved original conflicts with current source: "
                    f"{preserved_original}"
                )
        else:
            atomic_write_bytes(preserved_original, original_bytes)
        try:
            atomic_write_json(
                path,
                migrated,
                expected_digest=original_digest,
            )
        except Exception:
            atomic_write_bytes(path, original_bytes)
            raise
    return MigrationResult(
        path=path,
        from_version=from_version,
        to_version=target_version,
        applied=apply and changed,
        changed=changed,
        original_digest=original_digest,
        migrated_digest=migrated_digest,
        preserved_original=preserved_original,
    )
