"""Pure runtime value objects for Gold schema routing by contract version."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GoldSchemaPolicyByVersion", "GoldSchemaVersionPolicy"]


def _require_non_empty(value: str, field_name: str) -> None:
    """Validate that a schema-routing field is present."""
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _require_unique(versions: tuple[str, ...], collection_name: str) -> None:
    """Validate that schema-routing versions do not contain duplicates."""
    if len(versions) != len(set(versions)):
        raise ValueError(f"{collection_name} must not contain duplicate versions")


def _require_member(
    version: str,
    versions: tuple[str, ...],
    collection_name: str,
) -> None:
    """Validate that the active version appears in the schema collection."""
    if version not in versions:
        raise ValueError(f"active_version must be present in {collection_name}")


@dataclass(frozen=True, slots=True)
class GoldSchemaVersionPolicy:
    """One Gold schema binding for a specific contract version."""

    version: str
    schema: object

    def __post_init__(self) -> None:
        """Validate required version and schema values."""
        _require_non_empty(self.version, "version")
        if self.schema is None:
            raise ValueError("schema cannot be None")


@dataclass(frozen=True, slots=True)
class GoldSchemaPolicyByVersion:
    """Typed container for active and shadow Gold schema bindings."""

    active_version: str
    policies: tuple[GoldSchemaVersionPolicy, ...]

    def __post_init__(self) -> None:
        """Validate version uniqueness and active-version presence."""
        _require_non_empty(self.active_version, "active_version")
        versions = tuple(policy.version for policy in self.policies)
        _require_unique(versions, "policies")
        _require_member(self.active_version, versions, "policies")

    def for_version(self, version: str) -> object | None:
        """Return the schema bound to one contract version when present."""
        return next(
            (policy.schema for policy in self.policies if policy.version == version),
            None,
        )

    @property
    def active_schema(self) -> object:
        """Return the schema for the active contract version."""
        schema = self.for_version(self.active_version)
        if schema is None:  # pragma: no cover - guarded by __post_init__
            raise ValueError("active_version must be present in policies")
        return schema

    @property
    def versions(self) -> tuple[str, ...]:
        """Return the ordered schema versions."""
        return tuple(policy.version for policy in self.policies)

    @property
    def is_multi_version(self) -> bool:
        """Whether the routing policy carries multiple schema versions."""
        return len(self.policies) > 1
