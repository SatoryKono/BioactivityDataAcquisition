"""Dataset snapshot sidecar manifests for table exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl import __version__ as BIOETL_VERSION
from bioetl.application.services.export_manifest_attribution import (
    mixed_license_notice as _mixed_license_notice,
)
from bioetl.application.services.export_manifest_attribution import (
    provider_attribution_payload as _provider_attribution_payload,
)
from bioetl.application.services.export_manifest_attribution import (
    providers_for_table as _providers_for_table,
)
from bioetl.application.services.export_manifest_identity import (
    dataset_bundle_id as _dataset_bundle_id,
)
from bioetl.application.services.export_manifest_identity import (
    fingerprint_payload as _fingerprint_payload,
)
from bioetl.application.services.export_manifest_identity import (
    resolve_generated_at as _resolve_generated_at,
)
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
class ExportSidecarPayloadsRecord:
    """Provenance and licensing payloads for one exported dataset snapshot."""

    dataset_bundle_id: str
    provenance_manifest: dict[str, object]
    licensing_manifest: dict[str, object]


ExportSidecarPayloads = ExportSidecarPayloadsRecord


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
    requester: str | None = None,
    role: str = "viewer",
    filters_hash: str | None = None,
    expires_at: str | None = None,
    redaction_profile: str = "default",
    audit_ref: str | None = None,
    redacted_columns: tuple[str, ...] = (),
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
    return ExportSidecarPayloadsRecord(
        dataset_bundle_id=dataset_bundle_id,
        provenance_manifest=_build_export_provenance_manifest(
            table_name=table_name,
            layer=layer,
            export_format=export_format,
            row_count=row_count,
            columns=columns,
            providers=providers,
            provider_entries=provider_entries,
            dataset_bundle_id=dataset_bundle_id,
            timestamp=timestamp,
            data_fingerprint=data_fingerprint,
            exported_data_file=exported_data_file,
            code_revision=code_revision,
            run_ids=run_ids,
            requester=requester,
            role=role,
            filters_hash=filters_hash,
            expires_at=expires_at,
            redaction_profile=redaction_profile,
            audit_ref=audit_ref,
            redacted_columns=redacted_columns,
        ),
        licensing_manifest=_build_export_licensing_manifest(
            providers=providers,
            provider_entries=provider_entries,
            dataset_bundle_id=dataset_bundle_id,
            timestamp=timestamp,
        ),
    )


def _build_export_provenance_manifest(
    *,
    table_name: str,
    layer: str,
    export_format: str,
    row_count: int,
    columns: tuple[str, ...],
    providers: tuple[str, ...],
    provider_entries: tuple[dict[str, object], ...],
    dataset_bundle_id: str,
    timestamp: str,
    data_fingerprint: ExportFileFingerprint,
    exported_data_file: dict[str, object],
    code_revision: str | None,
    run_ids: tuple[str, ...],
    requester: str | None,
    role: str,
    filters_hash: str | None,
    expires_at: str | None,
    redaction_profile: str,
    audit_ref: str | None,
    redacted_columns: tuple[str, ...],
) -> dict[str, object]:
    """Build the deterministic export provenance sidecar payload."""
    return {
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
        "export_governance": {
            "audit_ref": audit_ref,
            "requester": requester,
            "role": role,
            "filters_hash": filters_hash,
            "expires_at": expires_at,
            "redaction_profile": redaction_profile,
            "redacted_columns": list(redacted_columns),
        },
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


def _build_export_licensing_manifest(
    *,
    providers: tuple[str, ...],
    provider_entries: tuple[dict[str, object], ...],
    dataset_bundle_id: str,
    timestamp: str,
) -> dict[str, object]:
    """Build the deterministic export licensing sidecar payload."""
    return {
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
    requester: str | None = None,
    role: str = "viewer",
    filters_hash: str | None = None,
    expires_at: str | None = None,
    redaction_profile: str = "default",
    audit_ref: str | None = None,
    redacted_columns: tuple[str, ...] = (),
    strict: bool = False,
) -> tuple[Path, ...]:
    """Write deterministic provenance, licensing, and checksum manifests."""
    data_fingerprint = writer.fingerprint_file(path=str(output_path))
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
        requester=requester,
        role=role,
        filters_hash=filters_hash,
        expires_at=expires_at,
        redaction_profile=redaction_profile,
        audit_ref=audit_ref,
        redacted_columns=redacted_columns,
        strict=strict,
    )
    manifest_prefix = output_path.stem
    provenance_path_str = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.provenance-manifest",
        payload=sidecars.provenance_manifest,
        output_dir=str(output_path.parent),
    )
    provenance_path = Path(provenance_path_str)
    licensing_path_str = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.licensing-manifest",
        payload=sidecars.licensing_manifest,
        output_dir=str(output_path.parent),
    )
    licensing_path = Path(licensing_path_str)
    checksum_payload = build_export_checksum_manifest(
        dataset_bundle_id=sidecars.dataset_bundle_id,
        generated_at=str(sidecars.provenance_manifest["generated_at"]),
        fingerprints=(
            data_fingerprint,
            writer.fingerprint_file(path=str(provenance_path)),
            writer.fingerprint_file(path=str(licensing_path)),
        ),
    )
    checksums_path_str = writer.write_manifest(
        manifest_name=f"{manifest_prefix}.checksums-manifest",
        payload=checksum_payload,
        output_dir=str(output_path.parent),
    )
    checksums_path = Path(checksums_path_str)
    return (provenance_path, licensing_path, checksums_path)
