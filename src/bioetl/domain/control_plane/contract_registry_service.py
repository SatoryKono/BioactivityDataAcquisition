"""Contract registry service with parsing, registration, and serialization logic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict

from .contract_registry_helpers import (
    build_existing_version_issue,
    build_version_regression_message,
    entry_payload,
    parse_entry_payload,
    resolve_path,
)
from .contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationError,
    RegistryValidationIssue,
    RegistryValidationResult,
    RegistryValidationSeverity,
)


class RegistryLoadError(Exception):
    """Error loading or saving contract registry data."""


def _missing_source_issue(
    contract_ref: str,
    source_path: str,
) -> RegistryValidationIssue:
    """Build source-path missing issue."""
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
    """Build artifact-path missing issue."""
    return RegistryValidationIssue(
        message=f"Published artifact not found: {artifact_path}",
        severity=RegistryValidationSeverity.BLOCKING,
        contract_ref=contract_ref,
        field="published_artifacts",
    )


class ContractRegistry:
    """Machine-verifiable contract registry."""

    def __init__(self, registry_path: Path | None = None) -> None:
        """Initialize contract registry, optionally loading it from a file path."""
        self.registry_path = registry_path
        self.entries: dict[str, ContractRegistryEntry] = {}
        self._registry_hash: str | None = None
        if registry_path is not None and registry_path.is_file():
            self.load(registry_path)

    def load(self, registry_path: Path | None = None) -> None:
        """Load registry from YAML file."""
        path = registry_path or self.registry_path
        if path is None:
            raise RegistryLoadError("Registry path is not set")
        self.registry_path = path
        data = self._read_registry_data(path)
        self.entries = self._parse_entries(data)
        self._calculate_registry_hash()

    def _read_registry_data(self, path: Path) -> JsonDict:
        """Read and parse registry YAML content."""
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RegistryLoadError(f"Failed to read registry: {exc!s}") from exc
        try:
            loaded = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise RegistryLoadError(f"Invalid registry YAML: {exc!s}") from exc
        if not isinstance(loaded, dict):
            raise RegistryLoadError("Invalid registry format: expected mapping")
        return loaded

    def _parse_entries(self, data: JsonDict) -> dict[str, ContractRegistryEntry]:
        """Parse entries payload into typed registry entries."""
        entries_data = data.get("entries")
        if not isinstance(entries_data, dict):
            raise RegistryLoadError(
                "Invalid registry format: missing 'entries' mapping"
            )
        entries: dict[str, ContractRegistryEntry] = {}
        for contract_ref, entry_data in entries_data.items():
            if not isinstance(entry_data, dict):
                raise RegistryLoadError(f"Invalid entry payload for {contract_ref}")
            try:
                parsed_entry = parse_entry_payload(str(contract_ref), entry_data)
            except ValueError as exc:
                raise RegistryLoadError(str(exc)) from exc
            entries[str(contract_ref)] = parsed_entry
        return entries

    def _calculate_registry_hash(self) -> None:
        """Calculate SHA256 hash of canonical registry content."""
        canonical_entries: dict[str, JsonDict] = {}
        for contract_ref, entry in sorted(self.entries.items()):
            canonical_entries[contract_ref] = {
                "identity": {
                    "contract_version": entry.identity.contract_version,
                    "schema_hash": entry.identity.schema_hash,
                },
                "status": entry.status.value,
                "supported_versions": sorted(entry.supported_versions),
            }
        canonical_repr = json.dumps(canonical_entries, sort_keys=True)
        self._registry_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    @property
    def registry_hash(self) -> str | None:
        """Return current registry hash."""
        return self._registry_hash

    def _validate_version_sequence(
        self,
        existing_entry: ContractRegistryEntry,
        candidate_entry: ContractRegistryEntry,
    ) -> None:
        """Validate that candidate version does not regress."""
        message = build_version_regression_message(
            existing_version_label=existing_entry.identity.contract_version,
            candidate_version_label=candidate_entry.identity.contract_version,
        )
        if message is not None:
            raise RegistryValidationError(message)

    def _validate_against_existing(
        self,
        existing: ContractRegistryEntry | None,
        candidate: ContractRegistryEntry,
    ) -> list[RegistryValidationIssue]:
        """Validate candidate against existing entry and return warnings."""
        if existing is None:
            return []
        if candidate.identity.contract_version != existing.identity.contract_version:
            self._validate_version_sequence(existing, candidate)
            return []
        warning = build_existing_version_issue(existing, candidate)
        return [warning] if warning is not None else []

    def register_contract(
        self, entry: ContractRegistryEntry
    ) -> RegistryValidationResult:
        """Register a new contract entry."""
        issues = entry.validate()
        if issues:
            return RegistryValidationResult(valid=False, issues=issues)

        existing = self.entries.get(entry.identity.contract_ref)
        issues.extend(self._validate_against_existing(existing, entry))
        self.entries[entry.identity.contract_ref] = entry
        self._calculate_registry_hash()
        return RegistryValidationResult(valid=len(issues) == 0, issues=issues)

    def get_entry(self, contract_ref: str) -> ContractRegistryEntry | None:
        """Get registry entry by contract reference."""
        return self.entries.get(contract_ref)

    def validate_all(self) -> RegistryValidationResult:
        """Validate all registered entries."""
        all_issues: list[RegistryValidationIssue] = []
        for contract_ref, entry in self.entries.items():
            entry_issues = entry.validate()
            for issue in entry_issues:
                if issue.contract_ref is not None:
                    all_issues.append(issue)
                    continue
                all_issues.append(
                    RegistryValidationIssue(
                        message=issue.message,
                        severity=issue.severity,
                        contract_ref=contract_ref,
                        field=issue.field,
                    )
                )
        return RegistryValidationResult(valid=len(all_issues) == 0, issues=all_issues)

    def _artifact_issues(
        self,
        contract_ref: str,
        artifacts: list[str],
        base_path: Path | None,
    ) -> list[RegistryValidationIssue]:
        """Return missing artifact issues for one entry."""
        issues: list[RegistryValidationIssue] = []
        for artifact_path in artifacts:
            if resolve_path(artifact_path, base_path).exists():
                continue
            issues.append(_missing_artifact_issue(contract_ref, artifact_path))
        return issues

    def validate_filesystem_consistency(
        self,
        base_path: Path | None = None,
    ) -> RegistryValidationResult:
        """Validate that source and artifact references exist on filesystem."""
        if base_path is None and self.registry_path is not None:
            base_path = self.registry_path.parent
        issues: list[RegistryValidationIssue] = []
        for contract_ref, entry in self.entries.items():
            if not resolve_path(entry.source_path, base_path).exists():
                issues.append(_missing_source_issue(contract_ref, entry.source_path))
            issues.extend(
                self._artifact_issues(
                    contract_ref=contract_ref,
                    artifacts=entry.published_artifacts,
                    base_path=base_path,
                )
            )
        return RegistryValidationResult(valid=len(issues) == 0, issues=issues)

    def to_dict(self) -> JsonDict:
        """Convert registry to dictionary for serialization."""
        return {
            "version": "1.0",
            "entries": {
                contract_ref: entry_payload(entry)
                for contract_ref, entry in self.entries.items()
            },
        }

    def save(self, output_path: Path | None = None) -> None:
        """Save registry to YAML file."""
        target_path = output_path or self.registry_path
        if target_path is None:
            raise RegistryLoadError("No output path specified and no registry path set")
        serialized = yaml.dump(self.to_dict(), sort_keys=False)
        try:
            target_path.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            raise RegistryLoadError(f"Failed to save registry: {exc!s}") from exc
        self.registry_path = target_path
        self._calculate_registry_hash()


def create_contract_registry(registry_path: Path | None = None) -> ContractRegistry:
    """Factory function for ContractRegistry."""
    return ContractRegistry(registry_path)
