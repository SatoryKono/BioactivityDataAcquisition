"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionCorruptionError,
)
from bioetl.application.services.control_plane.replay_bundle_descriptor_service import (
    build_run_replay_bundle_descriptor,
)
from bioetl.interfaces.cli.commands._run_manifest_historical_support import (
    _coerce_bulk_certification_specs,
    _load_residual_dispositions,
    _load_universe_external_records,
)
from bioetl.interfaces.cli.commands._run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.commands._run_manifest_services import (
    get_forensic_run_diff_service,
    get_historical_replay_closure_service,
    get_historical_replay_corpus_service,
    get_historical_replay_universe_service,
    get_run_manifest_service,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "COMMANDS",
    "certify_historical_bulk_command",
    "closure_report_command",
    "diff_command",
    "forensic_diff_command",
    "inventory_command",
    "replay_bundle_command",
    "run_manifest",
    "score_command",
    "show_command",
    "universe_report_command",
    "verify_command",
]

RUN_MANIFEST_STORE_CORRUPTION = "Run manifest store corruption"


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


@run_manifest.command("replay-bundle")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def replay_bundle_command(identifier: str, output_format: str) -> None:
    """Emit one replay-bundle descriptor for a supported run."""
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
        build_run_replay_bundle_descriptor(result).to_dict(),
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
@click.argument(
    "plan_path", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
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


@run_manifest.command("closure-report")
@click.option(
    "--dispositions",
    "dispositions_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional JSON residual-disposition file.",
)
@click.option(
    "--write",
    "write_artifact",
    is_flag=True,
    help="Persist the closure report under data/output/control/historical_replay_closure.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def closure_report_command(
    dispositions_path: Path | None,
    write_artifact: bool,
    output_format: str,
) -> None:
    """Build one retained-corpus closure report and optional persisted artifact."""
    service = get_historical_replay_closure_service()
    try:
        dispositions = _load_residual_dispositions(dispositions_path)
        report = service.build_closure_report(
            residual_dispositions=dispositions,
        )
        payload = report.to_dict()
        if write_artifact:
            from bioetl.composition.control_plane_api import (
                persist_historical_replay_closure_report,
            )

            artifact_path = persist_historical_replay_closure_report(report)
            payload = {**payload, "artifact_path": str(artifact_path)}
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        echo_error("Historical replay closure report failed", str(exc))
        return
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("universe-report")
@click.option(
    "--external-pack",
    "external_pack_paths",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    multiple=True,
    help="Authoritative archived/offline historical-run pack to merge into the full-universe report.",
)
@click.option(
    "--write",
    "write_artifact",
    is_flag=True,
    help="Persist the full-universe report under data/output/control/historical_replay_universe.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def universe_report_command(
    external_pack_paths: tuple[Path, ...],
    write_artifact: bool,
    output_format: str,
) -> None:
    """Build one full-universe historical replay report from retained and archived corpora."""
    service = get_historical_replay_universe_service()
    try:
        external_records = _load_universe_external_records(external_pack_paths)
        report = service.build_universe_closure_report(
            external_records=external_records,
        )
        payload = report.to_dict()
        if write_artifact:
            from bioetl.composition.control_plane_api import (
                persist_historical_replay_universe_report,
            )

            artifact_path = persist_historical_replay_universe_report(report)
            payload = {**payload, "artifact_path": str(artifact_path)}
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        echo_error("Historical replay universe report failed", str(exc))
        return
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=render_text_payload,
    )


COMMANDS = (
    certify_historical_bulk_command,
    closure_report_command,
    diff_command,
    forensic_diff_command,
    inventory_command,
    score_command,
    show_command,
    universe_report_command,
    verify_command,
)
