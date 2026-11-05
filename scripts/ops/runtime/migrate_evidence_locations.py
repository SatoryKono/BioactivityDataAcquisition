"""
Governed migration command for registering saved runs.
Implements RF-006: Register saved runs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from bioetl.application.services.evidence_location.registration import (
    EvidenceLocationRegistrationService,
)
from bioetl.application.services.evidence_location.registration_models import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationVerifyOutcome,
)
from bioetl.application.services.run_reports import DEFAULT_REPORT_ROOT
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    RunEvidenceLocation,
    build_run_evidence_location,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from scripts.engineering.common.repo_paths import (
    REPO_ROOT,
    confined_io_path,
    read_text_confined,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_REJECT_CODES = frozenset(
    {
        "conflict",
        "invalid",
        "error",
        "binding_mismatch",
        "location_invalid",
    }
)
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


def _request_from_location(
    location: RunEvidenceLocation,
) -> EvidenceLocationRegisterRequest:
    """Build a register/verify request from already-normalized locator fields."""
    return EvidenceLocationRegisterRequest(
        kind=location.kind,
        owner=location.owner,
        run_id=location.run_id,
        runtime_source_id=location.runtime_source_id,
        relative_data_root=location.relative_data_root,
        root_alias=location.root_alias,
        workflow_run_id=location.workflow_run_id,
    )


def _empty_stats() -> dict[str, int]:
    return {
        "registered": 0,
        "already_identical": 0,
        "conflict": 0,
        "invalid": 0,
        "error": 0,
        "binding_mismatch": 0,
        "location_invalid": 0,
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


def _validated_location(
    target: MigrationTarget,
) -> RunEvidenceLocation | EvidenceLocationRegistrationOutcome:
    """Build the same normalized locator registration uses, or invalid."""
    try:
        return build_run_evidence_location(
            kind=target.kind,
            owner=target.owner,
            run_id=target.run_id,
            runtime_source_id=target.runtime_source_id,
            root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
            relative_data_root=target.relative_data_root,
            workflow_run_id=target.workflow_run_id,
        )
    except EvidenceLocationInvalidError as exc:
        return EvidenceLocationRegistrationOutcome(code="invalid", detail=str(exc))


def _ownership_key(location: RunEvidenceLocation) -> tuple[str, str, str]:
    return (location.kind.value, location.owner, location.run_id)


def _runtime_source_from_mapping(payload: Mapping[str, object]) -> str | None:
    raw = payload.get("runtime_source_id")
    if raw is None:
        return None
    text = str(raw).strip().lower()
    return text or None


def _invalid_location(detail: str) -> EvidenceLocationRegistrationOutcome:
    return EvidenceLocationRegistrationOutcome(code="location_invalid", detail=detail)


def _resolve_source_data_root(
    location: RunEvidenceLocation,
    *,
    alias_base: Path,
) -> Path | EvidenceLocationRegistrationOutcome:
    registry = default_evidence_root_alias_registry(dashboard_data_root=alias_base)
    try:
        candidate = registry.resolve_data_root(
            root_alias=location.root_alias,
            relative_data_root=location.relative_data_root,
        )
        data_root = assert_path_within_trusted_base(
            candidate,
            trusted_base=alias_base,
            field_name="relative_data_root",
        )
    except EvidenceLocationInvalidError as exc:
        return _invalid_location(str(exc))
    if not data_root.is_dir():
        return _invalid_location("source_data_root_missing")
    return data_root


def _parse_migration_run_id(
    run_id: str,
) -> RunID | EvidenceLocationRegistrationOutcome:
    try:
        return RunID(UUID(str(run_id)))
    except ValueError:
        return _invalid_location("run_id_not_uuid")


def _owner_mismatch(
    expected: str, found: object
) -> EvidenceLocationRegistrationOutcome:
    return EvidenceLocationRegistrationOutcome(
        code="binding_mismatch",
        detail=f"owner_expected={expected} owner_found={found}",
    )


def _first_runtime_source(*payloads: Mapping[str, object]) -> str | None:
    for payload in payloads:
        source = _runtime_source_from_mapping(payload)
        if source is not None:
            return source
    return None


def _workflow_source_anchor(
    control: Path,
    run_id: RunID,
    location: RunEvidenceLocation,
) -> str | EvidenceLocationRegistrationOutcome:
    found = FileWorkflowManifestStore(
        base_path=control / "workflow_manifest"
    ).get_by_run_id(run_id)
    if found is None:
        return _invalid_location("source_run_missing")
    if str(found.workflow_name).strip() != location.owner:
        return _owner_mismatch(location.owner, found.workflow_name)
    source = _first_runtime_source(found.launch_context, found.defaults)
    if source is None:
        return _invalid_location("runtime_source_anchor_missing")
    return source


def _pipeline_source_anchor(
    control: Path,
    run_id: RunID,
    location: RunEvidenceLocation,
) -> str | EvidenceLocationRegistrationOutcome:
    found = FileRunManifestStore(base_path=control / "run_manifest").get_by_run_id(
        run_id
    )
    if found is None:
        return _invalid_location("source_run_missing")
    if str(found.pipeline_name).strip() != location.owner:
        return _owner_mismatch(location.owner, found.pipeline_name)
    found_workflow = (
        str(found.workflow_run_id).strip() if found.workflow_run_id else None
    )
    if found_workflow != location.workflow_run_id:
        return EvidenceLocationRegistrationOutcome(
            code="binding_mismatch",
            detail=(
                f"workflow_run_id_expected={location.workflow_run_id} "
                f"workflow_run_id_found={found_workflow}"
            ),
        )
    source = _first_runtime_source(found.launch_context, found.runtime_config)
    if source is None:
        return _invalid_location("runtime_source_anchor_missing")
    return source


def _reject_runtime_source_drift(
    location: RunEvidenceLocation,
    anchored_source: str,
) -> EvidenceLocationRegistrationOutcome | None:
    if anchored_source != location.runtime_source_id:
        return EvidenceLocationRegistrationOutcome(
            code="binding_mismatch",
            detail=(
                f"runtime_source_expected={location.runtime_source_id} "
                f"runtime_source_found={anchored_source}"
            ),
        )
    return None


def _preflight_source_anchors(
    location: RunEvidenceLocation,
    *,
    alias_base: Path,
) -> EvidenceLocationRegistrationOutcome | None:
    """Reject targets whose on-disk run anchors do not match the locator claim.

    Checks (dry-run and apply):
    - ``relative_data_root`` resolves under the trusted alias base and exists
    - the run_id has a control-plane manifest under that data root
    - manifest owner matches the locator owner
    - manifest-recorded ``runtime_source_id`` matches the locator claim
    """
    data_root = _resolve_source_data_root(location, alias_base=alias_base)
    if isinstance(data_root, EvidenceLocationRegistrationOutcome):
        return data_root
    run_id = _parse_migration_run_id(location.run_id)
    if isinstance(run_id, EvidenceLocationRegistrationOutcome):
        return run_id
    control = data_root / "output" / "control"
    if location.kind is EvidenceLocationKind.WORKFLOW:
        anchored = _workflow_source_anchor(control, run_id, location)
    else:
        anchored = _pipeline_source_anchor(control, run_id, location)
    if isinstance(anchored, EvidenceLocationRegistrationOutcome):
        return anchored
    return _reject_runtime_source_drift(location, anchored)


def _classify_dry_run(
    service: EvidenceLocationRegistrationService,
    *,
    planned: dict[tuple[str, str, str], str],
    location: RunEvidenceLocation,
) -> EvidenceLocationRegistrationOutcome:
    """Validate binding + existing/planned catalog without publishing a locator."""
    key = _ownership_key(location)
    fingerprint = location.revision
    prior = planned.get(key)
    if prior is not None:
        if prior == fingerprint:
            return EvidenceLocationRegistrationOutcome(code="already_identical")
        return EvidenceLocationRegistrationOutcome(
            code="conflict",
            detail="intra_batch_binding_conflict",
        )

    verified: EvidenceLocationVerifyOutcome = service.verify(
        _request_from_location(location)
    )
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
        if verified.code in {"binding_mismatch", "location_invalid"}:
            mapped = verified.code
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
    *,
    data_root: Path,
    dry_run: bool = True,
) -> dict[str, int]:
    """Execute the migration plan with source-anchor preflight."""
    alias_base = Path(data_root).resolve(strict=False)
    store = FileEvidenceLocationStore(report_root=report_root)
    service = EvidenceLocationRegistrationService(locations=store)
    stats = _empty_stats()
    planned: dict[tuple[str, str, str], str] = {}

    for target in targets:
        validated = _validated_location(target)
        if isinstance(validated, EvidenceLocationRegistrationOutcome):
            _record_outcome(
                stats,
                target=target,
                code=validated.code,
                detail=validated.detail,
                planned=dry_run,
            )
            continue

        preflight = _preflight_source_anchors(validated, alias_base=alias_base)
        if preflight is not None:
            _record_outcome(
                stats,
                target=target,
                code=preflight.code,
                detail=preflight.detail,
                planned=dry_run,
            )
            continue

        request = _request_from_location(validated)
        if dry_run:
            outcome = _classify_dry_run(
                service,
                planned=planned,
                location=validated,
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
        "--data-root",
        type=Path,
        required=True,
        help=(
            "Trusted dashboard_data alias base used to re-check source run "
            "anchors before dry-run/apply registration"
        ),
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
        data_root = confined_io_path(args.data_root, root=REPO_ROOT)
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
        data_root=data_root,
        dry_run=not args.apply,
    )

    if not args.apply:
        logger.info("Dry-run complete. Stats: %s", stats)
        return 1 if _has_rejects(stats) else 0

    logger.info("Apply complete. Stats: %s", stats)
    return 1 if _has_rejects(stats) else 0


if __name__ == "__main__":
    sys.exit(main())
