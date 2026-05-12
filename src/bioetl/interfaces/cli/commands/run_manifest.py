"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
)
from bioetl.application.services.control_plane.historical_replay_certification_service import (
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionCorruptionError,
)
from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.forensic_diff_service import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.historical_replay_corpus_service import (
        HistoricalReplayCorpusService,
    )
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "COMMANDS",
    "diff_command",
    "forensic_diff_command",
    "inventory_command",
    "run_manifest",
    "certify_historical_bulk_command",
    "score_command",
    "show_command",
    "verify_command",
]

RUN_MANIFEST_STORE_CORRUPTION = "Run manifest store corruption"


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_run_manifest_service as _impl,
    )

    return _impl()


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Load the forensic run-diff service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_forensic_run_diff_service as _impl,
    )

    return _impl()


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Load retained-corpus replay workflows through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_historical_replay_corpus_service as _impl,
    )

    return _impl()


@click.group()
def run_manifest() -> None:
    """Inspect control-plane run manifests and ledger history."""


@run_manifest.command("show")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_command(identifier: str, output_format: str) -> None:
    """Show one manifest by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except RunManifestInspectionCorruptionError as exc:
        echo_error(RUN_MANIFEST_STORE_CORRUPTION, str(exc))
        return
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("score")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml", "text"]),
    default="json",
    help="Output format",
)
def score_command(identifier: str, output_format: str) -> None:
    """Emit one machine-readable reproducibility audit score."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except RunManifestInspectionCorruptionError as exc:
        echo_error(RUN_MANIFEST_STORE_CORRUPTION, str(exc))
        return
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    payload = {
        "identifier": identifier,
        "manifest_id": result.manifest.manifest_id,
        "run_id": str(result.manifest.run_id),
        "reproducibility_audit_score": result.diagnostics.get(
            "reproducibility_audit_score",
            {},
        ),
    }
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("diff")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diff_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Diff two manifests resolved by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.diff(left_identifier, right_identifier)
    except RunManifestInspectionCorruptionError as exc:
        echo_error(RUN_MANIFEST_STORE_CORRUPTION, str(exc))
        return
    except ValueError as exc:
        echo_error("Run manifest diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("verify")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def verify_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Verify replay evidence across manifest and effective-config stores."""
    service = get_run_manifest_service()
    try:
        result = service.verify(left_identifier, right_identifier)
    except RunManifestInspectionCorruptionError as exc:
        echo_error(RUN_MANIFEST_STORE_CORRUPTION, str(exc))
        return
    except ValueError as exc:
        echo_error("Run manifest verification failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("forensic-diff")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def forensic_diff_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Compare two runs or manifests across forensic evidence surfaces."""
    service = get_forensic_run_diff_service()
    try:
        result = service.compare(left_identifier, right_identifier)
    except RunManifestInspectionCorruptionError as exc:
        echo_error(RUN_MANIFEST_STORE_CORRUPTION, str(exc))
        return
    except ValueError as exc:
        echo_error("Forensic run diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("inventory")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def inventory_command(output_format: str) -> None:
    """Inventory retained manifests against the certified historical tranche."""
    service = get_historical_replay_corpus_service()
    result = service.build_certifiability_inventory()
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("certify-historical-bulk")
@click.argument("plan_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def certify_historical_bulk_command(
    plan_path: Path,
    output_format: str,
) -> None:
    """Apply one JSON bulk-certification plan across retained manifests."""
    service = get_historical_replay_corpus_service()
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        specs = _coerce_bulk_certification_specs(payload)
        result = service.certify_retained_corpus(specs=specs)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        echo_error("Historical replay bulk certification failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


def _coerce_bulk_certification_specs(
    payload: object,
) -> tuple[HistoricalReplayBulkCertificationSpec, ...]:
    if not isinstance(payload, dict):
        raise ValueError("Bulk certification plan must be a JSON object")
    raw_specs = payload.get("specs")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise ValueError("Bulk certification plan requires a non-empty specs list")
    specs: list[HistoricalReplayBulkCertificationSpec] = []
    for item in raw_specs:
        if not isinstance(item, dict):
            raise ValueError("Bulk certification specs must be JSON objects")
        manifest_id = str(item.get("manifest_id") or "").strip()
        if not manifest_id:
            raise ValueError("Bulk certification spec is missing manifest_id")
        raw_certifications = item.get("certifications")
        if not isinstance(raw_certifications, list) or not raw_certifications:
            raise ValueError(
                f"Bulk certification spec {manifest_id!r} requires certifications"
            )
        specs.append(
            HistoricalReplayBulkCertificationSpec(
                manifest_id=manifest_id,
                certifications=tuple(
                    _coerce_snapshot_certification(manifest_id, certification)
                    for certification in raw_certifications
                ),
            )
        )
    return tuple(specs)


def _coerce_snapshot_certification(
    manifest_id: str,
    payload: object,
) -> HistoricalReplaySnapshotCertification:
    if not isinstance(payload, dict):
        raise ValueError(
            f"Bulk certification entries for {manifest_id!r} must be JSON objects"
        )
    required_fields = (
        "provider",
        "entity",
        "pipeline_name",
        "snapshot_id",
        "content_hash",
        "immutable_uri",
        "bronze_batch_ref",
    )
    missing = [
        field for field in required_fields if not str(payload.get(field) or "").strip()
    ]
    if missing:
        raise ValueError(
            f"Bulk certification entry for {manifest_id!r} is missing fields: "
            + ", ".join(missing)
        )
    return HistoricalReplaySnapshotCertification(
        provider=str(payload["provider"]).strip(),
        entity=str(payload["entity"]).strip(),
        pipeline_name=str(payload["pipeline_name"]).strip(),
        snapshot_id=str(payload["snapshot_id"]).strip(),
        content_hash=str(payload["content_hash"]).strip(),
        immutable_uri=str(payload["immutable_uri"]).strip(),
        bronze_batch_ref=str(payload["bronze_batch_ref"]).strip(),
        query=_optional_text(payload.get("query")),
        query_fingerprint=_optional_text(payload.get("query_fingerprint")),
        certification_artifact_ref=_optional_text(
            payload.get("certification_artifact_ref")
        ),
        certification_basis=_optional_text(payload.get("certification_basis"))
        or "retained_bronze_artifact",
        upstream_run_id=_optional_text(payload.get("upstream_run_id")),
        upstream_manifest_id=_optional_text(payload.get("upstream_manifest_id")),
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


COMMANDS = (
    certify_historical_bulk_command,
    diff_command,
    forensic_diff_command,
    inventory_command,
    score_command,
    show_command,
    verify_command,
)
