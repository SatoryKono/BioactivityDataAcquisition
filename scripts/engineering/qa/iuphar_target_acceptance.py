"""Run the approved offline integration acceptance on pinned inputs only."""

from __future__ import annotations

import argparse
from pathlib import Path

from bioetl.infrastructure.adapters.iuphar.snapshot_loader import load_profile
from iuphar_target_class.integration_acceptance import (
    IntegrationAcceptanceRequest,
    run_integration_acceptance,
)
from iuphar_target_class.models import RunProvenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--stage0-manifest", type=Path, required=True)
    parser.add_argument("--expected-labels", type=Path, required=True)
    parser.add_argument("--expected-labels-sha256", required=True)
    parser.add_argument("--pipeline-proof", type=Path)
    parser.add_argument("--pipeline-report", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-started-at", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    profile = load_profile(args.profile, args.profile_sha256, require_acceptance=False)
    if not profile.snapshot.completeness.publishable:
        parser.error("reference acceptance requires a publishable snapshot")
    provenance = RunProvenance(
        profile.snapshot.snapshot.snapshot_id,
        profile.normalization_version,
        profile.rules_version,
        profile.classification_schema_version,
        profile.snapshot.retrieved_at,
        args.run_started_at,
    )
    request = IntegrationAcceptanceRequest(
        args.stage0_manifest,
        args.expected_labels,
        args.expected_labels_sha256,
        profile.snapshot.snapshot_manifest_sha256,
        provenance,
        args.run_id,
        args.pipeline_proof,
        args.pipeline_report,
    )
    receipt = run_integration_acceptance(
        request,
        snapshot=profile.snapshot.snapshot,
        output_dir=args.output_dir,
    )
    print(f"{receipt['status']}: {args.output_dir / 'acceptance.json'}")
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
