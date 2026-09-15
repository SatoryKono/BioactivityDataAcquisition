"""Create or verify an isolated local archive with a verified restore copy."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy, RunManifest
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
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
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
    store = FileArchiveStore(args.data_root, args.archive_root)
    try:
        if not args.verify_only:
            store.create(manifest=manifest, plan=plan)
        verified, reason = store.verify(manifest=manifest, plan=plan)
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
