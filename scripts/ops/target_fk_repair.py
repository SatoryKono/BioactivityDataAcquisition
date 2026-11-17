"""Prepare isolated additive V30 target FK repair candidates; never promote."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from uuid import UUID

from bioetl.composition.bootstrap.runtime.composite_control_plane_bundle import (
    TargetFKRepairRequest,
    prepare_target_fk_repair,
)


def main(argv: list[str] | None = None) -> int:
    """Require explicit source, new destination, and reproducible run context."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--started-at", required=True, type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    manifest = asyncio.run(
        prepare_target_fk_repair(
            TargetFKRepairRequest(
                repo_root=args.repo_root,
                source_directory=args.source_directory,
                output_directory=args.output_directory,
                run_id=args.run_id,
                started_at=args.started_at,
            )
        )
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
