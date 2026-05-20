"""File-backed persistence and filesystem validation for contract registries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bioetl.domain.control_plane.contract_registry import ContractRegistry
from bioetl.domain.control_plane.contract_registry_helpers import resolve_path
from bioetl.domain.control_plane.contract_registry_types import (
    RegistryValidationIssue,
    RegistryValidationResult,
    RegistryValidationSeverity,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.contract_registry_loader import (
    load_contract_registry_payload,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = [
    "FileContractRegistryStore",
    "RegistryLoadError",
    "create_contract_registry",
]


class RegistryLoadError(Exception):
    """Error loading or saving contract registry data."""


def _missing_source_issue(
    contract_ref: str,
    source_path: str,
) -> RegistryValidationIssue:
    return RegistryValidationIssue(
        message=f"Source file not found: {source_path}",
        severity=RegistryValidationSeverity.BLOCKING,
        contract_ref=contract_ref,
        field="source_path",
    )


def _missing_artifact_issue(
    contract_ref: str,
    artifact_path: str,
) -> RegistryValidationIssue:
    return RegistryValidationIssue(
        message=f"Published artifact not found: {artifact_path}",
        severity=RegistryValidationSeverity.BLOCKING,
        contract_ref=contract_ref,
        field="published_artifacts",
    )


@dataclass(slots=True)
class FileContractRegistryStore:
    """Persist contract registries as YAML files and validate file references."""

    registry_path: Path

    def load(self, registry_path: Path | None = None) -> ContractRegistry:
        """Load one registry from YAML storage."""
        path = registry_path or self.registry_path
        data = self._read_registry_data(path)
        return ContractRegistry.from_dict(data)

    def save(
        self,
        registry: ContractRegistry,
        output_path: Path | None = None,
    ) -> None:
        """Serialize one registry to YAML storage."""
        target_path = output_path or self.registry_path
        serialized = yaml.safe_dump(registry.to_dict(), sort_keys=False)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target_path, serialized)
        except OSError as exc:
            raise RegistryLoadError(f"Failed to save registry: {exc!s}") from exc

    def validate_filesystem_consistency(
        self,
        registry: ContractRegistry,
        base_path: Path | None = None,
    ) -> RegistryValidationResult:
        """Validate that source and artifact references exist on filesystem."""
        resolved_base_path = base_path or self.registry_path.parent
        issues: list[RegistryValidationIssue] = []
        for contract_ref, entry in registry.entries.items():
            if not resolve_path(entry.source_path, resolved_base_path).exists():
                issues.append(_missing_source_issue(contract_ref, entry.source_path))
            for artifact_path in entry.published_artifacts:
                if resolve_path(artifact_path, resolved_base_path).exists():
                    continue
                issues.append(_missing_artifact_issue(contract_ref, artifact_path))
        return RegistryValidationResult(valid=len(issues) == 0, issues=issues)

    @staticmethod
    def _read_registry_data(path: Path) -> JsonDict:
        try:
            return load_contract_registry_payload(path)
        except FileNotFoundError as exc:
            raise RegistryLoadError(f"Failed to read registry: {exc!s}") from exc
        except OSError as exc:
            raise RegistryLoadError(f"Failed to read registry: {exc!s}") from exc
        except ValueError as exc:
            raise RegistryLoadError(str(exc)) from exc


def create_contract_registry(registry_path: Path) -> ContractRegistry:
    """Compatibility helper for loading a file-backed contract registry."""
    return FileContractRegistryStore(registry_path).load()
