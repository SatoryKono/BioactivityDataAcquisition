"""Utility for loading enum configurations from YAML files."""

from __future__ import annotations

from typing import Protocol

__all__ = [
    "EnumLoaderPort",
    "get_chembl_enum",
    "get_chembl_enum_set",
    "get_enum_config",
    "load_chembl_enums",
]


class EnumLoaderPort(Protocol):
    """Port for loading enum configurations. Implemented by infrastructure layer."""

    def load_chembl_enums(
        self,
    ) -> dict[str, object]:  # Any: Enum data structure from YAML
        """Load ChEMBL enum configurations.

        Returns:
            Dictionary containing all enum configurations
        """
        ...


def load_chembl_enums(enum_loader: EnumLoaderPort | None = None) -> dict[str, object]:
    """Load ChEMBL enum configurations using injected dependency.

    Args:
        enum_loader: Optional enum loader dependency. If None, raises NotImplementedError

    Returns:
        Dictionary containing all enum configurations

    Raises:
        NotImplementedError: If no enum_loader is provided (domain layer cannot do I/O)
    """
    if enum_loader is None:
        raise NotImplementedError(
            "Domain layer cannot perform direct I/O. Please inject EnumLoaderPort implementation."
        )
    return enum_loader.load_chembl_enums()


def get_enum_config(
    section: str, key: str, enum_loader: EnumLoaderPort | None = None
) -> list[str]:
    """Get a specific enum configuration.

    Args:
        section: The section name (e.g., 'activity', 'assay')
        key: The key within the section (e.g., 'standard_types', 'types')
        enum_loader: Optional enum loader dependency

    Returns:
        List of enum values

    Raises:
        KeyError: If section or key not found in enum configuration
    """
    enums = load_chembl_enums(enum_loader)
    try:
        return enums[section][key]
    except KeyError as e:
        raise KeyError(
            f"Enum configuration not found: section='{section}', key='{key}'"
        ) from e


def get_chembl_enum(entity: str, field: str) -> list[str]:
    """Get enum values for any ChEMBL entity.

    Args:
        entity: Entity name (activity, assay, molecule, target, publication)
        field: Field name (types, relations, categories, etc.)

    Returns:
        List of enum values

    Raises:
        KeyError: If entity or field not found in enum configuration
    """
    enums = load_chembl_enums()
    try:
        return enums[entity][field]
    except KeyError as e:
        raise KeyError(f"Enum not found: entity='{entity}', field='{field}'") from e


def get_chembl_enum_set(entity: str, field: str) -> frozenset[str]:
    """Get enum values as immutable frozenset.

    Args:
        entity: Entity name (activity, assay, molecule, target, publication)
        field: Field name (types, relations, categories, etc.)

    Returns:
        Frozenset of enum values for use in normalization profiles

    Raises:
        KeyError: If entity or field not found in enum configuration
    """
    return frozenset(get_chembl_enum(entity, field))
