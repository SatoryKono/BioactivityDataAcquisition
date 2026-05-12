#!/usr/bin/env python3
"""Run a deterministic retained-corpus historical replay closure campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioetl.application.services.control_plane.historical_replay_closure_service import (
    HistoricalReplayClosureService,
    HistoricalReplayResidualDisposition,
)
from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
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


def _build_auto_dispositions(
    inventory_payload: dict[str, object],
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
    )
    closure_service = HistoricalReplayClosureService(corpus_service=corpus_service)
    inventory = corpus_service.build_certifiability_inventory()
    inventory_payload = inventory.to_dict()

    if args.dispositions_path is not None:
        dispositions = _load_dispositions(args.dispositions_path)
        dispositions_path = args.dispositions_path
    else:
        dispositions = _build_auto_dispositions(inventory_payload)
        dispositions_path = None

    closure_report = closure_service.build_closure_report(
        residual_dispositions=dispositions,
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
            "global_universal_historical_replay_claim": (
                closure_report.global_universal_historical_replay_claim
            ),
            "retained_corpus_claim": closure_report.retained_corpus_claim,
            "residual_disposition_count": len(closure_report.residual_dispositions),
            "suggested_resolution_queue_count": len(
                closure_report.suggested_resolution_queue
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
