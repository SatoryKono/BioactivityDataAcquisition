"""Prepare, promote, roll back, or report main-contour classification acceptance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bioetl.composition.bootstrap.cli.metrics import bind_target_deployment
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.storage.target_candidates import (
    TargetCandidateBuildRequest,
    build_target_candidates,
    freeze_target_inputs,
)
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationJournal,
    TargetMigrationPaths,
    migration_status,
    prepare_target_migration,
    promote_target_migration,
    resolve_target_migration_transition,
    rollback_target_migration,
)
from scripts.engineering.common.repo_paths import confined_io_path
from scripts.ops.target_classification_contour import (
    REPO_ROOT,
    ContourEvidenceError,
    ContourMeasurementPaths,
    apply_measurements,
    evaluate_main_contour,
    inspect_repository,
    parse_evidence,
    write_contour_report,
)


_RESTORATION_ACTIONS = frozenset({"freeze-inputs", "prepare"})


def _load_plan(
    parser: argparse.ArgumentParser, plan: Path, *, action: str
) -> tuple[Path, TargetMigrationPaths, dict[str, Any], str, str]:
    active_root = resolve_configs_root().resolve().parent
    document = json.loads(confined_io_path(plan, root=active_root).read_bytes())
    source_profile, destination_profile = _plan_profiles(parser, document)
    if action == "promote" and document.get("cutover_authority") != "RF-013":
        parser.error(
            "canonical table promotion is reserved for RF-013; "
            "plan has no cutover authority"
        )
    paths = TargetMigrationPaths(
        **{key: Path(value) for key, value in document["paths"].items()}
    )
    if paths.workspace.resolve() != active_root:
        parser.error("plan workspace must be the active repository/configs root")
    return active_root, paths, document, source_profile, destination_profile


def _restoration_manifest(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    active_root: Path,
) -> Path | None:
    manifest = args.restoration_manifest
    if manifest is None:
        return None
    if args.action not in _RESTORATION_ACTIONS:
        parser.error("--restoration-manifest applies to freeze-inputs and prepare")
    return confined_io_path(manifest, root=active_root)


def _freeze_inputs(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    paths: TargetMigrationPaths,
    fields: tuple[str, ...],
    restoration: Path | None,
) -> None:
    if args.output is None:
        parser.error("freeze-inputs requires --output NEW_MANIFEST_PATH")
    freeze_target_inputs(
        paths,
        legacy_include_fields=fields,
        output=args.output,
        restoration_manifest=restoration,
    )
    print(json.dumps({"status": "frozen", "manifest": str(args.output)}))


def _build_candidates(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    paths: TargetMigrationPaths,
    fields: tuple[str, ...],
    restoration: Path | None,
) -> None:
    del restoration
    if not all(
        (
            args.input_manifest,
            args.input_manifest_sha256,
            args.output,
            args.run_id,
            args.run_started_at,
        )
    ):
        parser.error(
            "build-candidates requires pinned input manifest, output directory and run identity"
        )
    build_target_candidates(
        TargetCandidateBuildRequest(
            paths,
            args.input_manifest,
            args.input_manifest_sha256,
            args.output,
            fields,
            args.run_id,
            args.run_started_at,
            bind_target_deployment(paths),
        )
    )
    print(json.dumps({"status": "complete", "output": str(args.output)}))


def _migrate(
    args: argparse.Namespace,
    paths: TargetMigrationPaths,
    fields: tuple[str, ...],
    restoration: Path | None,
    source_profile: str,
    destination_profile: str,
) -> None:
    if args.action == "prepare":
        state = prepare_target_migration(
            paths,
            legacy_include_fields=fields,
            deployment=bind_target_deployment(paths),
            restoration_manifest=restoration,
            source_profile=source_profile,
            destination_profile=destination_profile,
        )
    elif args.action == "promote":
        state = promote_target_migration(
            paths,
            deployment=bind_target_deployment(paths),
            source_profile=source_profile,
            destination_profile=destination_profile,
            cutover_authority="RF-013",
        )
    else:
        state = rollback_target_migration(
            paths,
            source_profile=source_profile,
            destination_profile=destination_profile,
        )
    print(
        json.dumps(
            {
                "phase": state["phase"],
                "journal": str(paths.backup / "journal.json"),
                **migration_status(state),
            }
        )
    )


def _run_migration(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.plan is None:
        parser.error("migration actions require --plan")
    active_root, paths, document, source_profile, destination_profile = _load_plan(
        parser, args.plan, action=args.action
    )
    fields = tuple(document["legacy_include_fields"])
    restoration = _restoration_manifest(parser, args, active_root)
    if args.action == "freeze-inputs":
        _freeze_inputs(parser, args, paths, fields, restoration)
        return
    if args.action == "build-candidates":
        _build_candidates(parser, args, paths, fields, restoration)
        return
    _migrate(args, paths, fields, restoration, source_profile, destination_profile)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "freeze-inputs",
            "build-candidates",
            "prepare",
            "promote",
            "rollback",
            "contour-report",
        ),
    )
    parser.add_argument("--input-manifest", type=Path)
    parser.add_argument("--input-manifest-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--run-started-at")
    parser.add_argument(
        "--restoration-manifest",
        type=Path,
        help="Validated assay/target FK restoration manifest",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        help=(
            "JSON: explicit paths, source_profile, destination_profile "
            "and frozen legacy_include_fields"
        ),
    )
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--discrepancy-report", type=Path)
    parser.add_argument("--expectations", type=Path)
    parser.add_argument("--shadow-table", type=Path)
    parser.add_argument("--shadow-classification", type=Path)
    parser.add_argument("--table", type=Path)
    parser.add_argument("--repeat-table", type=Path)
    parser.add_argument("--xlsx", type=Path)
    parser.add_argument("--isolated-silver", type=Path)
    parser.add_argument("--isolated-gold", type=Path)
    parser.add_argument("--silver", type=Path)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--assay", type=Path)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit 1 unless promotion_decision is READY or LIVE_ACCEPTED",
    )
    args = parser.parse_args(argv)
    if args.action == "contour-report":
        return _contour_report(parser, args)
    _run_migration(parser, args)
    return 0


def _contour_report(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.evidence is None or args.output is None:
        parser.error("contour-report requires --evidence and --output")
    try:
        evidence_path = confined_io_path(args.evidence, allow_external_absolute=True)
        payload = json.loads(
            evidence_path.read_text(encoding="utf-8")
        )  # NOSONAR - confined_io_path
        evidence = parse_evidence(payload)
        observations = apply_measurements(
            inspect_repository(args.repo_root or REPO_ROOT),
            evidence,
            ContourMeasurementPaths(
                discrepancy_report=args.discrepancy_report,
                expectations=args.expectations,
                shadow_table=args.shadow_table,
                shadow_classification=args.shadow_classification,
                table=args.table,
                repeat_table=args.repeat_table,
                xlsx=args.xlsx,
                isolated_silver=args.isolated_silver,
                isolated_gold=args.isolated_gold,
                silver=args.silver,
                gold=args.gold,
                assay=args.assay,
            ),
        )
        report = evaluate_main_contour(evidence, observations)
        write_contour_report(
            report,
            confined_io_path(args.output, allow_external_absolute=True),
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ContourEvidenceError,
        ValueError,
    ) as exc:
        parser.exit(2, f"{exc}\n")
    decision = str(report["promotion_decision"])
    print(
        json.dumps(
            {
                "promotion_decision": decision,
                "report": str(args.output),
                "rollback_required": report["rollback_required"],
            },
            sort_keys=True,
        )
    )
    if report["rollback_required"] is True:
        return 1
    if args.require_ready and decision not in {"READY", "LIVE_ACCEPTED"}:
        return 1
    return 0


def _plan_profiles(
    parser: argparse.ArgumentParser, document: dict[str, object]
) -> tuple[str, str]:
    """Require an explicit executable transition; do not infer 3.2.0."""
    source = document.get("source_profile")
    destination = document.get("destination_profile")
    if not isinstance(source, str) or not isinstance(destination, str):
        parser.error("plan requires explicit source_profile and destination_profile")
    try:
        resolve_target_migration_transition(source, destination)
    except ValueError as error:
        parser.error(str(error))
    return source, destination


if __name__ == "__main__":
    raise SystemExit(main())
