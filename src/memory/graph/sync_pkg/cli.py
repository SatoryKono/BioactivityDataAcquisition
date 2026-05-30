"""CLI entry point and argument parsing for memory graph sync."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory.graph.sync_pkg._core import (
    GraphSnapshot,
    JsonValue,
    SnapshotSelection,
    SyncApplyOptions,
    _critical_analysis_audit_issues,
    _filtered_snapshot,
    _write_export,
    _write_json,
    apply_normalization_evidence_only,
    build_audit_report,
    build_fast_analysis_audit_report,
    build_snapshot,
    sync_snapshot,
)

from memory.graph.sync_pkg._core import DEFAULT_BATCH_SIZE
from memory.graph.sync_pkg._core import DEFAULT_ROOT


CLI_FLAG_DEFINITIONS: tuple[tuple[str, dict[str, object]], ...] = (
    (
        "--root",
        {
            "type": Path,
            "default": DEFAULT_ROOT,
            "help": "Project root directory.",
        },
    ),
    (
        "--apply",
        {
            "action": "store_true",
            "help": "Write the generated graph into Neo4j.",
        },
    ),
    (
        "--export",
        {
            "type": Path,
            "help": "Write the generated graph snapshot as JSON.",
        },
    ),
    (
        "--report",
        {
            "type": Path,
            "help": (
                "Write an audit report as JSON. "
                "The report includes snapshot stats, live managed/unmanaged summaries, "
                "label and relation diffs, and orphan summaries."
            ),
        },
    ),
    (
        "--report-fast",
        {
            "action": "store_true",
            "help": (
                "Use a reduced audit scope focused on critical analysis labels and relation types. "
                "This is faster and more stable on large live graphs."
            ),
        },
    ),
    (
        "--http-uri",
        {
            "type": str,
            "help": "Explicit Neo4j HTTP endpoint, e.g. http://localhost:7474.",
        },
    ),
    (
        "--batch-size",
        {
            "type": int,
            "default": DEFAULT_BATCH_SIZE,
            "help": "Maximum statements per Neo4j commit request.",
        },
    ),
    (
        "--prune-stale",
        {
            "action": "store_true",
            "help": (
                "Delete stale repo-derived nodes after sync. "
                "This only targets the current ingest wave and resets managed relations "
                "between repo-managed nodes before recreating them."
            ),
        },
    ),
    (
        "--full-reset-managed-wave",
        {
            "action": "store_true",
            "help": (
                "Delete the entire current managed ingest wave before rebuilding it. "
                "This removes all repo-managed nodes for the current wave and any relations "
                "attached to them, then recreates the wave from the current repository state."
            ),
        },
    ),
    (
        "--apply-normalization-evidence-only",
        {
            "action": "store_true",
            "help": (
                "Refresh only live normalization evidence on existing pipeline_surface and "
                "entity_config nodes without rebuilding the full repo snapshot."
            ),
        },
    ),
    (
        "--prune-legacy-unmanaged",
        {
            "action": "store_true",
            "help": (
                "Delete unmanaged legacy nodes for repo-derived labels after sync. "
                "This is intended to converge the repo graph to managed-only state for "
                "labels now owned by deterministic sync, while leaving unrelated labels "
                "such as MemoryEntity untouched."
            ),
        },
    ),
    (
        "--only-label",
        {
            "action": "append",
            "default": [],
            "help": (
                "Limit apply/export/report snapshot operations to one or more node labels. "
                "Useful for targeted sync debugging, e.g. --only-label complexity_candidate."
            ),
        },
    ),
    (
        "--only-analysis-layer",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to the analysis layer "
                "(retirement/development-cycle/complexity nodes and their relations)."
            ),
        },
    ),
    (
        "--only-retirement-layer",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to the retirement analysis layer "
                "(retirement/development-cycle nodes and retirement relations)."
            ),
        },
    ),
    (
        "--only-complexity-layer",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to the complexity analysis layer "
                "(complexity nodes and complexity relations)."
            ),
        },
    ),
    (
        "--only-storage-layer",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to storage, control-plane artifact, "
                "and related lineage materialization surfaces."
            ),
        },
    ),
    (
        "--only-runtime-evidence-layer",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to runtime evidence, emitted artifacts, "
                "and directly supporting module/doc/storage links."
            ),
        },
    ),
    (
        "--only-workflow-graph",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to GitHub workflow/job graph and "
                "related gate/script/file-structure links."
            ),
        },
    ),
    (
        "--only-docs-drift",
        {
            "action": "store_true",
            "help": (
                "Limit apply/export/report snapshot operations to docs/policies and their "
                "DESCRIBES drift edges into code/config/workflow surfaces."
            ),
        },
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and optionally sync a deterministic BioETL graph into Neo4j.",
    )
    for flag, options in CLI_FLAG_DEFINITIONS:
        parser.add_argument(flag, **options)
    return parser


def _selection_from_args(args: argparse.Namespace) -> SnapshotSelection:
    return SnapshotSelection(
        only_labels=tuple(args.only_label),
        only_analysis_layer=args.only_analysis_layer,
        only_retirement_layer=args.only_retirement_layer,
        only_complexity_layer=args.only_complexity_layer,
        only_storage_layer=args.only_storage_layer,
        only_runtime_evidence_layer=args.only_runtime_evidence_layer,
        only_workflow_graph=args.only_workflow_graph,
        only_docs_drift=args.only_docs_drift,
    )


def _validate_cli_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.prune_stale and args.full_reset_managed_wave:
        parser.error(
            "--prune-stale and --full-reset-managed-wave cannot be used together"
        )


def _print_snapshot_stats(snapshot: GraphSnapshot) -> None:
    print(json.dumps(snapshot.stats(), indent=2))


def _export_snapshot_if_requested(
    snapshot: GraphSnapshot,
    export_path: Path | None,
) -> None:
    if export_path is None:
        return
    _write_export(export_path, snapshot)
    print(f"Exported graph snapshot to {export_path}")


def _sync_snapshot_if_requested(
    args: argparse.Namespace,
    snapshot: GraphSnapshot,
    root: Path,
    selection: SnapshotSelection,
) -> None:
    if not args.apply:
        return

    sync_snapshot(
        snapshot,
        root,
        args.http_uri,
        SyncApplyOptions(
            batch_size=args.batch_size,
            prune_stale=args.prune_stale,
            full_reset_managed_wave=args.full_reset_managed_wave,
            prune_legacy_unmanaged=args.prune_legacy_unmanaged,
        ),
        selection=selection,
    )
    if not selection.targeted_mode():
        post_apply_report = build_fast_analysis_audit_report(
            snapshot, root, args.http_uri
        )
        critical_issues = _critical_analysis_audit_issues(post_apply_report)
        if critical_issues:
            raise RuntimeError(
                "Post-apply audit failed for critical analysis groups: "
                + "; ".join(critical_issues)
            )
    print("Neo4j sync completed.")


def _report_payload(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    report_fast: bool,
) -> dict[str, JsonValue]:
    if report_fast:
        return build_fast_analysis_audit_report(snapshot, root, http_uri)
    return build_audit_report(snapshot, root, http_uri)


def _write_report_if_requested(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    report_path: Path | None,
    report_fast: bool,
) -> None:
    if report_path is None:
        return
    report = _report_payload(snapshot, root, http_uri, report_fast)
    _write_json(report_path, report)
    print(f"Exported audit report to {report_path}")


def _normalization_operation_count(summary: dict[str, JsonValue]) -> int:
    completed = summary.get("completed_statement_count", 0)
    return max(1, int(completed))


def _snapshot_operation_count(args: argparse.Namespace) -> int:
    return (
        1
        + int(args.export is not None)
        + int(args.apply)
        + int(args.report is not None)
    )


def _run_apply_normalization_evidence_only(args: argparse.Namespace) -> int:
    """Execute normalization-evidence-only mode and return the CLI exit code."""
    summary = apply_normalization_evidence_only(
        args.root.resolve(),
        args.http_uri,
        batch_size=args.batch_size,
    )
    print(json.dumps(summary, indent=2))
    return 0


def _run_snapshot_cli(args: argparse.Namespace) -> int:
    """Execute the standard snapshot/sync CLI flow and return the exit code."""
    root = args.root.resolve()
    selection = _selection_from_args(args)
    snapshot = _filtered_snapshot(build_snapshot(root), selection=selection)
    _print_snapshot_stats(snapshot)
    _export_snapshot_if_requested(snapshot, args.export)
    _sync_snapshot_if_requested(args, snapshot, root, selection)
    _write_report_if_requested(
        snapshot,
        root,
        args.http_uri,
        args.report,
        args.report_fast,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_cli_args(parser, args)
    if args.apply_normalization_evidence_only:
        return _run_apply_normalization_evidence_only(args)
    return _run_snapshot_cli(args)


__all__ = [name for name in globals() if not name.startswith("__")]

