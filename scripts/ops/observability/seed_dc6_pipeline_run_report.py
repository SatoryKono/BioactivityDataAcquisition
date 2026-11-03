#!/usr/bin/env python3
"""Materialize a durable pipeline_run_report for the DC-6 chembl_assay seed.

Machine-local helper for cloud/DESKTOP live acceptance (L7 report_state,
Overview 9460 PRR). Does not commit artifacts, touch ``.env``, or start Docker.

Default identity matches DC-6 C-seed:
  pipeline=chembl_assay
  run_id=00000000-0000-4000-8000-000000000942
  workflow_id=chembl_baseline

Usage::

    python -m scripts.ops.observability.seed_dc6_pipeline_run_report
    python -m scripts.ops.observability.seed_dc6_pipeline_run_report --root reports/run-reports
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = ROOT / "tests/fixtures/reports/chembl_assay_backfill_run_report_golden.json"

DEFAULT_PIPELINE = "chembl_assay"
DEFAULT_RUN_ID = "00000000-0000-4000-8000-000000000942"
DEFAULT_WORKFLOW_ID = "chembl_baseline"
DEFAULT_WORKFLOW_RUN_ID = "00000000-0000-4000-8000-000000000941"
DEFAULT_MANIFEST_ID = "seed-phase0-dc6-chembl-assay-942"


def _build_payload(
    *,
    pipeline: str,
    run_id: str,
    workflow_id: str,
    workflow_run_id: str,
    manifest_id: str,
) -> dict[str, object]:
    payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "pipeline_run_report_v1":
        raise SystemExit(
            f"unexpected golden schema_version: {payload.get('schema_version')}"
        )
    identity = dict(payload.get("identity") or {})
    identity.update(
        {
            "run_id": run_id,
            "pipeline_name": pipeline,
            "provider": "chembl",
            "entity": "assay",
            "run_type": "backfill",
            "status": "success",
            "workflow_id": workflow_id,
            "workflow_run_id": workflow_run_id,
            "started_at": "2026-08-27T08:46:00+00:00",
            "completed_at": "2026-08-27T08:47:00+00:00",
            "duration_seconds": 60.0,
            "manifest_id": manifest_id,
        }
    )
    payload["identity"] = identity
    payload["artifacts"] = []
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT / "reports/run-reports",
        help="Report root (default: reports/run-reports)",
    )
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--workflow-run-id", default=DEFAULT_WORKFLOW_RUN_ID)
    parser.add_argument("--manifest-id", default=DEFAULT_MANIFEST_ID)
    args = parser.parse_args(argv)

    if not GOLDEN.is_file():
        raise SystemExit(f"missing golden fixture: {GOLDEN}")

    payload = _build_payload(
        pipeline=args.pipeline,
        run_id=args.run_id,
        workflow_id=args.workflow_id,
        workflow_run_id=args.workflow_run_id,
        manifest_id=args.manifest_id,
    )
    out_dir = args.root / "pipeline" / args.pipeline / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pipeline-run-report.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    latest = args.root / "pipeline" / args.pipeline / "_latest.json"
    latest.write_text(
        json.dumps(
            {
                "kind": "pipeline_run_report",
                "pipeline_name": args.pipeline,
                "run_id": args.run_id,
                "status": "success",
                "completed_at": payload["identity"]["completed_at"],  # type: ignore[index]
                "json_path": str(json_path.as_posix()),
                "markdown_path": None,
                "json_sha256": None,
                "markdown_sha256": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {json_path}")
    print(f"wrote {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
