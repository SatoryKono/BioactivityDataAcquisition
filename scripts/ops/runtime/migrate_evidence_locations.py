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
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationVerifyOutcome,
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
_VERIFY_REJECT_CODES = frozenset(
    {
        "invalid",
        "identity_conflict",
        "binding_mismatch",
        "location_invalid",
    }
)


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
    if not isinstance(data, dict):
        raise ValueError("targets JSON must be an object")
    if "targets" not in data:
        raise ValueError("targets JSON must contain a 'targets' array")
    raw_targets = data["targets"]
    if not isinstance(raw_targets, list):
        raise ValueError("'targets' must be a JSON array")

    targets: list[MigrationTarget] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            raise ValueError("each target must be a JSON object")
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


def _request_for(target: MigrationTarget) -> EvidenceLocationRegisterRequest:
    return EvidenceLocationRegisterRequest(
        kind=target.kind,
        owner=target.owner,
        run_id=target.run_id,
        runtime_source_id=target.runtime_source_id,
        relative_data_root=target.relative_data_root,
        root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
        workflow_run_id=target.workflow_run_id,
    )


def _empty_stats() -> dict[str, int]:
    return {
        "registered": 0,
        "already_identical": 0,
        "conflict": 0,
        "invalid": 0,
        "error": 0,
    }


def _record_outcome(
    stats: dict[str, int],
    *,
    target: MigrationTarget,
    code: str,
    detail: str | None,
    planned: bool,
) -> None:
    stats[code] = stats.get(code, 0) + 1
    if planned:
        prefix = "PLAN"
    elif code in {"registered", "already_identical"}:
        prefix = "PASS"
    else:
        prefix = "FAIL"
    message = f"{prefix}: {target.kind.value} {target.owner} {target.run_id} -> {code}"
    if detail:
        message = f"{message}: {detail}"
    if code in {"registered", "already_identical"} or (
        planned and code not in _REJECT_CODES
    ):
        logger.info("%s", message)
    else:
        logger.error("%s", message)


def _ownership_key(target: MigrationTarget) -> tuple[str, str, str]:
    return (target.kind.value, target.owner, target.run_id)


def _binding_fingerprint(target: MigrationTarget) -> tuple[str, str, str | None]:
    return (
        target.runtime_source_id,
        target.relative_data_root,
        target.workflow_run_id,
    )


def _classify_dry_run(
    service: EvidenceLocationRegistrationService,
    request: EvidenceLocationRegisterRequest,
    *,
    planned: dict[tuple[str, str, str], tuple[str, str, str | None]],
    target: MigrationTarget,
) -> EvidenceLocationRegistrationOutcome:
    """Validate binding + existing/planned catalog without publishing a locator."""
    key = _ownership_key(target)
    fingerprint = _binding_fingerprint(target)
    prior = planned.get(key)
    if prior is not None:
        if prior == fingerprint:
            return EvidenceLocationRegistrationOutcome(code="already_identical")
        return EvidenceLocationRegistrationOutcome(
            code="conflict",
            detail="intra_batch_binding_conflict",
        )

    verified: EvidenceLocationVerifyOutcome = service.verify(request)
    if verified.code == "location_missing":
        planned[key] = fingerprint
        return EvidenceLocationRegistrationOutcome(
            code="registered", detail="would_register"
        )
    if verified.code == "ok":
        planned[key] = fingerprint
        return EvidenceLocationRegistrationOutcome(code="already_identical")
    if verified.code in _VERIFY_REJECT_CODES:
        mapped = "invalid" if verified.code == "invalid" else "conflict"
        return EvidenceLocationRegistrationOutcome(
            code=mapped,
            detail=verified.detail or verified.code,
        )
    return EvidenceLocationRegistrationOutcome(
        code="error",
        detail=verified.detail or verified.code,
    )


def execute_migration(
    targets: Sequence[MigrationTarget],
    report_root: Path,
    dry_run: bool = True,
) -> dict[str, int]:
    """Execute the migration plan."""
    store = FileEvidenceLocationStore(report_root=report_root)
    service = EvidenceLocationRegistrationService(locations=store)
    stats = _empty_stats()
    planned: dict[tuple[str, str, str], tuple[str, str, str | None]] = {}

    for target in targets:
        request = _request_for(target)
        if dry_run:
            outcome = _classify_dry_run(
                service,
                request,
                planned=planned,
                target=target,
            )
            _record_outcome(
                stats,
                target=target,
                code=outcome.code,
                detail=outcome.detail,
                planned=True,
            )
            continue

        outcome = service.register(request)
        _record_outcome(
            stats,
            target=target,
            code=outcome.code,
            detail=outcome.detail,
            planned=False,
        )

    return stats


def _has_rejects(stats: dict[str, int]) -> bool:
    return any(stats.get(code, 0) for code in _REJECT_CODES)


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

    if not targets:
        logger.error("Targets list is empty.")
        return 1

    logger.info("Loaded %s targets.", len(targets))

    stats = execute_migration(
        targets=targets,
        report_root=report_root,
        dry_run=not args.apply,
    )

    if not args.apply:
        logger.info("Dry-run complete. Stats: %s", stats)
        return 1 if _has_rejects(stats) else 0

    logger.info("Apply complete. Stats: %s", stats)
    return 1 if _has_rejects(stats) else 0


if __name__ == "__main__":
    sys.exit(main())
