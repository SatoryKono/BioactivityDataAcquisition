#!/usr/bin/env python3
"""Build a full-universe historical replay closure artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseExternalRecord,
    HistoricalReplayUniverseService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.application.runtime_clock import current_utc_time
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileHistoricalReplayUniverseStore,
    FileRunLedgerStore,
    FileRunManifestStore,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a full historical-run universe closure artifact from the local "
            "retained corpus plus one or more authoritative external universe packs."
        )
    )
    parser.add_argument(
        "--external-pack",
        action="append",
        default=[],
        help="Path to a JSON pack with authoritative non-local historical run records.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Persist the universe closure artifact under data/output/control/historical_replay_universe.",
    )
    parser.add_argument(
        "--require-universal-claim",
        action="store_true",
        help="Fail when the full-universe universal replay claim remains unclaimed.",
    )
    parser.add_argument(
        "--require-durable-evidence-coverage",
        action="store_true",
        help="Fail when durable evidence coverage for the full historical universe remains unclaimed.",
    )
    return parser.parse_args()


def _load_external_records(
    paths: list[str],
) -> tuple[HistoricalReplayUniverseExternalRecord, ...]:
    records: list[HistoricalReplayUniverseExternalRecord] = []
    for raw_path in paths:
        from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

        path = resolve_output_path(Path(raw_path), root=REPO_ROOT)
        payload = json.loads(path.read_text(encoding="utf-8"))
        pack_ref = str(payload.get("pack_id") or path.name)
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise ValueError(
                f"External universe pack {path} must contain a records list"
            )
        for item in raw_records:
            if not isinstance(item, dict):
                raise ValueError(
                    f"External universe pack {path} contains a non-object record"
                )
            records.append(
                HistoricalReplayUniverseExternalRecord(
                    manifest_id=str(item["manifest_id"]).strip(),
                    run_id=str(item["run_id"]).strip(),
                    pipeline_name=str(item["pipeline_name"]).strip(),
                    provider=str(item["provider"]).strip(),
                    entity=str(item["entity"]).strip(),
                    execution_context=str(item["execution_context"]).strip(),
                    certification_status=str(item["certification_status"]).strip(),
                    replay_occurrence_kind=str(item["replay_occurrence_kind"]).strip(),
                    blocking_reasons=tuple(
                        str(value).strip()
                        for value in item.get("blocking_reasons", [])
                        if str(value).strip()
                    ),
                    evidence_residency=(
                        str(item.get("evidence_residency") or "archived").strip()
                    ),
                    durable_evidence_coverage=bool(
                        item.get("durable_evidence_coverage", False)
                    ),
                    source_pack_ref=pack_ref,
                )
            )
    return tuple(records)


def _has_required_universal_exact_replay_claim(report: object) -> bool:
    """Return whether the report may back universal exact-replay wording."""
    gate = getattr(report, "governed_full_corpus_gate", {})
    if not isinstance(gate, dict):
        return False
    return bool(gate.get("satisfied", False))


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
            entry_id_factory=lambda: create_runtime_occurrence_id(
                "historical_replay_certification_ledger_entry"
            ),
        ),
    )
    universe_service = HistoricalReplayUniverseService(
        corpus_service=corpus_service,
        now_factory=current_utc_time,
    )
    external_records = _load_external_records(args.external_pack)
    report = universe_service.build_universe_closure_report(
        external_records=external_records
    )

    artifact_path: str | None = None
    if args.write_report:
        store = FileHistoricalReplayUniverseStore(
            base_path=output_root / "historical_replay_universe"
        )
        artifact_path = str(store.save(report))

    payload = {
        "report_id": report.report_id,
        "artifact_path": artifact_path,
        "inventory_summary": {
            "manifest_count": report.inventory.manifest_count,
            "unresolved_count": report.inventory.unresolved_count,
            "durable_coverage_gap_count": report.inventory.durable_coverage_gap_count,
            "local_retained_count": report.inventory.local_retained_count,
            "external_archived_count": report.inventory.external_archived_count,
        },
        "universal_claim": report.universal_claim,
        "durable_evidence_coverage_claim": report.durable_evidence_coverage_claim,
        "governed_full_corpus_gate": report.governed_full_corpus_gate,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_universal_claim and not _has_required_universal_exact_replay_claim(
        report
    ):
        return 1
    if args.require_durable_evidence_coverage and not bool(
        report.durable_evidence_coverage_claim.get("claimed", False)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
