#!/usr/bin/env python
"""Register evidence roots from historical manifests and reports (RF-006).

A governed migration script designed to retroactively register historical
workflow and pipeline executions into the run evidence location catalog.
It executes the registration without triggering an actual ETL run.

It supports a dry-run mode (the default) to preview changes and conflicts,
and an --apply mode to commit them to the store.
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from bioetl.application.services.evidence_location import (
    EvidenceLocationRegisterRequest,
)
from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.composition.evidence_location_registration import (
    build_evidence_location_registration_service,
)

logger = logging.getLogger(__name__)


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


def _extract_request(payload: dict[str, object]) -> EvidenceLocationRegisterRequest:
    # Direct evidence location payload
    if "relative_data_root" in payload and "root_alias" in payload:
        return EvidenceLocationRegisterRequest(
            kind=EvidenceLocationKind(str(payload.get("kind"))),
            owner=str(payload.get("owner")),
            run_id=str(payload.get("run_id")),
            runtime_source_id=str(payload.get("runtime_source_id")),
            relative_data_root=str(payload.get("relative_data_root")),
            root_alias=str(payload.get("root_alias", "default")),
            workflow_run_id=str(payload.get("workflow_run_id"))
            if payload.get("workflow_run_id")
            else None,
        )

    # We can also attempt to read from 'identity' block of pipeline or workflow manifests/reports.
    # We will assume a minimal standardized format that contains what we need.
    if "identity" in payload and isinstance(payload["identity"], dict):
        identity = payload["identity"]
        if "workflow_name" in identity:
            kind = EvidenceLocationKind.WORKFLOW
            owner = str(identity.get("workflow_name"))
        else:
            kind = EvidenceLocationKind.PIPELINE
            owner = str(identity.get("pipeline_name", "unknown"))

        run_id = str(identity.get("run_id"))
        runtime_source_id = str(identity.get("runtime_source_id", ""))
        relative_data_root = str(payload.get("relative_data_root", "."))
        root_alias = str(payload.get("root_alias", "default"))
        workflow_run_id = str(identity.get("workflow_run_id")) if identity.get("workflow_run_id") else None

        return EvidenceLocationRegisterRequest(
            kind=kind,
            owner=owner,
            run_id=run_id,
            runtime_source_id=runtime_source_id,
            relative_data_root=relative_data_root,
            root_alias=root_alias,
            workflow_run_id=workflow_run_id,
        )

    raise ValueError("Payload missing required evidence location fields.")


def main(args: Sequence[str] | None = None) -> int:
    parsed = parse_args(args)
    settings = Settings()
    service, _ = build_evidence_location_registration_service(settings)

    results: dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIPPED": 0, "NOT_RUN": 0}

    for input_path in parsed.inputs:
        path = Path(input_path)
        logger.info("Processing %s", path)
        if not path.is_file():
            logger.error("File not found: %s", path)
            results["FAIL"] += 1
            continue

        try:
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            request = _extract_request(payload)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read JSON %s: %s", path, e)
            results["FAIL"] += 1
            continue
        except ValueError as e:
            logger.error("Invalid payload in %s: %s", path, e)
            results["FAIL"] += 1
            continue

        if not parsed.apply:
            # Plan mode uses the verification lookup to identify conflicts and expected outcomes
            lookup = service.locations.lookup(
                kind=request.kind,
                owner=request.owner,
                run_id=request.run_id,
                expected_runtime_source_id=request.runtime_source_id,
            )
            if lookup.code.value == "found":
                logger.info("[DRY-RUN] Will be identical/already registered for %s", path)
                results["PASS"] += 1
            elif lookup.code.value == "identity_conflict":
                logger.warning("[DRY-RUN] Will conflict for %s", path)
                results["SKIPPED"] += 1
            else:
                logger.info("[DRY-RUN] Will register new location for %s", path)
                results["NOT_RUN"] += 1
        else:
            outcome = service.register(request)
            if outcome.code in ("registered", "already_identical"):
                logger.info("[APPLY] Registered %s", path)
                results["PASS"] += 1
            elif outcome.code == "conflict":
                logger.warning("[APPLY] Conflict for %s: %s", path, outcome.detail)
                results["SKIPPED"] += 1
            else:
                logger.error("[APPLY] Failed to register %s: %s", path, outcome.detail)
                results["FAIL"] += 1

    logger.info("Registration receipt: %s", results)

    if results["FAIL"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
