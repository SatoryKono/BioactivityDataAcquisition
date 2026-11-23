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
    prepare_target_migration,
    promote_target_migration,
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
        "--restoration-manifest",
        type=Path,
        help="Validated assay/target FK restoration manifest",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="JSON: explicit paths and frozen legacy_include_fields",
    )
    args = parser.parse_args(argv)
    active_root = resolve_configs_root().resolve().parent
    document = json.loads(confined_io_path(args.plan, root=active_root).read_bytes())
    paths = TargetMigrationPaths(
        **{key: Path(value) for key, value in document["paths"].items()}
    )
    if paths.workspace.resolve() != active_root:
        parser.error("plan workspace must be the active repository/configs root")
    fields = tuple(document["legacy_include_fields"])
    if args.restoration_manifest is not None and args.action not in {
        "freeze-inputs",
        "prepare",
    }:
        parser.error("--restoration-manifest applies to freeze-inputs and prepare")
    restoration = (
        None
        if args.restoration_manifest is None
        else confined_io_path(args.restoration_manifest, root=active_root)
    )
    if args.action == "freeze-inputs":
        if args.output is None:
            parser.error("freeze-inputs requires --output NEW_MANIFEST_PATH")
        freeze_target_inputs(
            paths,
            legacy_include_fields=fields,
            output=args.output,
            restoration_manifest=restoration,
        )
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
                restoration_manifest=restoration,
            )
        elif args.action == "promote":
            state = promote_target_migration(
                paths, deployment=bind_target_deployment(paths)
            )
        else:
            state = rollback_target_migration(paths)
        print(
            json.dumps(
                {
                    "phase": state["phase"],
                    "journal": str(paths.backup / "journal.json"),
                }
            )
        )


if __name__ == "__main__":
    main()
