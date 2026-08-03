"""Utility for loading enum configurations from YAML files."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

__all__ = [
    "EnumLoaderProtocol",
    "get_chembl_enum",
    "get_chembl_enum_set",
    "get_enum_config",
    "get_enum_set",
    "get_provider_enum",
    "get_provider_enum_config",
    "load_chembl_enums",
    "load_provider_enums",
]


class EnumLoaderProtocol(Protocol):
    """Port for loading enum configurations. Implemented by infrastructure layer."""

    def load_provider_enums(
        self,
        provider: str,
    ) -> dict[str, object]:
        """Load enum configurations for one provider."""
        ...

    def load_chembl_enums(
        self,
    ) -> dict[str, object]:  # Any: Enum data structure from YAML
        """Load ChEMBL enum configurations.

        Returns:
            Dictionary containing all enum configurations
        """
        ...


def _normalize_coordinate(value: str, *, label: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise KeyError(f"Enum {label} cannot be blank")
    return normalized


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"Expected mapping for {label}; got {type(value).__name__}")
    return value


def _require_list(
    value: object, *, provider: str, entity: str, field: str
) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(
            "Expected list but got "
            f"{type(value).__name__} for provider='{provider}', "
            f"entity='{entity}', field='{field}'"
        )
    return value


def load_provider_enums(
    provider: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> dict[str, object]:
    """Load enum configurations for a provider using injected dependency.

    The domain layer remains I/O-free; callers must inject an infrastructure
    loader such as ``FileSystemEnumLoader``.
    """
    normalized_provider = _normalize_coordinate(provider, label="provider")
    if enum_loader is None:
        raise NotImplementedError(
            "Domain layer cannot perform direct I/O. Please inject EnumLoaderProtocol implementation."
        )
    return enum_loader.load_provider_enums(normalized_provider)


def load_chembl_enums(
    enum_loader: EnumLoaderProtocol | None = None,
) -> dict[str, object]:
    """Load ChEMBL enum configurations using injected dependency.

    Args:
        enum_loader: Optional enum loader dependency. If None, raises NotImplementedError

    Returns:
        Dictionary containing all enum configurations

    Raises:
        NotImplementedError: If no enum_loader is provided (domain layer cannot do I/O)
    """
    return load_provider_enums("chembl", enum_loader)


def get_enum_config(
    section: str, key: str, enum_loader: EnumLoaderProtocol | None = None
) -> list[str]:
    """Get a ChEMBL enum configuration.

    Args:
        section: The section name (e.g., 'activity', 'assay')
        key: The key within the section (e.g., 'standard_types', 'types')
        enum_loader: Optional enum loader dependency

    Returns:
        List of enum values

    Raises:
        KeyError: If section or key not found in enum configuration
    """
    return get_provider_enum_config("chembl", section, key, enum_loader)


def get_provider_enum_config(
    provider: str,
    entity: str,
    field: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> list[str]:
    """Get a provider enum configuration.

    Args:
        provider: Provider name, for example ``chembl`` or ``uniprot``.
        entity: Entity section name, for example ``activity`` or ``protein``.
        field: Field key within the entity section.
        enum_loader: Optional enum loader dependency.

    Returns:
        List of enum values.
    """
    normalized_provider = _normalize_coordinate(provider, label="provider")
    normalized_entity = _normalize_coordinate(entity, label="entity")
    normalized_field = _normalize_coordinate(field, label="field")
    enums = load_provider_enums(normalized_provider, enum_loader)
    try:
        entity_config = _require_mapping(
            enums[normalized_entity],
            label=f"provider='{normalized_provider}', entity='{normalized_entity}'",
        )
        return _require_list(
            entity_config[normalized_field],
            provider=normalized_provider,
            entity=normalized_entity,
            field=normalized_field,
        )
    except KeyError as e:
        raise KeyError(
            "Enum configuration not found: "
            f"provider='{normalized_provider}', entity='{normalized_entity}', "
            f"field='{normalized_field}'"
        ) from e


def get_provider_enum(
    provider: str,
    entity: str,
    field: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> list[str]:
    """Get enum values for any provider/entity/field coordinate.

    This is the provider-wide registry API used by profile and governance code.
    It preserves the domain/infrastructure boundary by requiring an injected
    loader whenever file-backed values are needed.
    """
    return get_provider_enum_config(provider, entity, field, enum_loader)


def get_enum_set(
    provider: str,
    entity: str,
    field: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> frozenset[str]:
    """Get provider enum values as an immutable frozenset."""
    return frozenset(get_provider_enum(provider, entity, field, enum_loader))


def get_chembl_enum(
    entity: str,
    field: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> list[str]:
    """Get enum values for any ChEMBL entity.

    Args:
        entity: Entity name (activity, assay, molecule, target, publication)
        field: Field name (types, relations, categories, etc.)
        enum_loader: Optional enum loader dependency

    Returns:
        List of enum values

    Raises:
        KeyError: If entity or field not found in enum configuration
        TypeError: If the retrieved value is not a list
    """
    return get_provider_enum("chembl", entity, field, enum_loader)


def get_chembl_enum_set(
    entity: str,
    field: str,
    enum_loader: EnumLoaderProtocol | None = None,
) -> frozenset[str]:
    """Get enum values as immutable frozenset.

    Args:
        entity: Entity name (activity, assay, molecule, target, publication)
        field: Field name (types, relations, categories, etc.)
        enum_loader: Optional enum loader dependency

    Returns:
        Frozenset of enum values for use in normalization profiles

    Raises:
        KeyError: If entity or field not found in enum configuration
    """
    return get_enum_set("chembl", entity, field, enum_loader)
