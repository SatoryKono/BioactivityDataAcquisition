"""Dataset snapshot sidecar manifests for table exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl import __version__ as BIOETL_VERSION
from bioetl.domain.ports import ExportFileFingerprint

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.ports import ClockPort, ExportWriterPort

__all__ = [
    "ExportSidecarPayloads",
    "build_export_checksum_manifest",
    "build_export_sidecar_payloads",
    "write_export_sidecar_manifests",
]

MANIFEST_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ProviderAttributionRecord:
    """Provider-level data attribution and redistribution metadata."""

    provider: str
    source_url: str
    license_name: str
    license_url: str
    attribution_text: str
    redistribution_notes: str
    caveats: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExportSidecarPayloadsRecord:
    """Provenance and licensing payloads for one exported dataset snapshot."""

    dataset_bundle_id: str
    provenance_manifest: dict[str, object]
    licensing_manifest: dict[str, object]


ProviderAttribution = ProviderAttributionRecord
ExportSidecarPayloads = ExportSidecarPayloadsRecord


_PROVIDER_ATTRIBUTIONS: dict[str, ProviderAttributionRecord] = {
    "chembl": ProviderAttributionRecord(
        provider="chembl",
        source_url="https://www.ebi.ac.uk/chembl/",
        license_name="CC BY-SA 3.0",
        license_url="https://www.ebi.ac.uk/chembl/terms",
        attribution_text="ChEMBL data is provided by EMBL-EBI.",
        redistribution_notes=(
            "Preserve ChEMBL attribution and review share-alike obligations for "
            "redistributed derived datasets."
        ),
    ),
    "crossref": ProviderAttributionRecord(
        provider="crossref",
        source_url="https://api.crossref.org",
        license_name="Crossref metadata terms",
        license_url="https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
        attribution_text="Crossref metadata is provided by Crossref members.",
        redistribution_notes=(
            "Metadata is generally open, but linked full text and abstracts may "
            "carry separate rights."
        ),
    ),
    "openalex": ProviderAttributionRecord(
        provider="openalex",
        source_url="https://openalex.org/",
        license_name="CC0",
        license_url="https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing",
        attribution_text="OpenAlex data is provided by OurResearch.",
        redistribution_notes="OpenAlex states that its data is licensed as CC0.",
    ),
    "pubchem": ProviderAttributionRecord(
        provider="pubchem",
        source_url="https://pubchem.ncbi.nlm.nih.gov/",
        license_name="Source-specific / mixed",
        license_url="https://pubchem.ncbi.nlm.nih.gov/docs/downloads",
        attribution_text="PubChem data is provided by NCBI and PubChem contributors.",
        redistribution_notes=(
            "PubChem aggregates contributor data; check row/source provenance for "
            "source-specific licensing before redistribution."
        ),
    ),
    "pubmed": ProviderAttributionRecord(
        provider="pubmed",
        source_url="https://pubmed.ncbi.nlm.nih.gov/",
        license_name="NLM/NCBI terms and source-specific rights",
        license_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
        attribution_text="PubMed metadata is provided by NLM/NCBI.",
        redistribution_notes=(
            "Citation metadata and abstracts can have different rights; preserve "
            "source attribution and review NLM policies."
        ),
    ),
    "semanticscholar": ProviderAttributionRecord(
        provider="semanticscholar",
        source_url="https://www.semanticscholar.org/",
        license_name="Semantic Scholar API License Agreement",
        license_url="https://www.semanticscholar.org/product/api/license",
        attribution_text="Semantic Scholar data is provided by AI2.",
        redistribution_notes=(
            "Semantic Scholar API/data terms require attribution and may include "
            "use restrictions for API-derived data."
        ),
    ),
    "uniprot": ProviderAttributionRecord(
        provider="uniprot",
        source_url="https://www.uniprot.org/",
        license_name="CC BY 4.0",
        license_url="https://www.uniprot.org/help/license",
        attribution_text="UniProt data is provided by the UniProt Consortium.",
        redistribution_notes="Preserve UniProt attribution for redistributed outputs.",
    ),
}

_COMPOSITE_SOURCES: dict[str, tuple[str, ...]] = {
    "composite.activity": ("chembl",),
    "composite.assay": ("chembl",),
    "composite.molecule": ("chembl", "pubchem"),
    "composite.publication": (
        "chembl",
        "openalex",
        "pubmed",
        "semanticscholar",
    ),
    "composite.target": ("chembl", "uniprot"),
}


def build_export_sidecar_payloads(
    *,
    table_name: str,
    layer: str,
    export_format: str,
    row_count: int,
    columns: tuple[str, ...],
    data_fingerprint: ExportFileFingerprint,
    generated_at: str | None = None,
    allow_nondeterministic_generated_at: bool = False,
    clock: ClockPort | None = None,
    run_ids: tuple[str, ...] = (),
    code_revision: str | None = None,
    strict: bool = False,
) -> ExportSidecarPayloads:
    """Build deterministic provenance and licensing payloads for one export."""
    providers = _providers_for_table(table_name)
    provider_entries = tuple(
        _provider_attribution_payload(provider, strict=strict) for provider in providers
    )
    dataset_bundle_id = _dataset_bundle_id(
        table_name=table_name,
        layer=layer,
        export_format=export_format,
        row_count=row_count,
        columns=columns,
        providers=providers,
        data_sha256=data_fingerprint.sha256,
    )
    timestamp = _resolve_generated_at(
        generated_at,
        allow_nondeterministic=allow_nondeterministic_generated_at,
        clock=clock,
    )
    exported_data_file = _fingerprint_payload(data_fingerprint)

    provenance_manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "bioetl.dataset_snapshot.provenance",
        "dataset_bundle_id": dataset_bundle_id,
        "generated_at": timestamp,
        "bioetl_version": BIOETL_VERSION,
        "code_revision": code_revision,
        "table_name": table_name,
        "layer": layer,
        "export_format": export_format,
        "row_count": row_count,
        "columns": list(columns),
        "run_ids": list(run_ids),
        "providers": list(providers),
        "source_endpoints": [
            entry["source_url"] for entry in provider_entries if entry["source_url"]
        ],
        "exported_files": [exported_data_file],
        "schema_contract": {
            "contract_ref": f"{layer}:{table_name}",
            "schema_version": "not_collected",
            "field_count": len(columns),
        },
        "transformation_policies": {
            "status": "not_collected_in_export_service",
            "normalization_policy_refs": [],
        },
        "retrieval_window": {
            "status": "not_collected_in_export_service",
            "started_at": None,
            "finished_at": None,
        },
        "data_quality": {
            "status": "not_collected_in_export_service",
            "quarantined_records": None,
            "dq_report_ref": None,
        },
        "offline_validation": {
            "checksum_manifest_required": True,
            "data_file_sha256": data_fingerprint.sha256,
        },
    }
    licensing_manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "bioetl.dataset_snapshot.licensing",
        "dataset_bundle_id": dataset_bundle_id,
        "generated_at": timestamp,
        "code_license": {
            "license_name": "MIT",
            "license_url": "https://opensource.org/license/mit",
            "scope": "BioETL source code only",
        },
        "data_licenses": list(provider_entries),
        "mixed_license_behavior": _mixed_license_notice(providers),
        "legal_notice": (
            "This manifest records provider attribution and known redistribution "
            "caveats; it is not legal advice."
        ),
    }
    return ExportSidecarPayloadsRecord(
        dataset_bundle_id=dataset_bundle_id,
        provenance_manifest=provenance_manifest,
        licensing_manifest=licensing_manifest,
    )


def build_export_checksum_manifest(
    *,
    dataset_bundle_id: str,
    generated_at: str | None,
    fingerprints: tuple[ExportFileFingerprint, ...],
    allow_nondeterministic_generated_at: bool = False,
    clock: ClockPort | None = None,
) -> dict[str, object]:
    """Build a deterministic checksum manifest for data and sidecar files."""
    timestamp = _resolve_generated_at(
        generated_at,
        allow_nondeterministic=allow_nondeterministic_generated_at,
        clock=clock,
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "bioetl.dataset_snapshot.checksums",
        "dataset_bundle_id": dataset_bundle_id,
        "generated_at": timestamp,
        "algorithm": "sha256",
        "files": [_fingerprint_payload(fingerprint) for fingerprint in fingerprints],
    }


def write_export_sidecar_manifests(
    *,
    writer: ExportWriterPort,
    table: pa.Table,
    table_name: str,
    layer: str,
    export_format: str,
    output_path: Path,
    row_count: int,
    generated_at: str | None = None,
    allow_nondeterministic_generated_at: bool = False,
    clock: ClockPort | None = None,
    run_ids: tuple[str, ...] = (),
    code_revision: str | None = None,
    strict: bool = False,
) -> tuple[Path, ...]:
    """Write deterministic provenance, licensing, and checksum manifests."""
    data_fingerprint = writer.fingerprint_file(path=output_path)
    sidecars = build_export_sidecar_payloads(
        table_name=table_name,
        layer=layer,
        export_format=export_format,
        row_count=row_count,
        columns=tuple(field.name for field in table.schema),
        data_fingerprint=data_fingerprint,
        generated_at=generated_at,
        allow_nondeterministic_generated_at=allow_nondeterministic_generated_at,
        clock=clock,
        run_ids=run_ids,
        code_revision=code_revision,
        strict=strict,
    )
    manifest_prefix = output_path.stem
    provenance_path = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.provenance-manifest",
        payload=sidecars.provenance_manifest,
        output_dir=output_path.parent,
    )
    licensing_path = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.licensing-manifest",
        payload=sidecars.licensing_manifest,
        output_dir=output_path.parent,
    )
    checksum_payload = build_export_checksum_manifest(
        dataset_bundle_id=sidecars.dataset_bundle_id,
        generated_at=str(sidecars.provenance_manifest["generated_at"]),
        fingerprints=(
            data_fingerprint,
            writer.fingerprint_file(path=provenance_path),
            writer.fingerprint_file(path=licensing_path),
        ),
    )
    checksums_path = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.checksums-manifest",
        payload=checksum_payload,
        output_dir=output_path.parent,
    )
    return (provenance_path, licensing_path, checksums_path)


def _providers_for_table(table_name: str) -> tuple[str, ...]:
    if table_name in _COMPOSITE_SOURCES:
        return _COMPOSITE_SOURCES[table_name]
    provider = table_name.split(".", maxsplit=1)[0].strip()
    return (provider or "unknown",)


def _provider_attribution_payload(
    provider: str,
    *,
    strict: bool,
) -> dict[str, object]:
    attribution = _PROVIDER_ATTRIBUTIONS.get(provider)
    if attribution is None:
        if strict:
            raise ValueError(
                f"Missing provider attribution for export provider: {provider}"
            )
        return {
            "provider": provider,
            "source_url": None,
            "license_name": "unknown",
            "license_url": None,
            "attribution_text": None,
            "redistribution_notes": (
                "Provider attribution is not registered; review source terms before "
                "redistribution."
            ),
            "caveats": ["missing_provider_attribution"],
        }
    payload = asdict(attribution)
    payload["caveats"] = list(attribution.caveats)
    return payload


def _dataset_bundle_id(
    *,
    table_name: str,
    layer: str,
    export_format: str,
    row_count: int,
    columns: tuple[str, ...],
    providers: tuple[str, ...],
    data_sha256: str,
) -> str:
    payload = {
        "columns": list(columns),
        "data_sha256": data_sha256,
        "export_format": export_format,
        "layer": layer,
        "providers": list(providers),
        "row_count": row_count,
        "table_name": table_name,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return f"bioetl-export-{digest}"


def _fingerprint_payload(fingerprint: ExportFileFingerprint) -> dict[str, object]:
    return {
        "path": fingerprint.path.as_posix(),
        "size_bytes": fingerprint.size_bytes,
        "sha256": fingerprint.sha256,
    }


def _mixed_license_notice(providers: tuple[str, ...]) -> str:
    if len(providers) <= 1:
        return (
            "Single-provider export; data/output license obligations remain separate "
            "from the MIT code license."
        )
    return (
        "Composite or multi-provider export; downstream redistribution must satisfy "
        "all contributing provider terms and must not be treated as MIT-licensed data."
    )


def _resolve_generated_at(
    generated_at: str | None,
    *,
    allow_nondeterministic: bool,
    clock: ClockPort | None,
) -> str:
    """Resolve export manifest timestamp without implicit replay-time wall clock drift."""
    if generated_at is not None:
        timestamp = generated_at.strip()
        if timestamp:
            return timestamp
    if allow_nondeterministic:
        if clock is not None:
            return _format_utc(clock.now())
        return _utc_now()
    raise ValueError(
        "generated_at must be provided for deterministic export manifests; "
        "operator-only exports must opt into non-deterministic generated_at"
    )


def _utc_now() -> str:
    return _format_utc(datetime.now(UTC))


def _format_utc(value: datetime) -> str:
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
