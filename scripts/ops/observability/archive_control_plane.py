"""Create or verify an isolated local archive with a verified restore copy."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy, RunManifest
from bioetl.composition.archive_assessment import refresh_archived_assessment
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)


def main(argv: list[str] | None = None) -> int:
    """Archive only resolved selected-run evidence; preserve source and existing packs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report-root", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--refresh-assessment", action="store_true")
    args = parser.parse_args(argv)
    if args.refresh_assessment and (args.verify_only or args.report_root is None):
        parser.error(
            "--refresh-assessment requires --report-root and cannot use --verify-only"
        )
    manifest = RunManifest.from_dict(
        json.loads(args.manifest.read_text(encoding="utf-8"))
    )
    planner = FileControlPlaneArtifactLifecycleStore(
        base_path=args.data_root.resolve() / "output" / "control"
    )
    plan = planner.plan_for_manifest(
        ControlPlaneArtifactLifecyclePolicy(retention_days=90, now=datetime.now(UTC)),
        manifest=manifest,
    )
    store = FileArchiveStore(args.data_root, args.archive_root, args.report_root)
    try:
        verified, reason = store.verify(manifest=manifest, plan=plan)
        if not args.verify_only and reason == "archive_evidence_not_recorded":
            store.create(manifest=manifest, plan=plan)
        verified, reason = store.verify(manifest=manifest, plan=plan)
        if verified is True and args.refresh_assessment:
            verified, reason = refresh_archived_assessment(
                data_root=args.data_root.resolve(),
                archive_root=args.archive_root.resolve(),
                report_root=args.report_root.resolve(),
                manifest=manifest,
                plan=plan,
                observed_at=datetime.now(UTC),
            )
    except (OSError, ValueError) as exc:
        print(json.dumps({"verified": False, "error_type": type(exc).__name__}))
        return 1
    print(
        json.dumps(
            {
                "verified": verified,
                "reason": reason,
                "artifact_refs": len(plan.artifacts),
                "files": len({artifact.path for artifact in plan.artifacts}),
            }
        )
    )
    return 0 if verified is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
