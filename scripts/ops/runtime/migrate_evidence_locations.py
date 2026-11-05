"""
Governed migration command for registering saved runs.
Implements RF-006: Register saved runs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bioetl.application.services.evidence_location.registration import (
    EvidenceLocationRegistrationService,
)
from bioetl.application.services.evidence_location.registration_models import (
    EvidenceLocationRegisterRequest,
)
from bioetl.application.services.run_reports import DEFAULT_REPORT_ROOT
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)
from scripts.engineering.common.repo_paths import (
    REPO_ROOT,
    confined_io_path,
    read_text_confined,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_REJECT_CODES = frozenset({"conflict", "invalid", "error"})


@dataclass
class MigrationTarget:
    kind: EvidenceLocationKind
    owner: str
    run_id: str
    runtime_source_id: str
    relative_data_root: str
    workflow_run_id: str | None = None


def read_target_list(
    path: Path | str,
    *,
    root: Path | None = None,
) -> list[MigrationTarget]:
    """Read a machine-local list of targets under a confined root."""
    payload = read_text_confined(path, root=root or REPO_ROOT)
    data = json.loads(payload)
    targets: list[MigrationTarget] = []
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

    stats = {
        "registered": 0,
        "already_identical": 0,
        "conflict": 0,
        "invalid": 0,
        "error": 0,
    }

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
            logger.info(
                "PLAN: Would register %s %s %s",
                target.kind.value,
                target.owner,
                target.run_id,
            )
            continue

        outcome = service.register(request)
        stats[outcome.code] = stats.get(outcome.code, 0) + 1

        if outcome.code in ("registered", "already_identical"):
            logger.info(
                "PASS: %s %s %s -> %s",
                target.kind.value,
                target.owner,
                target.run_id,
                outcome.code,
            )
        else:
            logger.error(
                "FAIL: %s %s %s -> %s: %s",
                target.kind.value,
                target.owner,
                target.run_id,
                outcome.code,
                outcome.detail,
            )

    return stats


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate historical evidence locations.",
    )
    parser.add_argument(
        "--targets",
        type=Path,
        required=True,
        help="Path to JSON file containing explicit list of targets",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
        help="Path to the reports root directory",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes instead of dry-run",
    )

    args = parser.parse_args(argv)

    try:
        targets_path = confined_io_path(args.targets, root=REPO_ROOT)
        report_root = confined_io_path(args.report_root, root=REPO_ROOT)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if not targets_path.is_file():
        logger.error("Targets file not found: %s", targets_path)
        return 1

    try:
        targets = read_target_list(targets_path, root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Failed to parse targets: %s", exc)
        return 1

    logger.info("Loaded %s targets.", len(targets))

    stats = execute_migration(
        targets=targets,
        report_root=report_root,
        dry_run=not args.apply,
    )

    if not args.apply:
        logger.info("Dry-run complete.")
        return 0

    logger.info("Apply complete. Stats: %s", stats)
    if any(stats.get(code, 0) for code in _REJECT_CODES):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
