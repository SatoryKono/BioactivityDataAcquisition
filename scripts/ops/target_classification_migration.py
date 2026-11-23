"""Prepare, promote or roll back paired target tables under maintenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioetl.composition.bootstrap.cli.metrics import bind_target_deployment
from bioetl.infrastructure.config.config_root import resolve_configs_root
from scripts.engineering.common.repo_paths import confined_io_path
from bioetl.infrastructure.storage.target_candidates import (
    TargetCandidateBuildRequest,
    build_target_candidates,
    freeze_target_inputs,
)

from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
    migration_status,
    prepare_target_migration,
    promote_target_migration,
    resolve_target_migration_transition,
    rollback_target_migration,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("freeze-inputs", "build-candidates", "prepare", "promote", "rollback"),
    )
    parser.add_argument("--input-manifest", type=Path)
    parser.add_argument("--input-manifest-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--run-started-at")
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help=(
            "JSON: explicit paths, source_profile, destination_profile "
            "and frozen legacy_include_fields"
        ),
    )
    args = parser.parse_args(argv)
    active_root = resolve_configs_root().resolve().parent
    document = json.loads(confined_io_path(args.plan, root=active_root).read_bytes())
    source_profile, destination_profile = _plan_profiles(parser, document)
    if args.action == "promote" and document.get("cutover_authority") != "RF-013":
        parser.error(
            "canonical table promotion is reserved for RF-013; "
            "plan has no cutover authority"
        )
    paths = TargetMigrationPaths(
        **{key: Path(value) for key, value in document["paths"].items()}
    )
    if paths.workspace.resolve() != active_root:
        parser.error("plan workspace must be the active repository/configs root")
    fields = tuple(document["legacy_include_fields"])
    if args.action == "freeze-inputs":
        if args.output is None:
            parser.error("freeze-inputs requires --output NEW_MANIFEST_PATH")
        freeze_target_inputs(paths, legacy_include_fields=fields, output=args.output)
        print(json.dumps({"status": "frozen", "manifest": str(args.output)}))
    elif args.action == "build-candidates":
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
    else:
        if args.action == "prepare":
            state = prepare_target_migration(
                paths,
                legacy_include_fields=fields,
                deployment=bind_target_deployment(paths),
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
        reported = migration_status(state)
        print(
            json.dumps(
                {
                    "phase": state["phase"],
                    "journal": str(paths.backup / "journal.json"),
                    **reported,
                }
            )
        )


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
    main()
