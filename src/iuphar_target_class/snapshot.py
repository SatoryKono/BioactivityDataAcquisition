"""Immutable snapshot provider and offline completeness checks.

A snapshot is not a full release while coverage and species are unapproved
or any completeness check fails. Incomplete data yields source_unavailable,
not not_found.
"""

from __future__ import annotations

from dataclasses import dataclass

from .stage0.io import canonical_json_bytes, sha256_bytes

VERSION_MATCHED = "совпали"
VERSION_DIFFER = "различаются"
VERSION_UNAVAILABLE = "недоступны"


@dataclass(frozen=True, slots=True)
class FrozenRecord:
    """One stored payload. Callers receive these bytes, not a live dict."""

    kind: str
    record_id: str
    payload: bytes
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class TargetView:
    """Index fields copied from a frozen target payload."""

    target_id: str
    uniprot_ids: tuple[str, ...]
    gene_symbol: str | None
    species: str | None
    family_ids: tuple[str, ...]
    taxon: str | None
    type_name: str | None
    record: FrozenRecord


@dataclass(frozen=True, slots=True)
class ProviderHit:
    """Raw records, the hash of a single record, and diagnostics."""

    records: tuple[FrozenRecord, ...]
    payload_sha256: str | None
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Completeness:
    """Offline manifest result. Only a complete snapshot may be published."""

    complete: bool
    publishable: bool
    version_unverified: bool
    allows_not_found: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SnapshotIndexes:
    """Indexes built once. The version is the hash of the sorted keys."""

    version: str
    target_ids: tuple[str, ...]
    uniprot_ids: tuple[str, ...]
    gene_keys: tuple[str, ...]
    family_ids: tuple[str, ...]


def freeze_record(kind: str, record_id: str, payload: object) -> FrozenRecord:
    """Store canonical JSON bytes and their SHA-256."""
    raw = canonical_json_bytes(payload)
    return FrozenRecord(kind, record_id, raw, sha256_bytes(raw))


class SnapshotProvider:
    """Read-only snapshot. Repeated reads return the same bytes and hash."""

    def __init__(
        self,
        targets: tuple[TargetView, ...],
        families: tuple[FrozenRecord, ...],
    ) -> None:
        self._targets: dict[str, TargetView] = {}
        self._uniprot: dict[str, list[str]] = {}
        self._gene: dict[tuple[str, str], list[str]] = {}
        self._families: dict[str, FrozenRecord] = {}
        for target in targets:
            if target.target_id in self._targets:
                message = f"duplicate target id: {target.target_id}"
                raise ValueError(message)
            self._targets[target.target_id] = target
            for accession in target.uniprot_ids:
                self._uniprot.setdefault(accession, []).append(target.target_id)
            if target.gene_symbol and target.species:
                key = (target.gene_symbol, target.species)
                self._gene.setdefault(key, []).append(target.target_id)
        for family in families:
            if family.record_id in self._families:
                message = f"duplicate family id: {family.record_id}"
                raise ValueError(message)
            self._families[family.record_id] = family
        self.indexes = _indexes(
            self._targets,
            self._uniprot,
            self._gene,
            self._families,
        )

    def get_target(self, target_id: str) -> ProviderHit:
        """Return the stored target payload, or an empty hit."""
        target = self._targets.get(target_id)
        if target is None:
            return ProviderHit((), None, ())
        return ProviderHit((target.record,), target.record.payload_sha256, ())

    def find_by_uniprot(self, accession: str) -> ProviderHit:
        """Return every target linked to this accession, in id order."""
        return self._collect(self._uniprot.get(accession, ()))

    def find_by_gene(self, symbol: str, species: str) -> ProviderHit:
        """Return targets for one gene symbol in one species."""
        return self._collect(self._gene.get((symbol, species), ()))

    def get_families(self, family_ids: tuple[str, ...]) -> ProviderHit:
        """Return stored families. A missing id is a diagnostic."""
        records: list[FrozenRecord] = []
        missing: list[str] = []
        for family_id in family_ids:
            family = self._families.get(family_id)
            if family is None:
                missing.append(family_id)
            else:
                records.append(family)
        diagnostics = tuple(f"missing family {family_id}" for family_id in missing)
        digest = records[0].payload_sha256 if len(records) == 1 else None
        return ProviderHit(tuple(records), digest, diagnostics)

    def _collect(self, target_ids: list[str] | tuple[str, ...]) -> ProviderHit:
        ordered = tuple(
            self._targets[target_id].record for target_id in sorted(set(target_ids))
        )
        digest = ordered[0].payload_sha256 if len(ordered) == 1 else None
        return ProviderHit(ordered, digest, ())


def assess_completeness(
    *,
    coverage_approved: bool,
    required_types_loaded: bool,
    pagination_complete: bool,
    transport_or_schema_errors: bool,
    totals_match: bool,
    provider_versions: str,
    version_limitation_recorded: bool,
) -> Completeness:
    """Apply the offline completeness rule. Unapproved coverage cannot publish."""
    known = {VERSION_MATCHED, VERSION_DIFFER, VERSION_UNAVAILABLE}
    if provider_versions not in known:
        message = "provider version state is not recognised"
        raise ValueError(message)
    version_unverified = provider_versions == VERSION_UNAVAILABLE
    if not coverage_approved:
        return Completeness(
            complete=False,
            publishable=False,
            version_unverified=version_unverified,
            allows_not_found=False,
            reason="охват и набор видов снимка не утверждены",
        )
    problems: list[str] = []
    if not required_types_loaded:
        problems.append("обязательные типы не загружены")
    if not pagination_complete or transport_or_schema_errors:
        problems.append("пагинация или транспорт/схема")
    if not totals_match:
        problems.append("контрольные итоги расходятся")
    if provider_versions == VERSION_DIFFER:
        problems.append("версии поставщика различаются")
    if problems:
        return Completeness(
            complete=False,
            publishable=False,
            version_unverified=version_unverified,
            allows_not_found=False,
            reason="; ".join(problems),
        )
    if version_unverified and not version_limitation_recorded:
        return Completeness(
            complete=False,
            publishable=False,
            version_unverified=True,
            allows_not_found=False,
            reason="version_unverified без ограничения в manifest",
        )
    return Completeness(
        complete=True,
        publishable=not version_unverified,
        version_unverified=version_unverified,
        allows_not_found=True,
        reason="version_unverified" if version_unverified else "полнота выполнена",
    )


def absence_status(completeness: Completeness) -> str:
    """Map an empty finished search to not_found only on a complete snapshot."""
    if completeness.allows_not_found:
        return "not_found"
    return "source_unavailable"


def _indexes(
    targets: dict[str, TargetView],
    uniprot: dict[str, list[str]],
    gene: dict[tuple[str, str], list[str]],
    families: dict[str, FrozenRecord],
) -> SnapshotIndexes:
    target_ids = tuple(sorted(targets))
    uniprot_ids = tuple(sorted(uniprot))
    gene_keys = tuple(sorted(f"{symbol}|{species}" for symbol, species in gene))
    family_ids = tuple(sorted(families))
    version = sha256_bytes(
        canonical_json_bytes(
            {
                "families": family_ids,
                "genes": gene_keys,
                "targets": target_ids,
                "uniprot": uniprot_ids,
            },
        ),
    )
    return SnapshotIndexes(version, target_ids, uniprot_ids, gene_keys, family_ids)
