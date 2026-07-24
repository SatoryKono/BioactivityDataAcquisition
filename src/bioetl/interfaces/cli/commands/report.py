"""CLI commands for inspecting pipeline/workflow run reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from bioetl.application.services.run_reports.query import (
    diff_pipeline_reports,
    list_pipeline_reports,
    list_workflow_reports,
    load_pipeline_report,
    load_workflow_report,
    prune_reports,
)
from bioetl.application.services.run_reports.writer import DEFAULT_REPORT_ROOT
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_group,
    typed_click_option,
    typed_group_command,
)


@typed_click_group()
def report() -> None:
    """Inspect and manage local pipeline/workflow run reports."""


@typed_group_command(report, "show")
@typed_click_option("--pipeline", default=None, help="Pipeline name")
@typed_click_option("--run-id", default=None, help="Pipeline run id")
@typed_click_option("--workflow", default=None, help="Workflow name")
@typed_click_option("--workflow-run-id", default=None, help="Workflow run id")
@typed_click_option("--latest", is_flag=True, help="Load _latest pointer")
@typed_click_option(
    "--root",
    default=None,
    type=click.Path(path_type=Path),
    help="Reports root (default reports/run-reports)",
)
@typed_click_option(
    "--json", "as_json", is_flag=True, help="Print JSON instead of markdown"
)
def show_command(
    pipeline: str | None,
    run_id: str | None,
    workflow: str | None,
    workflow_run_id: str | None,
    latest: bool,
    root: Path | None,
    as_json: bool,
) -> None:
    """Show one pipeline or workflow run report."""
    report_root = root or DEFAULT_REPORT_ROOT
    if pipeline:
        payload = load_pipeline_report(
            pipeline_name=pipeline,
            run_id=run_id,
            latest=latest or run_id is None,
            root=report_root,
        )
        if payload is None:
            raise click.ClickException(
                f"pipeline run report not found for pipeline={pipeline!r} run_id={run_id!r}"
            )
        _emit_report(payload, as_json=as_json, markdown_hint="pipeline-run-report.md")
        return
    if workflow:
        payload = load_workflow_report(
            workflow_name=workflow,
            workflow_run_id=workflow_run_id,
            latest=latest or workflow_run_id is None,
            root=report_root,
        )
        if payload is None:
            raise click.ClickException(
                f"workflow run report not found for workflow={workflow!r} "
                f"workflow_run_id={workflow_run_id!r}"
            )
        _emit_report(payload, as_json=as_json, markdown_hint="workflow-run-report.md")
        return
    raise click.ClickException("provide --pipeline or --workflow")


@typed_group_command(report, "list")
@typed_click_option("--pipeline", default=None, help="Filter by pipeline name")
@typed_click_option("--workflow", default=None, help="Filter by workflow name")
@typed_click_option("--limit", default=20, show_default=True, type=int)
@typed_click_option(
    "--root",
    default=None,
    type=click.Path(path_type=Path),
    help="Reports root",
)
def list_command(
    pipeline: str | None,
    workflow: str | None,
    limit: int,
    root: Path | None,
) -> None:
    """List recent run reports."""
    report_root = root or DEFAULT_REPORT_ROOT
    if workflow and not pipeline:
        entries = list_workflow_reports(
            workflow_name=workflow,
            limit=limit,
            root=report_root,
        )
        for item in entries:
            click.echo(
                f"{item.owner}\t{item.run_id}\t{item.status or '-'}\t{item.json_path}"
            )
        return
    entries = list_pipeline_reports(
        pipeline_name=pipeline,
        limit=limit,
        root=report_root,
    )
    for item in entries:
        click.echo(
            f"{item.owner}\t{item.run_id}\t{item.status or '-'}\t{item.json_path}"
        )


@typed_group_command(report, "diff")
@typed_click_option("--pipeline", required=True, help="Pipeline name")
@typed_click_option("--run-id-a", required=True, help="Left run id")
@typed_click_option("--run-id-b", required=True, help="Right run id")
@typed_click_option(
    "--root",
    default=None,
    type=click.Path(path_type=Path),
    help="Reports root",
)
def diff_command(
    pipeline: str,
    run_id_a: str,
    run_id_b: str,
    root: Path | None,
) -> None:
    """Diff funnel and top reasons between two pipeline runs."""
    report_root = root or DEFAULT_REPORT_ROOT
    left = load_pipeline_report(
        pipeline_name=pipeline,
        run_id=run_id_a,
        root=report_root,
    )
    right = load_pipeline_report(
        pipeline_name=pipeline,
        run_id=run_id_b,
        root=report_root,
    )
    if left is None or right is None:
        raise click.ClickException("one or both run reports were not found")
    payload = diff_pipeline_reports(left, right)
    click.echo(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


@typed_group_command(report, "prune")
@typed_click_option(
    "--kind",
    type=click.Choice(["pipeline", "workflow"]),
    required=True,
)
@typed_click_option("--owner", default=None, help="pipeline or workflow name")
@typed_click_option("--max-count", type=int, default=None)
@typed_click_option("--max-age-days", type=int, default=None)
@typed_click_option("--apply", is_flag=True, help="Actually delete (default dry-run)")
@typed_click_option(
    "--root",
    default=None,
    type=click.Path(path_type=Path),
)
def prune_command(
    kind: str,
    owner: str | None,
    max_count: int | None,
    max_age_days: int | None,
    apply: bool,
    root: Path | None,
) -> None:
    """Prune old run report directories (dry-run by default)."""
    removed = prune_reports(
        kind=kind,
        owner=owner,
        max_count=max_count,
        max_age_days=max_age_days,
        root=root or DEFAULT_REPORT_ROOT,
        dry_run=not apply,
    )
    mode = "deleted" if apply else "would delete"
    for path in removed:
        click.echo(f"{mode}: {path}")
    click.echo(f"{mode}: {len(removed)} directories")


def _emit_report(
    payload: dict[str, Any],  # Any: decoded report JSON payload
    *,
    as_json: bool,
    markdown_hint: str,
) -> None:
    if as_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return
    # Prefer sibling markdown when available via artifacts
    for item in payload.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        ref = item.get("ref")
        if not ref or not str(ref).endswith(".md"):
            continue
        path = Path(str(ref))
        if path.is_file():
            click.echo(path.read_text(encoding="utf-8"))
            return
    identity = payload.get("identity") or {}
    click.echo(
        f"# report {identity.get('pipeline_name') or identity.get('workflow_name')}"
    )
    click.echo(json.dumps(identity, indent=2, sort_keys=True, ensure_ascii=False))
    click.echo(f"(markdown sibling `{markdown_hint}` not found; printed identity JSON)")
