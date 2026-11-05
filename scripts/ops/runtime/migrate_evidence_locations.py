"""
Governed migration command for registering saved runs.
Implements RF-006: Register saved runs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from collections.abc import Sequence

from bioetl.application.services.evidence_location.registration import (
    EvidenceLocationRegistrationService,
)
from bioetl.application.services.evidence_location.registration_models import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class MigrationTarget:
    kind: EvidenceLocationKind
    owner: str
    run_id: str
    runtime_source_id: str
    relative_data_root: str
    workflow_run_id: str | None = None


def read_target_list(path: Path) -> list[MigrationTarget]:
    """Read a machine-local list of targets."""
    with path.open("r") as f:
        data = json.load(f)
        targets = []
        for item in data.get("targets", []):
            targets.append(
                MigrationTarget(
                    kind=EvidenceLocationKind(item["kind"]),
                    owner=item["owner"],
                    run_id=item["run_id"],
                    runtime_source_id=item["runtime_source_id"],
                    relative_data_root=item["relative_data_root"],
                    workflow_run_id=item.get("workflow_run_id"),
                )
            )
        return targets


def execute_migration(
    targets: Sequence[MigrationTarget],
    report_root: Path,
    dry_run: bool = True,
) -> dict[str, int]:
    """Execute the migration plan."""
    store = FileEvidenceLocationStore(report_root=report_root)
    service = EvidenceLocationRegistrationService(locations=store)

    stats = {"registered": 0, "already_identical": 0, "conflict": 0, "invalid": 0, "error": 0}

    for target in targets:
        request = EvidenceLocationRegisterRequest(
            kind=target.kind,
            owner=target.owner,
            run_id=target.run_id,
            runtime_source_id=target.runtime_source_id,
            relative_data_root=target.relative_data_root,
            root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
            workflow_run_id=target.workflow_run_id,
        )

        if dry_run:
            logger.info(f"PLAN: Would register {target.kind.value} {target.owner} {target.run_id}")
            continue

        outcome = service.register(request)
        stats[outcome.code] = stats.get(outcome.code, 0) + 1

        if outcome.code in ("registered", "already_identical"):
            logger.info(f"PASS: {target.kind.value} {target.owner} {target.run_id} -> {outcome.code}")
        else:
            logger.error(f"FAIL: {target.kind.value} {target.owner} {target.run_id} -> {outcome.code}: {outcome.detail}")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate historical evidence locations.")
    parser.add_argument(
        "--targets",
        type=Path,
        required=True,
        help="Path to JSON file containing explicit list of targets"
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=Path("reports"),
        help="Path to the reports root directory"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes instead of dry-run"
    )

    args = parser.parse_args()

    if not args.targets.exists():
        logger.error(f"Targets file not found: {args.targets}")
        return 1

    try:
        targets = read_target_list(args.targets)
    except Exception as exc:
        logger.error(f"Failed to parse targets: {exc}")
        return 1

    logger.info(f"Loaded {len(targets)} targets.")

    stats = execute_migration(
        targets=targets,
        report_root=args.report_root,
        dry_run=not args.apply,
    )

    if not args.apply:
        logger.info("Dry-run complete.")
    else:
        logger.info(f"Apply complete. Stats: {stats}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
