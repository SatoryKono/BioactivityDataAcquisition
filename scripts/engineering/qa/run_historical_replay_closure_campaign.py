#!/usr/bin/env python3
"""Run a deterministic retained-corpus historical replay closure campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bioetl.application.services.control_plane.historical_replay_closure_service import (
    HistoricalReplayClaimScopeMode,
    HistoricalReplayClosureService,
    HistoricalReplayResidualDisposition,
)
from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.historical_replay_certification_service import (
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.domain.control_plane import RunManifest
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileHistoricalReplayClosureStore,
    FileRunLedgerStore,
    FileRunManifestStore,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a retained-corpus historical replay closure report, optionally "
            "emitting deterministic residual dispositions and persisted artifacts."
        )
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Persist the closure report under data/output/control/historical_replay_closure.",
    )
    parser.add_argument(
        "--write-dispositions",
        action="store_true",
        help="Persist deterministic residual dispositions for currently blocked manifests.",
    )
    parser.add_argument(
        "--dispositions-path",
        type=Path,
        default=None,
        help="Use an explicit residual-disposition JSON file instead of auto-generated ones.",
    )
    parser.add_argument(
        "--auto-certify-sources",
        action="store_true",
        help="Auto-certify retained source runs when Bronze evidence is still reconstructible.",
    )
    parser.add_argument(
        "--auto-certify-composites",
        action="store_true",
        help="Auto-certify retained composite runs when certified/replayable source lineage is available.",
    )
    parser.add_argument(
        "--claim-scope-mode",
        choices=[
            "all_retained_historical_runs",
            "retained_certifiable_historical_runs",
        ],
        default="all_retained_historical_runs",
        help="Choose whether the final claim gate targets the full retained corpus or only the certifiable retained subset.",
    )
    return parser.parse_args()


def _default_disposition_for(record: dict[str, object]) -> tuple[str, str]:
    status = str(record.get("certification_status") or "").strip()
    if status == "awaiting_source_snapshot_certification":
        return (
            "reconstruct_immutable_evidence",
            "retained historical source run still requires explicit immutable snapshot certification evidence",
        )
    if status == "awaiting_certified_source_lineage":
        return (
            "certify_upstream_source_lineage",
            "historical composite run still requires certified upstream source lineage before parent replay certification",
        )
    if status == "outside_certified_historical_scope":
        return (
            "outside_universal_claim_scope",
            "retained run remains outside the currently supported certified historical replay tranche",
        )
    return (
        "manual_review_required",
        "historical replay state requires operator review before a trustworthy closure claim can be made",
    )


def _narrowed_scope_disposition_for(record: dict[str, object]) -> tuple[str, str]:
    status = str(record.get("certification_status") or "").strip()
    if status == "awaiting_source_snapshot_certification":
        return (
            "irrecoverable_missing_immutable_evidence",
            "retained source run has no trustworthy immutable snapshot evidence path left in the local corpus",
        )
    if status == "awaiting_certified_source_lineage":
        return (
            "outside_universal_claim_scope",
            "retained composite run depends on upstream source lineage that remains outside the certifiable retained evidence scope",
        )
    if status == "outside_certified_historical_scope":
        return (
            "outside_universal_claim_scope",
            "retained run remains outside the currently supported certifiable historical replay scope",
        )
    return (
        "manual_review_required",
        "historical replay state still requires operator review before a trustworthy scope decision can be made",
    )


def _build_auto_dispositions(
    inventory_payload: dict[str, object],
    *,
    claim_scope_mode: HistoricalReplayClaimScopeMode,
) -> tuple[HistoricalReplayResidualDisposition, ...]:
    records = inventory_payload.get("records")
    if not isinstance(records, list):
        return ()
    dispositions: list[HistoricalReplayResidualDisposition] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        status = str(item.get("certification_status") or "").strip()
        if status not in {
            "awaiting_source_snapshot_certification",
            "awaiting_certified_source_lineage",
            "needs_operator_review",
            "outside_certified_historical_scope",
        }:
            continue
        if claim_scope_mode == "retained_certifiable_historical_runs":
            disposition, rationale = _narrowed_scope_disposition_for(item)
        else:
            disposition, rationale = _default_disposition_for(item)
        manifest_id = str(item.get("manifest_id") or "").strip()
        if not manifest_id:
            continue
        dispositions.append(
            HistoricalReplayResidualDisposition(
                manifest_id=manifest_id,
                disposition=disposition,
                rationale=rationale,
                evidence_refs=(),
            )
        )
    return tuple(sorted(dispositions, key=lambda item: (item.manifest_id, item.disposition)))


def _load_dispositions(path: Path) -> tuple[HistoricalReplayResidualDisposition, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_items = payload.get("dispositions")
    if not isinstance(raw_items, list):
        raise ValueError("dispositions file requires a top-level dispositions list")
    result: list[HistoricalReplayResidualDisposition] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("disposition entries must be JSON objects")
        manifest_id = str(item.get("manifest_id") or "").strip()
        disposition = str(item.get("disposition") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        if not manifest_id or not disposition or not rationale:
            raise ValueError(
                "disposition entries require manifest_id, disposition, and rationale"
            )
        evidence_refs = item.get("evidence_refs")
        evidence_ref_values = (
            tuple(str(value).strip() for value in evidence_refs if str(value).strip())
            if isinstance(evidence_refs, list)
            else ()
        )
        result.append(
            HistoricalReplayResidualDisposition(
                manifest_id=manifest_id,
                disposition=disposition,
                rationale=rationale,
                evidence_refs=evidence_ref_values,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.manifest_id, item.disposition)))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load_ledger_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _build_bronze_meta_index(bronze_root: Path) -> dict[str, list[tuple[Path, dict[str, object]]]]:
    index: dict[str, list[tuple[Path, dict[str, object]]]] = {}
    for meta_path in bronze_root.rglob("*.meta.json"):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            continue
        index.setdefault(run_id, []).append((meta_path, payload))
    for items in index.values():
        items.sort(key=lambda item: str(item[0]))
    return index


def _relative_bronze_uri(bronze_root: Path, artifact_path: Path) -> str:
    return f"bronze://{artifact_path.relative_to(bronze_root).as_posix()}"


def _resolve_meta_payload_artifact_path(meta_path: Path) -> Path | None:
    text = str(meta_path)
    if not text.endswith(".meta.json"):
        return None
    candidate = Path(text[: -len(".meta.json")])
    if candidate.exists():
        return candidate
    return None


def _build_source_auto_specs(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    manifest_store: FileRunManifestStore,
    bronze_root: Path,
    bronze_meta_index: dict[str, list[tuple[Path, dict[str, object]]]],
) -> tuple[HistoricalReplayBulkCertificationSpec, ...]:
    specs: list[HistoricalReplayBulkCertificationSpec] = []
    for record in inventory.records:
        if record.certification_status != "awaiting_source_snapshot_certification":
            continue
        manifest = manifest_store.get(record.manifest_id)
        if manifest is None:
            continue
        source_ref = manifest.source_refs[0] if manifest.source_refs else None
        meta_items = bronze_meta_index.get(str(manifest.run_id), ())
        certifications: list[HistoricalReplaySnapshotCertification] = []
        for meta_path, payload in meta_items:
            artifact_path = _resolve_meta_payload_artifact_path(meta_path)
            if artifact_path is None or not artifact_path.exists():
                continue
            content_hash = _file_sha256(artifact_path)
            certifications.append(
                HistoricalReplaySnapshotCertification(
                    provider=(
                        source_ref.provider
                        if source_ref is not None
                        else manifest.provider
                    ),
                    entity=(
                        source_ref.entity if source_ref is not None else manifest.entity
                    ),
                    pipeline_name=(
                        source_ref.pipeline_name
                        if source_ref is not None
                        else manifest.pipeline_name
                    ),
                    snapshot_id=f"sha256:{content_hash}",
                    content_hash=content_hash,
                    immutable_uri=_relative_bronze_uri(bronze_root, artifact_path),
                    bronze_batch_ref=(
                        f"bronze_batch:{payload['batch_id']}"
                        if str(payload.get("batch_id") or "").strip()
                        else _relative_bronze_uri(bronze_root, artifact_path)
                    ),
                    query=source_ref.query if source_ref is not None else None,
                    certification_artifact_ref=(
                        "control://historical-replay/auto-source-certification"
                    ),
                    certification_basis="retained_bronze_artifact",
                )
            )
        if certifications:
            specs.append(
                HistoricalReplayBulkCertificationSpec(
                    manifest_id=manifest.manifest_id,
                    certifications=tuple(certifications),
                )
            )
    return tuple(specs)


def _build_valid_upstream_source_index(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    manifest_store: FileRunManifestStore,
    ledger_store: FileRunLedgerStore,
) -> dict[tuple[str, str, str], list[tuple[RunManifest, dict[str, Any]]]]:
    valid_statuses = {"already_replayable", "already_certified"}
    index: dict[tuple[str, str, str], list[tuple[RunManifest, dict[str, Any]]]] = {}
    for record in inventory.records:
        if (
            record.execution_context == "composite"
            or record.certification_status not in valid_statuses
        ):
            continue
        manifest = manifest_store.get(record.manifest_id)
        if manifest is None:
            continue
        diagnostics = build_diagnostics_summary(
            manifest,
            tuple(ledger_store.list_entries(manifest.manifest_id)),
        )
        snapshots = diagnostics.get("input_snapshots", [])
        if not isinstance(snapshots, list) or not snapshots:
            continue
        key = (manifest.provider, manifest.entity, manifest.pipeline_name)
        index.setdefault(key, []).append((manifest, diagnostics))
    for candidates in index.values():
        candidates.sort(key=lambda item: (item[0].created_at, item[0].manifest_id))
    return index


def _choose_upstream_candidate(
    candidates: list[tuple[RunManifest, dict[str, Any]]],
    *,
    composite_manifest: RunManifest,
) -> tuple[RunManifest, dict[str, Any]] | None:
    earlier_or_equal = [
        item for item in candidates if item[0].created_at <= composite_manifest.created_at
    ]
    if earlier_or_equal:
        return earlier_or_equal[-1]
    if candidates:
        return candidates[-1]
    return None


def _build_composite_auto_specs(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    manifest_store: FileRunManifestStore,
    ledger_store: FileRunLedgerStore,
) -> tuple[HistoricalReplayBulkCertificationSpec, ...]:
    upstream_index = _build_valid_upstream_source_index(
        inventory=inventory,
        manifest_store=manifest_store,
        ledger_store=ledger_store,
    )
    specs: list[HistoricalReplayBulkCertificationSpec] = []
    for record in inventory.records:
        if record.certification_status != "awaiting_certified_source_lineage":
            continue
        manifest = manifest_store.get(record.manifest_id)
        if manifest is None:
            continue
        certifications: list[HistoricalReplaySnapshotCertification] = []
        for source_ref in manifest.source_refs:
            key = (source_ref.provider, source_ref.entity, source_ref.pipeline_name)
            candidate = _choose_upstream_candidate(
                upstream_index.get(key, []),
                composite_manifest=manifest,
            )
            if candidate is None:
                certifications = []
                break
            upstream_manifest, diagnostics = candidate
            snapshots = diagnostics.get("input_snapshots", [])
            if not isinstance(snapshots, list) or not snapshots:
                certifications = []
                break
            snapshot = dict(sorted(dict(snapshots[0]).items()))
            immutable_uri = str(snapshot.get("immutable_uri") or "").strip()
            snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
            content_hash = str(snapshot.get("content_hash") or "").strip()
            if not immutable_uri or not snapshot_id or not content_hash:
                certifications = []
                break
            certifications.append(
                HistoricalReplaySnapshotCertification(
                    provider=source_ref.provider,
                    entity=source_ref.entity,
                    pipeline_name=source_ref.pipeline_name,
                    snapshot_id=snapshot_id,
                    content_hash=content_hash,
                    immutable_uri=immutable_uri,
                    bronze_batch_ref=immutable_uri,
                    query=source_ref.query,
                    query_fingerprint=str(
                        snapshot.get("query_fingerprint") or ""
                    ).strip()
                    or None,
                    certification_artifact_ref=(
                        "control://historical-replay/auto-composite-certification"
                    ),
                    certification_basis="certified_source_lineage",
                    upstream_run_id=str(upstream_manifest.run_id),
                    upstream_manifest_id=upstream_manifest.manifest_id,
                )
            )
        if certifications:
            specs.append(
                HistoricalReplayBulkCertificationSpec(
                    manifest_id=manifest.manifest_id,
                    certifications=tuple(certifications),
                )
            )
    return tuple(specs)


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    manifest_store = FileRunManifestStore(
        base_path=output_root / "run_manifest",
        metrics=metrics,
    )
    ledger_store = FileRunLedgerStore(
        base_path=output_root / "run_ledger",
        metrics=metrics,
    )
    corpus_service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
        ),
    )
    closure_service = HistoricalReplayClosureService(corpus_service=corpus_service)
    bronze_root = Path(settings.data_dir) / "output" / "bronze"
    bronze_meta_index = _build_bronze_meta_index(bronze_root)

    source_certification_result = None
    composite_certification_result = None
    inventory = corpus_service.build_certifiability_inventory()

    if args.auto_certify_sources:
        source_specs = _build_source_auto_specs(
            inventory=inventory,
            manifest_store=manifest_store,
            bronze_root=bronze_root,
            bronze_meta_index=bronze_meta_index,
        )
        if source_specs:
            source_certification_result = corpus_service.certify_retained_corpus(
                specs=source_specs
            )
            inventory = source_certification_result.inventory_after

    if args.auto_certify_composites:
        composite_specs = _build_composite_auto_specs(
            inventory=inventory,
            manifest_store=manifest_store,
            ledger_store=ledger_store,
        )
        if composite_specs:
            composite_certification_result = corpus_service.certify_retained_corpus(
                specs=composite_specs
            )
            inventory = composite_certification_result.inventory_after

    inventory_payload = inventory.to_dict()

    if args.dispositions_path is not None:
        dispositions = _load_dispositions(args.dispositions_path)
        dispositions_path = args.dispositions_path
    else:
        dispositions = _build_auto_dispositions(
            inventory_payload,
            claim_scope_mode=args.claim_scope_mode,
        )
        dispositions_path = None

    closure_report = closure_service.build_closure_report(
        residual_dispositions=dispositions,
        claim_scope_mode=args.claim_scope_mode,
    )

    closure_store = FileHistoricalReplayClosureStore(
        base_path=output_root / "historical_replay_closure"
    )
    report_path = closure_store.save(closure_report) if args.write_report else None

    written_dispositions_path: Path | None = None
    if args.write_dispositions and args.dispositions_path is None:
        written_dispositions_path = (
            output_root
            / "historical_replay_closure"
            / f"{closure_report.report_id}.residual_dispositions.json"
        )
        written_dispositions_path.parent.mkdir(parents=True, exist_ok=True)
        written_dispositions_path.write_text(
            json.dumps(
                {
                    "report_id": closure_report.report_id,
                    "dispositions": [item.to_dict() for item in dispositions],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    payload = {
        "inventory_summary": {
            "manifest_count": inventory.manifest_count,
            "certified_count": inventory.certified_count,
            "replayable_count": inventory.replayable_count,
            "awaiting_source_certification_count": (
                inventory.awaiting_source_certification_count
            ),
            "awaiting_composite_lineage_count": (
                inventory.awaiting_composite_lineage_count
            ),
            "unsupported_count": inventory.unsupported_count,
            "remaining_uncertified_count": inventory.remaining_uncertified_count,
        },
        "closure_report": {
            "report_id": closure_report.report_id,
            "closure_verdict": closure_report.closure_verdict,
            "closure_reason": closure_report.closure_reason,
            "claim_scope_mode": closure_report.claim_scope_mode,
            "global_universal_historical_replay_claim": (
                closure_report.global_universal_historical_replay_claim
            ),
            "retained_corpus_claim": closure_report.retained_corpus_claim,
            "residual_disposition_count": len(closure_report.residual_dispositions),
            "suggested_resolution_queue_count": len(
                closure_report.suggested_resolution_queue
            ),
        },
        "auto_certification": {
            "sources": (
                {
                    "completed_count": source_certification_result.completed_count,
                    "skipped_count": source_certification_result.skipped_count,
                }
                if source_certification_result is not None
                else None
            ),
            "composites": (
                {
                    "completed_count": composite_certification_result.completed_count,
                    "skipped_count": composite_certification_result.skipped_count,
                }
                if composite_certification_result is not None
                else None
            ),
        },
        "artifact_paths": {
            "closure_report": str(report_path) if report_path is not None else None,
            "residual_dispositions": (
                str(written_dispositions_path)
                if written_dispositions_path is not None
                else (
                    str(dispositions_path) if dispositions_path is not None else None
                )
            ),
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
