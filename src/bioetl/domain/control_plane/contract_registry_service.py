"""Pure contract registry semantics for parsing, registration, and hashing."""

from __future__ import annotations

import hashlib
import json

from bioetl.domain.serialization import serialize_to_json_canonical
from bioetl.domain.types import JsonDict

from .contract_registry_helpers import (
    build_existing_version_issue,
    build_version_regression_message,
    entry_payload,
    parse_entry_payload,
)
from .contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationError,
    RegistryValidationIssue,
    RegistryValidationResult,
)


class ContractRegistry:
    """Machine-verifiable contract registry without persistence concerns."""

    def __init__(self, entries: dict[str, ContractRegistryEntry] | None = None) -> None:
        """Initialize the registry with optional pre-parsed entries."""
        self.entries = dict(entries or {})
        self._registry_hash_v1: str | None = None
        self._registry_hash_v2: str | None = None
        if self.entries:
            self._calculate_registry_hash()

    @classmethod
    def from_dict(cls, data: JsonDict) -> ContractRegistry:
        """Build a registry from a parsed mapping payload."""
        entries = cls._parse_entries(data)
        return cls(entries=entries)

    @staticmethod
    def _parse_entries(data: JsonDict) -> dict[str, ContractRegistryEntry]:
        """Parse entries payload into typed registry entries."""
        entries_data = data.get("entries")
        if not isinstance(entries_data, dict):
            raise ValueError("Invalid registry format: missing 'entries' mapping")
        entries: dict[str, ContractRegistryEntry] = {}
        for contract_ref, entry_data in entries_data.items():
            if not isinstance(entry_data, dict):
                raise ValueError(f"Invalid entry payload for {contract_ref}")
            try:
                parsed_entry = parse_entry_payload(str(contract_ref), entry_data)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            entries[str(contract_ref)] = parsed_entry
        return entries

    def _build_registry_hash_payload(self) -> JsonDict:
        """Build the semantic payload used for registry hash generation."""
        registry_entries: dict[str, JsonDict] = {}
        for contract_ref, entry in sorted(self.entries.items()):
            registry_entries[contract_ref] = {
                "identity": {
                    "contract_version": entry.identity.contract_version,
                    "schema_hash": entry.identity.schema_hash,
                    "normalization_profile_ref": entry.identity.normalization_profile_ref,
                    "normalization_profile_version": entry.identity.normalization_profile_version,
                    "normalization_profile_hash": entry.identity.normalization_profile_hash,
                },
                "status": entry.status.value,
                "supported_versions": sorted(entry.supported_versions),
            }
        return registry_entries

    def _calculate_registry_hash(self) -> None:
        """Calculate legacy v1 and canonical v2 registry hashes."""
        payload = self._build_registry_hash_payload()
        legacy_repr = json.dumps(payload, sort_keys=True)
        canonical_repr = serialize_to_json_canonical(payload)
        self._registry_hash_v1 = hashlib.sha256(legacy_repr.encode("utf-8")).hexdigest()
        self._registry_hash_v2 = hashlib.sha256(
            canonical_repr.encode("utf-8")
        ).hexdigest()

    @property
    def registry_hash(self) -> str | None:
        """Return canonical registry hash (v2)."""
        return self._registry_hash_v2

    @property
    def registry_hash_v1(self) -> str | None:
        """Return legacy registry hash computed with stdlib json.dumps()."""
        return self._registry_hash_v1

    @property
    def registry_hash_v2(self) -> str | None:
        """Return canonical registry hash computed via serialize_json_canonical()."""
        return self._registry_hash_v2

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

    def to_dict(self) -> JsonDict:
        """Convert registry to dictionary for serialization."""
        return {
            "version": "1.0",
            "entries": {
                contract_ref: entry_payload(entry)
                for contract_ref, entry in self.entries.items()
            },
        }
