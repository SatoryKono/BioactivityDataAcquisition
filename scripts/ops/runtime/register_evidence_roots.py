#!/usr/bin/env python
"""Register evidence roots from historical manifests and reports (RF-006).

A governed migration script that registers historical workflow and pipeline
executions into the run evidence location catalog without starting ETL.

Dry-run is the default. ``--apply`` commits registrations through
``EvidenceLocationRegistrationService.register``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from bioetl.application.services.evidence_location import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationService,
)
from bioetl.composition.evidence_location_registration import (
    build_evidence_location_registration_service,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
)
from bioetl.infrastructure.config.settings_api import Settings
from scripts.engineering.common.repo_paths import read_text_confined

logger = logging.getLogger(__name__)

_RECEIPT_KEYS = ("PASS", "FAIL", "SKIPPED", "NOT_RUN")


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register evidence locations for historical runs."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Paths to JSON manifests or summaries containing execution details.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute registration (default is plan/dry-run mode).",
    )
    return parser.parse_args(args)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _require_object(payload: object) -> Mapping[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object.")
    return payload


def _required_text(source: Mapping[str, object], key: str) -> str:
    value = source.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"Payload missing required field {key}.")


def _root_alias(source: Mapping[str, object]) -> str:
    if "root_alias" not in source:
        return DEFAULT_EVIDENCE_ROOT_ALIAS
    return _required_text(source, "root_alias")


def _request_from_direct(
    payload: Mapping[str, object],
) -> EvidenceLocationRegisterRequest:
    return EvidenceLocationRegisterRequest(
        kind=EvidenceLocationKind(_required_text(payload, "kind")),
        owner=_required_text(payload, "owner"),
        run_id=_required_text(payload, "run_id"),
        runtime_source_id=_required_text(payload, "runtime_source_id"),
        relative_data_root=_required_text(payload, "relative_data_root"),
        root_alias=_root_alias(payload),
        workflow_run_id=_optional_text(payload.get("workflow_run_id")),
    )


def _request_from_identity(
    payload: Mapping[str, object],
) -> EvidenceLocationRegisterRequest:
    identity = payload["identity"]
    if not isinstance(identity, dict):
        raise ValueError("Payload missing required evidence location fields.")
    relative_data_root = _required_text(payload, "relative_data_root")
    runtime_source_id = _required_text(identity, "runtime_source_id")
    if "workflow_name" in identity:
        kind = EvidenceLocationKind.WORKFLOW
        owner = _required_text(identity, "workflow_name")
        run_id = _required_text(identity, "workflow_run_id")
        workflow_run_id = None
    else:
        kind = EvidenceLocationKind.PIPELINE
        owner = _required_text(identity, "pipeline_name")
        run_id = _required_text(identity, "run_id")
        workflow_run_id = _optional_text(identity.get("workflow_run_id"))
    return EvidenceLocationRegisterRequest(
        kind=kind,
        owner=owner,
        run_id=run_id,
        runtime_source_id=runtime_source_id,
        relative_data_root=relative_data_root,
        root_alias=_root_alias(payload),
        workflow_run_id=workflow_run_id,
    )


def _extract_request(payload: Mapping[str, object]) -> EvidenceLocationRegisterRequest:
    if "relative_data_root" in payload and "root_alias" in payload:
        return _request_from_direct(payload)
    if "identity" in payload:
        return _request_from_identity(payload)
    raise ValueError("Payload missing required evidence location fields.")


def _load_manifest(path: Path) -> Mapping[str, object]:
    """Read one CLI manifest after path confinement (pythonsecurity:S8707)."""
    raw = read_text_confined(path, allow_external_absolute=True)
    return _require_object(json.loads(raw))


def _plan(
    service: EvidenceLocationRegistrationService,
    request: EvidenceLocationRegisterRequest,
    path: Path,
) -> str:
    outcome = service.verify(request)
    if outcome.code == "ok":
        logger.info("[DRY-RUN] Will be identical/already registered for %s", path)
        return "PASS"
    if outcome.code in {"binding_mismatch", "identity_conflict"}:
        logger.warning("[DRY-RUN] Will conflict for %s: %s", path, outcome.detail)
        return "SKIPPED"
    if outcome.code == "location_missing":
        logger.info("[DRY-RUN] Will register new location for %s", path)
        return "NOT_RUN"
    logger.error(
        "[DRY-RUN] Cannot register %s: %s", path, outcome.detail or outcome.code
    )
    return "FAIL"


def _apply(
    service: EvidenceLocationRegistrationService,
    request: EvidenceLocationRegisterRequest,
    path: Path,
) -> str:
    outcome = service.register(request)
    if outcome.code in {"registered", "already_identical"}:
        logger.info("[APPLY] Registered %s", path)
        return "PASS"
    if outcome.code == "conflict":
        logger.warning("[APPLY] Conflict for %s: %s", path, outcome.detail)
        return "SKIPPED"
    logger.error("[APPLY] Failed to register %s: %s", path, outcome.detail)
    return "FAIL"


def _process_one(
    service: EvidenceLocationRegistrationService,
    *,
    apply: bool,
    path: Path,
    results: dict[str, int],
) -> None:
    logger.info("Processing %s", path)
    try:
        request = _extract_request(_load_manifest(path))
    except FileNotFoundError:
        logger.error("File not found: %s", path)
        results["FAIL"] += 1
        return
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        logger.error("Invalid payload in %s: %s", path, exc)
        results["FAIL"] += 1
        return
    bucket = _apply(service, request, path) if apply else _plan(service, request, path)
    logger.info(
        "entry path=%s kind=%s owner=%s run_id=%s outcome=%s",
        path,
        getattr(request.kind, "value", request.kind),
        request.owner,
        request.run_id,
        bucket,
    )
    results[bucket] += 1


def main(args: Sequence[str] | None = None) -> int:
    parsed = parse_args(args)
    settings = Settings()
    service, _ = build_evidence_location_registration_service(settings)
    results = dict.fromkeys(_RECEIPT_KEYS, 0)
    for input_path in parsed.inputs:
        _process_one(
            service,
            apply=bool(parsed.apply),
            path=Path(input_path),
            results=results,
        )
    logger.info("Registration receipt: %s", results)
    if results["FAIL"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
