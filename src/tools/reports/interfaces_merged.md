================================================================================
File: __init__.py
Path: __init__.py
================================================================================
"""User interfaces for BioETL.

This package contains user-facing interfaces for the BioETL system.
Currently provides CLI and observability interfaces.

Components:
    cli: Command-line interface (Click-based).
    observability: User-facing observability utilities.

The interfaces layer sits at the outermost ring of the hexagonal
architecture and depends on all other layers per RULES.md.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_LAZY_MODULE_EXPORTS: dict[str, str] = {
    "cli": "bioetl.interfaces.cli",
    "http": "bioetl.interfaces.http",
    "observability": "bioetl.interfaces.observability",
}

__all__ = list(_LAZY_MODULE_EXPORTS.keys())


def __getattr__(name: str) -> ModuleType:
    """Lazily expose interface subpackages for patch/import stability."""
    try:
        module_name = _LAZY_MODULE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return stable interface exports for shell/help introspection."""
    # Use set-unpacking to avoid redundant intermediate set(...) calls flagged by static
    # analysis while keeping the behaviour: union of current globals and declared exports.
    return sorted({*globals(), *__all__})

================================================================================
File: __init__.py
Path: cli\__init__.py
================================================================================
"""CLI package for BioETL.

Provides command-line interface for pipeline operations.
This package follows the thin controller pattern - commands delegate
to Application services for all business logic.

Structure:
    cli/
    ├── __init__.py      # Package exports
    ├── main.py          # CLI entry point
    ├── formatters.py    # Output formatters
    └── commands/        # Individual command modules
        ├── run.py       # bioetl run
        ├── checkpoint.py# bioetl checkpoint
        ├── quarantine.py# bioetl quarantine
        └── maintenance.py# bioetl maintenance
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services import RunOptions
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

from bioetl.interfaces.cli.commands.domains.run.support import validate_pipeline_name
from bioetl.interfaces.cli.main import cli as cli
from bioetl.interfaces.cli.main import main as main


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Build a pipeline runner via the public composition facade.

    Kept as a package-level convenience export while avoiding a direct
    composition import at module import time.
    """
    from bioetl.composition.execution_api import create_pipeline_runner as _impl

    return _impl(name, options)


def __dir__() -> list[str]:
    """Return stable CLI exports for introspection."""
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "cli",
    "create_pipeline_runner",
    "main",
    "validate_pipeline_name",
]

================================================================================
File: __main__.py
Path: cli\__main__.py
================================================================================
"""Entry point for running CLI as a module.

Allows: python -m bioetl.interfaces.cli [commands]
"""

from __future__ import annotations

from bioetl.interfaces.cli.main import main

if __name__ == "__main__":
    main()

================================================================================
File: __init__.py
Path: cli\commands\__init__.py
================================================================================
"""CLI commands package for BioETL.

The compatibility surface remains at ``bioetl.interfaces.cli.commands.*``,
while canonical implementations are partitioned by operational domain under
``bioetl.interfaces.cli.commands.domains``.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_PUBLIC_COMMAND_MODULES = frozenset(
    {
        "adr",
        "archive",
        "checkpoint",
        "cleanup",
        "config",
        "config_dq",
        "diagnostics",
        "debug",
        "export",
        "export_support",
        "health",
        "health_rendering",
        "health_server_integration",
        "inspection_output",
        "lineage",
        "lock",
        "maintenance",
        "metrics_server_integration",
        "plan",
        "quarantine",
        "quarantine_execution",
        "quarantine_rendering",
        "quarantine_support",
        "run",
        "run_all",
        "run_composite",
        "run_manifest",
        "vacuum",
    }
)

__all__ = sorted(_PUBLIC_COMMAND_MODULES)


def __getattr__(name: str) -> ModuleType:
    """Lazily expose retained top-level command seams for compat patch targets."""
    if name not in _PUBLIC_COMMAND_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module

================================================================================
File: _compat.py
Path: cli\commands\_compat.py
================================================================================
"""Helpers for compatibility shims in the CLI commands layer."""

from __future__ import annotations

import sys
from importlib import import_module


def alias_module(module_name: str, target_module_name: str) -> None:
    """Replace a compat shim module with the canonical target module object."""
    target_module = import_module(target_module_name)
    current_module = sys.modules[module_name]
    current_module.__dict__.update(
        {
            name: getattr(target_module, name)
            for name in dir(target_module)
            if not name.startswith("__")
        }
    )
    current_module.__dict__["__doc__"] = getattr(target_module, "__doc__", None)
    current_module.__dict__["__all__"] = getattr(
        target_module,
        "__all__",
        [name for name in dir(target_module) if not name.startswith("_")],
    )
    sys.modules[module_name] = target_module


def reexport_module(module_name: str, target_module_name: str) -> None:
    """Populate a shim module with the public and private names of a target module."""
    target_module = import_module(target_module_name)
    target_globals = sys.modules[module_name].__dict__
    exported_names = {
        name: getattr(target_module, name)
        for name in dir(target_module)
        if not name.startswith("__")
    }
    target_globals.update(exported_names)
    target_globals["__doc__"] = getattr(target_module, "__doc__", None)
    target_globals["__all__"] = getattr(
        target_module,
        "__all__",
        [name for name in exported_names if not name.startswith("_")],
    )

================================================================================
File: _inspection_output.py
Path: cli\commands\_inspection_output.py
================================================================================
"""Shared output helpers for read-only CLI inspection commands."""

from __future__ import annotations

import json
from collections.abc import Callable

import yaml

from bioetl.interfaces.cli.formatters import echo_info

TextPayloadRenderer = Callable[[dict[str, object]], str]

__all__ = ["emit_inspection_payload"]


def emit_inspection_payload(
    payload: dict[str, object],
    output_format: str,
    *,
    text_renderer: TextPayloadRenderer,
) -> None:
    """Render inspection payload as JSON, YAML, or human-readable text."""
    if output_format == "json":
        echo_info(json.dumps(payload, indent=2, default=str))
        return
    if output_format == "yaml":
        echo_info(yaml.dump(payload, default_flow_style=False, sort_keys=False))
        return
    echo_info(text_renderer(payload))

================================================================================
File: _run_manifest_output.py
Path: cli\commands\_run_manifest_output.py
================================================================================
"""Private text renderers for run-manifest CLI commands."""

from __future__ import annotations

import json
from collections.abc import Iterable


def _format_scalar(value: object) -> str:
    """Format one scalar value for text-mode CLI output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_block(value: object) -> list[str]:
    """Format nested values as one or more human-readable text lines."""
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    if isinstance(value, list):
        if not value:
            return ["[]"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    return [_format_scalar(value)]


def _append_section(
    lines: list[str],
    title: str,
    items: Iterable[tuple[str, object]],
) -> None:
    """Append a titled section to text output."""
    filtered = [(label, value) for label, value in items if value not in (None, [], {})]
    if not filtered:
        return
    if lines:
        lines.append("")
    lines.append(title)
    for label, value in filtered:
        rendered = _format_block(value)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)


def _render_manifest_section(manifest: dict[str, object]) -> list[str]:
    """Render manifest section."""
    lines: list[str] = []
    provenance = manifest.get("code_provenance", {})

    _append_section(
        lines,
        "Manifest",
        (
            ("manifest_id", manifest.get("manifest_id")),
            ("run_id", manifest.get("run_id")),
            ("pipeline_name", manifest.get("pipeline_name")),
            ("provider", manifest.get("provider")),
            ("entity", manifest.get("entity")),
            ("run_type", manifest.get("run_type")),
            ("created_at", manifest.get("created_at")),
            ("execution_fingerprint", manifest.get("execution_fingerprint")),
            ("schema_version", manifest.get("schema_version")),
            ("replay_of_run_id", manifest.get("replay_of_run_id")),
            ("replay_of_manifest_id", manifest.get("replay_of_manifest_id")),
        ),
    )

    if isinstance(provenance, dict):
        _append_section(
            lines,
            "Code Provenance",
            (
                ("pipeline_version", provenance.get("pipeline_version")),
                ("git_commit", provenance.get("git_commit")),
                ("config_hash", provenance.get("config_hash")),
            ),
        )

    _append_section(
        lines,
        "Execution Inputs",
        (
            ("launch_context", manifest.get("launch_context")),
            ("runtime_config", manifest.get("runtime_config")),
            ("resolved_config", manifest.get("resolved_config")),
            ("source_refs", manifest.get("source_refs")),
            ("planned_artifacts", manifest.get("planned_artifacts")),
        ),
    )

    return lines


def _render_ledger_section(ledger_entries: list[object]) -> list[str]:
    """Render ledger section."""
    lines: list[str] = []

    if isinstance(ledger_entries, list) and ledger_entries:
        lines.append("Ledger")
        lines.append(f"  entries: {len(ledger_entries)}")
        for entry in ledger_entries:
            if not isinstance(entry, dict):
                lines.append(f"  - {_format_scalar(entry)}")
                continue
            summary = f"{entry.get('occurred_at', '?')} {entry.get('event_type', '?')}"
            stage = entry.get("stage")
            status = entry.get("status")
            if stage is not None:
                summary += f" stage={stage}"
            if status is not None:
                summary += f" status={status}"
            lines.append(f"  - {summary}")
    else:
        _append_section(lines, "Ledger", (("entries", 0),))

    return lines


def _render_diagnostics_section(diagnostics: dict[str, object]) -> list[str]:
    """Render diagnostics section."""
    lines: list[str] = []

    if isinstance(diagnostics, dict):
        _append_section(
            lines,
            "Diagnostics",
            (
                ("latest_status", diagnostics.get("latest_status")),
                ("latest_event_type", diagnostics.get("latest_event_type")),
                ("total_events", diagnostics.get("total_events")),
                ("execution_fingerprint", diagnostics.get("execution_fingerprint")),
                ("config_hash", diagnostics.get("config_hash")),
                ("contract_ref", diagnostics.get("contract_ref")),
                ("contract_version", diagnostics.get("contract_version")),
                ("dq_policy_ref", diagnostics.get("dq_policy_ref")),
                ("rule_bundle_version", diagnostics.get("rule_bundle_version")),
                (
                    "effective_config_artifact_id",
                    diagnostics.get("effective_config_artifact_id"),
                ),
                (
                    "dq_contract_compatibility_hash",
                    diagnostics.get("dq_contract_compatibility_hash"),
                ),
                ("requested_exact_replay", diagnostics.get("requested_exact_replay")),
                (
                    "exact_replay_support_boundary",
                    diagnostics.get("exact_replay_support_boundary"),
                ),
                ("replay_family_contract", diagnostics.get("replay_family_contract")),
                (
                    "replay_capability_reason",
                    diagnostics.get("replay_capability_reason"),
                ),
                ("exact_replay_blockers", diagnostics.get("exact_replay_blockers")),
                ("input_snapshot_ids", diagnostics.get("input_snapshot_ids")),
                (
                    "input_snapshot_content_hashes",
                    diagnostics.get("input_snapshot_content_hashes"),
                ),
                (
                    "input_snapshot_identity_fingerprint",
                    diagnostics.get("input_snapshot_identity_fingerprint"),
                ),
                ("replay_mode", diagnostics.get("replay_mode")),
                ("replay_of_run_id", diagnostics.get("replay_of_run_id")),
                ("replay_of_manifest_id", diagnostics.get("replay_of_manifest_id")),
                ("replay_parentage", diagnostics.get("replay_parentage")),
                ("input_snapshot_count", diagnostics.get("input_snapshot_count")),
                ("input_snapshots", diagnostics.get("input_snapshots")),
                ("event_family_counts", diagnostics.get("event_family_counts")),
                ("event_type_counts", diagnostics.get("event_type_counts")),
                ("planned_artifact_count", diagnostics.get("planned_artifact_count")),
                (
                    "published_artifact_count",
                    diagnostics.get("published_artifact_count"),
                ),
                ("missing_artifact_links", diagnostics.get("missing_artifact_links")),
                ("lineage_fragment_ids", diagnostics.get("lineage_fragment_ids")),
                ("artifact_refs", diagnostics.get("artifact_refs")),
                ("identity_graph_complete", diagnostics.get("identity_graph_complete")),
                ("dq_rule_ids", diagnostics.get("dq_rule_ids")),
                ("dq_dispositions", diagnostics.get("dq_dispositions")),
                ("dq_report_paths", diagnostics.get("dq_report_paths")),
                ("dq_violation_kinds", diagnostics.get("dq_violation_kinds")),
                (
                    "cross_validation_rule_ids",
                    diagnostics.get("cross_validation_rule_ids"),
                ),
                (
                    "cross_validation_config_paths",
                    diagnostics.get("cross_validation_config_paths"),
                ),
                (
                    "cross_validation_quarantine_policy",
                    diagnostics.get("cross_validation_quarantine_policy"),
                ),
                (
                    "cross_validation_quarantine_replay_contract",
                    diagnostics.get("cross_validation_quarantine_replay_contract"),
                ),
                (
                    "occurrence_only_diagnostics",
                    diagnostics.get("occurrence_only_diagnostics"),
                ),
                (
                    "cross_validation_signal_present",
                    diagnostics.get("cross_validation_signal_present"),
                ),
                ("correlation_anchor_gaps", diagnostics.get("correlation_anchor_gaps")),
                ("persistence_profile", diagnostics.get("persistence_profile")),
                ("alert_signals", diagnostics.get("alert_signals")),
                ("next_steps", diagnostics.get("next_steps")),
            ),
        )

    return lines


def _render_identity_graph_section(identity_graph: object) -> list[str]:
    """Render one explicit identity-graph reconstruction section."""
    lines: list[str] = []
    if not isinstance(identity_graph, dict):
        return lines
    _append_section(
        lines,
        "Identity Graph",
        (
            ("run_id", identity_graph.get("run_id")),
            ("manifest_id", identity_graph.get("manifest_id")),
            ("execution_fingerprint", identity_graph.get("execution_fingerprint")),
            ("effective_config_hash", identity_graph.get("effective_config_hash")),
            ("contract_ref", identity_graph.get("contract_ref")),
            ("contract_version", identity_graph.get("contract_version")),
            ("replay_capability", identity_graph.get("replay_capability")),
            ("requested_exact_replay", identity_graph.get("requested_exact_replay")),
            (
                "exact_replay_support_boundary",
                identity_graph.get("exact_replay_support_boundary"),
            ),
            ("replay_family_contract", identity_graph.get("replay_family_contract")),
            (
                "replay_capability_reason",
                identity_graph.get("replay_capability_reason"),
            ),
            ("exact_replay_eligible", identity_graph.get("exact_replay_eligible")),
            ("exact_replay_blockers", identity_graph.get("exact_replay_blockers")),
            ("input_snapshot_ids", identity_graph.get("input_snapshot_ids")),
            (
                "input_snapshot_content_hashes",
                identity_graph.get("input_snapshot_content_hashes"),
            ),
            (
                "input_snapshot_identity_fingerprint",
                identity_graph.get("input_snapshot_identity_fingerprint"),
            ),
            ("replay_mode", identity_graph.get("replay_mode")),
            ("replay_of_run_id", identity_graph.get("replay_of_run_id")),
            ("replay_of_manifest_id", identity_graph.get("replay_of_manifest_id")),
            ("replay_parentage", identity_graph.get("replay_parentage")),
            ("input_snapshot_count", identity_graph.get("input_snapshot_count")),
            ("input_snapshots", identity_graph.get("input_snapshots")),
            ("planned_artifacts", identity_graph.get("planned_artifacts")),
            ("published_artifacts", identity_graph.get("published_artifacts")),
            (
                "occurrence_only_diagnostics",
                identity_graph.get("occurrence_only_diagnostics"),
            ),
        ),
    )
    return lines


def render_show_payload(payload: dict[str, object]) -> str:
    """Render one manifest inspection payload in human-readable form."""
    manifest = payload.get("manifest", {})
    ledger_entries = payload.get("ledger_entries", [])
    diagnostics = payload.get("diagnostics", {})
    identity_graph = payload.get("identity_graph", {})

    if not isinstance(ledger_entries, list):
        ledger_entries = []
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    if not isinstance(identity_graph, dict):
        identity_graph = {}

    if not isinstance(manifest, dict):
        return json.dumps(payload, indent=2, default=str)

    lines: list[str] = []
    lines.extend(_render_manifest_section(manifest))

    if lines:
        lines.append("")
    lines.extend(_render_ledger_section(ledger_entries))

    if lines and isinstance(ledger_entries, list) and ledger_entries:
        lines.append("")
    lines.extend(_render_diagnostics_section(diagnostics))

    identity_graph_lines = _render_identity_graph_section(identity_graph)
    if lines and identity_graph_lines:
        lines.append("")
    lines.extend(identity_graph_lines)

    return "\n".join(lines)


def render_diff_payload(payload: dict[str, object]) -> str:
    """Render one manifest diff payload in human-readable form."""
    left_manifest_id = payload.get("left_manifest_id")
    right_manifest_id = payload.get("right_manifest_id")
    differences = payload.get("differences", [])
    lines: list[str] = [
        "Manifest Diff",
        f"  left_manifest_id: {_format_scalar(left_manifest_id)}",
        f"  right_manifest_id: {_format_scalar(right_manifest_id)}",
        f"  classification: {_format_scalar(payload.get('classification'))}",
        f"  semantic_equivalent: {_format_scalar(payload.get('semantic_equivalent'))}",
        f"  occurrence_only: {_format_scalar(payload.get('occurrence_only'))}",
        f"  replay_relationship: {_format_scalar(payload.get('replay_relationship'))}",
    ]
    for label in (
        "occurrence_difference_fields",
        "semantic_difference_fields",
        "noncanonical_difference_fields",
    ):
        value = payload.get(label)
        if value in (None, [], ()):
            continue
        rendered = _format_block(value)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)
    if not isinstance(differences, list) or not differences:
        lines.append("  differences: 0")
        return "\n".join(lines)
    lines.append(f"  differences: {len(differences)}")
    for entry in differences:
        if not isinstance(entry, dict):
            lines.append("")
            lines.append(f"- {_format_scalar(entry)}")
            continue
        lines.append("")
        lines.append(f"- field: {_format_scalar(entry.get('field'))}")
        for side in ("left", "right"):
            rendered = _format_block(entry.get(side))
            if len(rendered) == 1:
                lines.append(f"  {side}: {rendered[0]}")
                continue
            lines.append(f"  {side}:")
            lines.extend(f"    {line}" for line in rendered)
    return "\n".join(lines)


def render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "manifest" in payload:
        return render_show_payload(payload)
    if "differences" in payload:
        return render_diff_payload(payload)
    return json.dumps(payload, indent=2, default=str)

================================================================================
File: adr.py
Path: cli\commands\adr.py
================================================================================
"""ADR management commands for BioETL CLI.

Provides commands to list, show, and validate ADR documents.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import click

from bioetl.domain.types import JsonDict
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.domain.ports import AdrServicePort

__all__ = [
    "COMMANDS",
    "adr",
    "list_command",
    "show_command",
    "validate_command",
]


@click.group()  # type: ignore[untyped-decorator]
def adr() -> None:
    """ADR (Architecture Decision Records) utilities."""


def get_adr_service() -> AdrServicePort:
    """Load the ADR service through composition on demand."""
    from bioetl.composition.control_plane_api import get_adr_service as _impl

    return _impl()


@adr.command("list")  # type: ignore[untyped-decorator]
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
def list_command(as_json: bool) -> None:
    """List all ADR documents.

    Args:
        as_json: When True, outputs the ADR list as a JSON array instead of
            a human-readable text list.
    """
    service = get_adr_service()
    items = service.list_adrs()
    if as_json:
        payload: list[
            JsonDict  # Any: CLI/HTTP response values are heterogeneous
        ] = [  # Any: CLI/HTTP response values are heterogeneous
            {"number": i.number, "title": i.title, "path": i.path} for i in items
        ]
        echo_info(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not items:
        echo_info("No ADR documents found.")
        return
    echo_info("ADR documents:")
    for item in items:
        echo_info(f"  - ADR-{item.number:03d}: {item.title}")


@adr.command("show")  # type: ignore[untyped-decorator]
@click.argument("number", type=int)  # type: ignore[untyped-decorator]
@click.option("--raw", is_flag=True, help="Print raw markdown content")  # type: ignore[untyped-decorator]
def show_command(number: int, raw: bool) -> None:
    """Show a specific ADR by number.

    Args:
        number: ADR number to display (e.g., 26 for ADR-026).
        raw: When True, prints the raw Markdown content instead of a
            formatted summary.
    """
    service = get_adr_service()
    try:
        doc = service.get_adr(number)
    except FileNotFoundError as e:
        echo_error("ADR not found", str(e))
        return
    if raw:
        echo_info(doc.content)
        return
    echo_info(f"ADR-{doc.number:03d}: {doc.title}")
    if doc.status:
        echo_info(f"Status: {doc.status}")
    if doc.date:
        echo_info(f"Date: {doc.date}")
    echo_info("")
    # Print first lines as preview
    head = "\n".join(doc.content.splitlines()[:40])
    echo_info(head)


@adr.command("validate")  # type: ignore[untyped-decorator]
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
def validate_command(as_json: bool) -> None:
    """Validate ADR repository and print a summary.

    Args:
        as_json: When True, outputs the validation report as JSON instead of
            a human-readable text summary.
    """
    service = get_adr_service()
    report = service.validate()
    if as_json:
        payload = {
            "valid": report.valid,
            "total": report.total,
            "errors": report.errors,
            "warnings": report.warnings,
            "issues": [
                {
                    "number": i.number,
                    "path": i.path,
                    "message": i.message,
                    "severity": i.severity,
                }
                for i in report.issues
            ],
        }
        echo_info(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    status = "OK" if report.valid else "FAILED"
    echo_info(f"ADR validation: {status}")
    echo_info(f"  Total: {report.total}")
    echo_info(f"  Errors: {report.errors}")
    echo_info(f"  Warnings: {report.warnings}")
    if report.issues:
        echo_info("Issues:")
        for i in report.issues:
            num = f"ADR-{i.number:03d}" if i.number is not None else "ADR-???"
            echo_info(f"  - [{i.severity.upper()}] {num} @ {i.path}: {i.message}")


# Explicit command collection to mark usage for tooling.
COMMANDS = (
    list_command,
    show_command,
    validate_command,
)

================================================================================
File: archive.py
Path: cli\commands\archive.py
================================================================================
"""Retained public archive command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.archive import (
        archive_command as archive_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.archive import (
        get_lifecycle_service as get_lifecycle_service,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.archive")

================================================================================
File: checkpoint.py
Path: cli\commands\checkpoint.py
================================================================================
"""Checkpoint management commands for BioETL CLI.

Implements checkpoint listing and management commands.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_checkpoint, echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )

__all__ = [
    "COMMANDS",
    "checkpoint",
    "checkpoint_audit_run",
    "checkpoint_inspect",
    "checkpoint_list",
]

_NONE_ENTRY_LINE = "  - none"


@click.group()  # type: ignore[untyped-decorator]
def checkpoint() -> None:
    """Manage checkpoints."""


def get_checkpoint_manager(pipeline: str) -> CheckpointManagerService:
    """Load the checkpoint manager through composition on demand."""
    from bioetl.composition.resources_api import get_checkpoint_manager as _impl

    return _impl(pipeline)


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load observability workflows through the canonical public interface."""
    from bioetl.interfaces.observability import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


def _render_audit_entry_lines(entries: list[object]) -> list[str]:
    """Render audit entries as compact operator-facing lines."""
    lines: list[str] = []
    for item in entries:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        line = (
            "  - "
            f"{item.get('timestamp', '?')} "
            f"{item.get('layer', '?')}/{item.get('table_name', '?')} "
            f"{item.get('operation', '?')} "
            f"records={item.get('records_count', '?')}"
        )
        lines.append(line)
    return lines or [_NONE_ENTRY_LINE]


def _resolve_replay_view(
    run_manifest: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Return manifest metadata plus the preferred replay diagnostics view."""
    manifest = run_manifest.get("manifest", {})
    diagnostics = run_manifest.get("diagnostics", {})
    identity_graph = run_manifest.get("identity_graph", {})
    replay_view = (
        identity_graph
        if isinstance(identity_graph, dict) and identity_graph
        else diagnostics
    )
    return (
        manifest if isinstance(manifest, dict) else None,
        replay_view if isinstance(replay_view, dict) else None,
    )


def _extract_persistence_profile_details(
    replay_view: dict[str, object],
) -> tuple[object | None, object | None, object | None, object | None]:
    """Return the operator-facing persistence profile details from replay view."""
    persistence_profile = replay_view.get("persistence_profile")
    if not isinstance(persistence_profile, dict):
        return None, None, None, None
    return (
        persistence_profile.get("attained_profile"),
        persistence_profile.get("composite_resume_reconstructability"),
        persistence_profile.get("replay_ready_missing_requirements"),
        persistence_profile.get("forensic_grade_missing_requirements"),
    )


def _render_audit_run_manifest_lines(
    run_manifest: dict[str, object],
) -> list[str]:
    """Render manifest and replay diagnostics lines for audit-run output."""
    manifest, replay_view = _resolve_replay_view(run_manifest)
    lines: list[str] = []
    if manifest is not None:
        lines.extend(
            [
                f"  manifest_id: {manifest.get('manifest_id')}",
                f"  pipeline_name: {manifest.get('pipeline_name')}",
            ]
        )
    if replay_view is None:
        return lines

    (
        attained_profile,
        composite_resume_reconstructability,
        replay_ready_missing_requirements,
        forensic_grade_missing_requirements,
    ) = _extract_persistence_profile_details(replay_view)
    lines.extend(
        [
            f"  replay_capability: {replay_view.get('replay_capability')}",
            f"  requested_exact_replay: {replay_view.get('requested_exact_replay')}",
            f"  exact_replay_support_boundary: {replay_view.get('exact_replay_support_boundary')}",
            f"  replay_capability_reason: {replay_view.get('replay_capability_reason')}",
            f"  exact_replay_blockers: {replay_view.get('exact_replay_blockers')}",
            f"  input_snapshot_ids: {replay_view.get('input_snapshot_ids')}",
            f"  input_snapshot_identity_fingerprint: {replay_view.get('input_snapshot_identity_fingerprint')}",
            f"  persistence_profile: {attained_profile}",
            f"  replay_ready_missing_requirements: {replay_ready_missing_requirements}",
            f"  forensic_grade_missing_requirements: {forensic_grade_missing_requirements}",
            f"  composite_resume_reconstructability: {composite_resume_reconstructability}",
            f"  alert_signals: {replay_view.get('alert_signals')}",
            f"  next_steps: {replay_view.get('next_steps')}",
        ]
    )
    return lines


def _render_audit_run_payload(payload: dict[str, object]) -> str:
    """Render one audit-run inspection payload in human-readable text."""
    audit = payload.get("audit", {})
    run_manifest = payload.get("run_manifest")
    entries = audit.get("entries", []) if isinstance(audit, dict) else []
    lines = [
        "Audit Run Diagnostics",
        f"  run_id: {payload.get('run_id')}",
        f"  audit_entries: {len(entries) if isinstance(entries, list) else 0}",
    ]
    if isinstance(run_manifest, dict):
        lines.extend(_render_audit_run_manifest_lines(run_manifest))
    lines.extend(["", "Audit Entries"])
    if isinstance(entries, list):
        lines.extend(_render_audit_entry_lines(entries))
    else:
        lines.append(_NONE_ENTRY_LINE)
    return "\n".join(lines)


def _render_checkpoint_workflow_payload(payload: dict[str, object]) -> str:
    """Render one checkpoint workflow payload in human-readable text."""
    checkpoint = payload.get("checkpoint")
    audit = payload.get("audit", {})
    run_manifest = payload.get("run_manifest")
    entries = audit.get("entries", []) if isinstance(audit, dict) else []
    lines = [
        "Checkpoint Workflow Diagnostics",
        f"  pipeline_name: {payload.get('pipeline_name')}",
    ]
    if isinstance(checkpoint, dict):
        lines.extend(
            [
                f"  checkpoint_run_id: {checkpoint.get('run_id')}",
                f"  checkpoint_metadata_keys: "
                f"{len(checkpoint.get('metadata', {})) if isinstance(checkpoint.get('metadata'), dict) else 0}",
            ]
        )
    else:
        lines.append("  checkpoint: none")
    if isinstance(run_manifest, dict):
        manifest = run_manifest.get("manifest", {})
        if isinstance(manifest, dict):
            lines.extend(
                [
                    f"  manifest_id: {manifest.get('manifest_id')}",
                    f"  manifest_run_id: {manifest.get('run_id')}",
                ]
            )
    lines.extend(
        [
            f"  audit_entries: {len(entries) if isinstance(entries, list) else 0}",
            "",
            "Audit Entries",
        ]
    )
    if isinstance(entries, list):
        lines.extend(_render_audit_entry_lines(entries))
    else:
        lines.append(_NONE_ENTRY_LINE)
    return "\n".join(lines)


def _render_checkpoint_payload(payload: dict[str, object]) -> str:
    """Render checkpoint CLI inspection payload in text mode."""
    if "run_id" in payload and "audit" in payload and "pipeline_name" not in payload:
        return _render_audit_run_payload(payload)
    if "pipeline_name" in payload and "audit" in payload:
        return _render_checkpoint_workflow_payload(payload)
    return json.dumps(payload, indent=2, default=str)


@checkpoint.command("list")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints.

    Args:
        pipeline: Pipeline.
    """
    echo_info(f"Listing checkpoints for {pipeline}...")

    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            echo_checkpoint(cp)

    asyncio.run(_list())


@checkpoint.command("audit-run")  # type: ignore[untyped-decorator]
@click.option("--run-id", required=True, help="Pipeline RUN_ID to inspect")  # type: ignore[untyped-decorator]
@click.option("--limit", default=100, show_default=True, help="Maximum audit entries")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def checkpoint_audit_run(run_id: str, limit: int, output_format: str) -> None:
    """Inspect one pipeline run across audit and run-manifest observability surfaces."""
    workflow_service = get_observability_workflow_service()

    async def _inspect() -> None:
        try:
            result = await workflow_service.inspect_audit_run(run_id, limit=limit)
        except ValueError as exc:
            echo_error("Audit run diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@checkpoint.command("inspect")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
@click.option("--run-id", default=None, help="Optional RUN_ID override")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--audit-limit",
    default=100,
    show_default=True,
    help="Maximum audit entries",
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def checkpoint_inspect(
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Inspect checkpoint state with correlated audit and run-manifest context."""
    workflow_service = get_observability_workflow_service()

    async def _inspect() -> None:
        try:
            result = await workflow_service.inspect_checkpoint_workflow(
                pipeline,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        except ValueError as exc:
            echo_error("Checkpoint diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


# Hint for tooling: explicit reference to command function.
COMMANDS = (checkpoint_list, checkpoint_audit_run, checkpoint_inspect)

================================================================================
File: cleanup.py
Path: cli\commands\cleanup.py
================================================================================
"""Retained public cleanup command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        bronze_cleanup_command as bronze_cleanup_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        cleanup_preview_command as cleanup_preview_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        get_bronze_cleanup_service as get_bronze_cleanup_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        preview_pipeline_cleanup as preview_pipeline_cleanup,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.cleanup")

================================================================================
File: config.py
Path: cli\commands\config.py
================================================================================
"""Configuration commands for BioETL CLI.

Implements config inspection and validation commands.
Uses ConfigService from composition entrypoints for clean layering.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import click

from bioetl.domain.types import JsonDict
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.config_service import ConfigService

__all__ = [
    "COMMANDS",
    "config",
    "list_pipelines_command",
    "show_command",
    "show_settings_command",
    "validate_command",
]


def get_config_service() -> ConfigService:
    """Load the config service through composition on demand."""
    from bioetl.composition.control_plane_api import get_config_service as _impl

    return _impl()


def _config_to_dict(config: object) -> JsonDict:
    """Convert a Pydantic model or dataclass to a JSON-serializable dict.

    Args:
        config: Pydantic model, dataclass, or primitive value to convert.

    Returns:
        JSON-serializable dict representation of the config object.
    """
    if hasattr(config, "model_dump"):
        model_dump = config.model_dump
        result: JsonDict = model_dump()
        return result
    if hasattr(config, "__dict__"):
        converted: JsonDict = {  # Any: YAML config has heterogeneous values
            k: _config_to_dict(v) if hasattr(v, "__dict__") else v
            for k, v in config.__dict__.items()
            if not k.startswith("_")
        }
        return converted
    return {"value": config}  # Wrap primitives in a dict


@click.group()  # type: ignore[untyped-decorator]
def config() -> None:
    """View and validate configuration."""


@config.command("show")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_command(pipeline: str, output_format: str) -> None:
    """Show configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config show chembl_activity

        bioetl config show chembl_activity --format json

    Args:
        pipeline: Pipeline.
        output_format: Output format.
    """
    service = get_config_service()

    try:
        config_dict = service.get_pipeline_yaml_config(pipeline)
    except ValueError as e:
        echo_error("Configuration error", str(e))
        return
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))
        return

    if output_format == "json":
        echo_info(json.dumps(config_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(config_dict, default_flow_style=False, sort_keys=False))


@config.command("validate")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
def validate_command(pipeline: str) -> None:
    """Validate configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config validate chembl_activity

    Args:
        pipeline: Pipeline.
    """
    service = get_config_service()

    try:
        info = service.validate_pipeline_config(pipeline)
        echo_info(f"Configuration valid for {pipeline}")
        echo_info(f"  Provider: {info.provider}")
        echo_info(f"  Entity type: {info.entity_type}")
        echo_info(f"  Silver table: {info.silver_table}")
        if info.gold_table:
            echo_info(f"  Gold table: {info.gold_table}")
    except ValueError as e:
        echo_error("Configuration invalid", str(e))
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))


@config.command("show-settings")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_settings_command(output_format: str) -> None:
    """Show global application settings.

    Displays environment-based configuration from BIOETL_* variables.

    Examples:

        bioetl config show-settings

        bioetl config show-settings --format json

    Args:
        output_format: Output format.
    """
    service = get_config_service()
    settings_info = service.get_settings()

    # Convert SettingsInfo to dict for output
    settings_dict: JsonDict = {  # Any: YAML config has heterogeneous values
        "env": settings_info.env,
        "data_dir": settings_info.data_dir,
        "bronze_path": settings_info.bronze_path,
        "silver_path": settings_info.silver_path,
        "gold_path": settings_info.gold_path,
        "checkpoint_path": settings_info.checkpoint_path,
        "quarantine_path": settings_info.quarantine_path,
        "debug": settings_info.debug,
        "test_mode": settings_info.test_mode,
        "metrics_enabled": settings_info.metrics_enabled,
        "metrics_port": settings_info.metrics_port,
        "batch_size": settings_info.batch_size,
    }

    # Add additional settings (with sensitive values masked)
    for key, value in settings_info.additional.items():
        if "api_key" in key.lower() or "password" in key.lower():
            settings_dict[key] = "***MASKED***"
        else:
            settings_dict[key] = value

    if output_format == "json":
        echo_info(json.dumps(settings_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(settings_dict, default_flow_style=False, sort_keys=False))


@config.command("list-pipelines")  # type: ignore[untyped-decorator]
def list_pipelines_command() -> None:
    """List all registered pipelines.

    Examples:

        bioetl config list-pipelines
    """
    service = get_config_service()
    pipelines = service.list_pipelines()

    if not pipelines:
        echo_info("No pipelines registered.")
        return

    echo_info("Available pipelines:")
    for pipeline in sorted(pipelines):
        echo_info(f"  - {pipeline}")


# Explicit command collection to mark usage for tooling.
COMMANDS = (
    list_pipelines_command,
    show_command,
    show_settings_command,
    validate_command,
)

================================================================================
File: config_dq.py
Path: cli\commands\config_dq.py
================================================================================
"""Data Quality configuration commands for BioETL CLI.

Implements DQ config inspection and validation commands.
Uses ConfigService from composition entrypoints for clean layering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml

from bioetl.domain.types import JsonDict
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.config_service import ConfigService

__all__ = [
    "COMMANDS",
    "check_compatibility_command",
    "dq",
    "show_dq_config_command",
    "show_effective_config_command",
    "validate_dq_config_command",
]


def get_config_service() -> ConfigService:
    """Load the config service through composition on demand."""
    from bioetl.composition.control_plane_api import get_config_service as _impl

    return _impl()


@click.group()  # type: ignore[untyped-decorator]
def dq() -> None:
    """Data Quality configuration commands."""


@dq.command("show")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_dq_config_command(pipeline: str, output_format: str) -> None:
    """Show Data Quality configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl dq show chembl_activity

        bioetl dq show chembl_activity --format json

    Args:
        pipeline: Pipeline.
        output_format: Output format.
    """
    service = get_config_service()

    try:
        dq_config = service.get_dq_config(pipeline)
    except ValueError as e:
        echo_error("DQ Configuration error", str(e))
        return
    except FileNotFoundError as e:
        echo_error("DQ Config file not found", str(e))
        return

    if output_format == "json":
        echo_info(json.dumps(dq_config, indent=2, default=str))
    else:
        echo_info(yaml.dump(dq_config, default_flow_style=False, sort_keys=False))


@dq.command("validate")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--config-file",
    type=click.Path(exists=True),
    help="Path to DQ config file to validate",
)
def validate_dq_config_command(pipeline: str, config_file: str | None) -> None:
    """Validate Data Quality configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)
    CONFIG_FILE: Optional path to DQ config file to validate

    Examples:

        bioetl dq validate chembl_activity

        bioetl dq validate chembl_activity --config-file custom_dq_config.yaml

    Args:
        pipeline: Pipeline.
        config_file: Optional path to DQ config file.
    """
    service = get_config_service()

    try:
        if config_file:
            with Path(config_file).open(encoding="utf-8") as file_obj:
                loaded = yaml.safe_load(file_obj)
            if not isinstance(loaded, dict):
                echo_error(
                    "DQ Configuration invalid",
                    "Config file must contain a mapping at the top level.",
                )
                return
            is_valid = service.validate_dq_config(pipeline, loaded)
            if is_valid:
                echo_info(f"[OK] DQ configuration is valid for {pipeline}")
                return
            echo_error(f"[ERROR] DQ configuration is invalid for {pipeline}")
            return

        dq_config = service.get_dq_config(pipeline)
        echo_info(f"[OK] DQ configuration is valid for {pipeline}")
        echo_info(f"  Contract Ref: {dq_config.get('contract_ref', 'N/A')}")
        echo_info(f"  Contract Version: {dq_config.get('contract_version', 'N/A')}")
        echo_info(f"  Rule Bundle: {dq_config.get('rule_bundle_version', 'N/A')}")
        echo_info(
            "  Default Disposition: "
            f"{dq_config.get('default_disposition_policy', 'N/A')}"
        )
        echo_info(f"  Strictness Mode: {dq_config.get('strictness_mode', 'N/A')}")
    except ValueError as e:
        echo_error("DQ Configuration invalid", str(e))
    except FileNotFoundError as e:
        echo_error("DQ Config file not found", str(e))
    except (OSError, TypeError, yaml.YAMLError) as e:
        echo_error("DQ Configuration validation failed", str(e))


@dq.command("show-effective")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
@click.option(  # type: ignore[untyped-decorator]
    "--override",
    "overrides",
    multiple=True,
    help="Runtime override in format key=value",
)
def show_effective_config_command(
    pipeline: str, output_format: str, overrides: tuple[str, ...]
) -> None:
    """Show effective configuration artifact for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)
    OVERRIDES: Optional runtime overrides

    Examples:

        bioetl dq show-effective chembl_activity

        bioetl dq show-effective chembl_activity --override batch_size=100

        bioetl dq show-effective chembl_activity --format json

    Args:
        pipeline: Pipeline.
        output_format: Output format.
        overrides: Runtime overrides.
    """
    service = get_config_service()

    try:
        runtime_overrides: JsonDict = {}
        for override in overrides:
            if "=" not in override:
                continue
            key, value = override.split("=", 1)
            runtime_overrides[key] = value

        artifact = service.get_effective_config_artifact(pipeline, runtime_overrides)

        if output_format == "json":
            echo_info(json.dumps(artifact, indent=2, default=str))
        else:
            echo_info(yaml.dump(artifact, default_flow_style=False, sort_keys=False))

    except ValueError as e:
        echo_error("Effective config error", str(e))
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))
    except TypeError as e:
        echo_error("Failed to create effective config artifact", str(e))


@dq.command("check-compatibility")  # type: ignore[untyped-decorator]
@click.argument("artifact1_file")  # type: ignore[untyped-decorator]
@click.argument("artifact2_file")  # type: ignore[untyped-decorator]
def check_compatibility_command(artifact1_file: str, artifact2_file: str) -> None:
    """Check compatibility between two configuration artifacts.

    ARTIFACT1_FILE: Path to first artifact file
    ARTIFACT2_FILE: Path to second artifact file

    Examples:

        bioetl dq check-compatibility artifact1.json artifact2.json

    Args:
        artifact1_file: Path to first artifact file.
        artifact2_file: Path to second artifact file.
    """
    service = get_config_service()

    try:
        with Path(artifact1_file).open(encoding="utf-8") as file_one:
            artifact1 = json.load(file_one)
        with Path(artifact2_file).open(encoding="utf-8") as file_two:
            artifact2 = json.load(file_two)
        if not isinstance(artifact1, dict) or not isinstance(artifact2, dict):
            echo_error("Compatibility check failed", "Artifacts must be JSON objects")
            return

        is_compatible = service.check_config_compatibility(artifact1, artifact2)

        if is_compatible:
            dq_compatible = artifact1.get(
                "dq_contract_compatibility_hash", "N/A"
            ) == artifact2.get("dq_contract_compatibility_hash", "N/A")
            effective_hash_compatible = artifact1.get(
                "effective_config_hash", "N/A"
            ) == artifact2.get("effective_config_hash", "N/A")
            echo_info("[OK] Configurations are compatible")
            echo_info(f"  Artifact 1: {artifact1.get('artifact_id', 'unknown')}")
            echo_info(f"  Artifact 2: {artifact2.get('artifact_id', 'unknown')}")
            echo_info(f"  DQ Compatible: {dq_compatible}")
            echo_info(f"  Effective Config Hash: {effective_hash_compatible}")
        else:
            echo_error("[ERROR] Configurations are NOT compatible")
            echo_error(f"  Artifact 1: {artifact1.get('artifact_id', 'unknown')}")
            echo_error(f"  Artifact 2: {artifact2.get('artifact_id', 'unknown')}")
            echo_error("  Check DQ contract compatibility and effective config hashes")

    except FileNotFoundError as e:
        echo_error("Artifact file not found", str(e))
    except json.JSONDecodeError as e:
        echo_error("Invalid JSON in artifact file", str(e))
    except (OSError, ValueError, TypeError) as e:
        echo_error("Compatibility check failed", str(e))


# Explicit command collection to mark usage for tooling.
COMMANDS = (
    show_dq_config_command,
    validate_dq_config_command,
    show_effective_config_command,
    check_compatibility_command,
)

================================================================================
File: debug.py
Path: cli\commands\debug.py
================================================================================
"""Debug command for interactive pipeline step-through execution.

Runs a pipeline with breakpoints at configurable lifecycle stages,
allowing inspection of intermediate state (records, DQ metrics, etc.).
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services import RunOptions, RunResult
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.pipeline_debug_service import DebugAbortError
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.ports import StageBreakpoint

__all__ = ["debug"]

_BREAKPOINT_CHOICES = (
    "after_preflight",
    "after_bronze",
    "after_silver",
    "after_gold",
    "after_dq",
    "on_error",
    "on_quarantine",
)


def _load_stage_breakpoint() -> type[StageBreakpoint]:
    """Resolve StageBreakpoint lazily to avoid command import fan-out."""
    from bioetl.domain.ports import StageBreakpoint

    return StageBreakpoint


def _load_run_options_type() -> type[RunOptions]:
    """Resolve RunOptions lazily to keep CLI imports lightweight."""
    from bioetl.application.services import RunOptions

    return RunOptions


def _load_debug_abort_error_type() -> type[DebugAbortError]:
    """Resolve DebugAbortError lazily to keep CLI imports lightweight."""
    from bioetl.application.services.pipeline_debug_service import DebugAbortError

    return DebugAbortError


def _resolve_context_registry(
    ctx: click.Context | None,
) -> PipelineRegistry | None:
    """Proxy to the shared run support helper without importing it eagerly."""
    from bioetl.interfaces.cli.commands.domains.run.support import (
        resolve_context_registry,
    )

    return resolve_context_registry(ctx)


def _validate_pipeline_name(
    click_context: click.Context | None,
    param: click.Parameter | None,
    value: str,
) -> str:
    """Proxy to the shared pipeline validator without eager imports."""
    from bioetl.interfaces.cli.commands.domains.run.support import (
        validate_pipeline_name,
    )

    return validate_pipeline_name(click_context, param, value)


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as _impl

    return _impl(registry=registry)


@click.command()  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline",
    callback=_validate_pipeline_name,
    required=True,
    help="Pipeline to debug",
)
@click.option(  # type: ignore[untyped-decorator]
    "--breakpoints",
    type=str,
    default=None,
    help=f"Comma-separated breakpoints: {', '.join(_BREAKPOINT_CHOICES)}. "
    "Default: all breakpoints enabled.",
)
@click.option(  # type: ignore[untyped-decorator]
    "--limit", type=int, default=10, help="Max records to process (default: 10)"
)
@click.option(  # type: ignore[untyped-decorator]
    "--mode",
    type=click.Choice(["interactive", "log"]),
    default="interactive",
    help="Debug mode: interactive (CLI prompts) or log (auto-continue with logging)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run",
)
@click.pass_context  # type: ignore[untyped-decorator]
def debug(
    ctx: click.Context,
    pipeline: str,
    breakpoints: str | None,
    limit: int,
    mode: str,
    run_type: str,
) -> None:
    """Run a pipeline in debug mode with breakpoints.

    Enables step-through execution with inspection of intermediate
    state at each pipeline lifecycle stage.
    """
    # Parse breakpoints
    enabled_breakpoints: set[StageBreakpoint] | None = None
    if breakpoints:
        stage_breakpoint = _load_stage_breakpoint()
        try:
            enabled_breakpoints = {
                stage_breakpoint(bp.strip()) for bp in breakpoints.split(",")
            }
        except ValueError as exc:
            echo_error(
                f"Invalid breakpoint: {exc}. Valid: {', '.join(_BREAKPOINT_CHOICES)}"
            )
            sys.exit(ExitCode.CONFIG_ERROR)

    echo_info(f"Starting debug session for pipeline '{pipeline}'")
    echo_info(f"Mode: {mode} | Limit: {limit} | Run type: {run_type}")

    if enabled_breakpoints:
        echo_info(f"Breakpoints: {', '.join(bp.value for bp in enabled_breakpoints)}")
    else:
        echo_info("Breakpoints: all stages enabled")

    run_options_type = _load_run_options_type()
    options = run_options_type(
        run_type=run_type,
        limit=limit,
        dry_run=False,
        log_level="DEBUG",
    )
    registry = _resolve_context_registry(ctx)
    debug_abort_error = _load_debug_abort_error_type()

    try:
        result = asyncio.run(
            _run_debug_session(
                pipeline,
                options,
                mode,
                enabled_breakpoints,
                registry=registry,
            )
        )
        echo_info(f"Debug session complete: {result.status.value}")
        echo_info(
            f"Records: fetched={result.records_fetched}, "
            f"silver={result.records_silver}, "
            f"quarantined={result.records_quarantined}"
        )
    except debug_abort_error:
        echo_info("Pipeline aborted by user at breakpoint")
        sys.exit(ExitCode.SIGINT)
    except KeyboardInterrupt:
        echo_info("Debug session interrupted")
        sys.exit(ExitCode.SIGINT)


async def _run_debug_session(
    pipeline: str,
    options: RunOptions,
    mode: str,
    enabled_breakpoints: set[StageBreakpoint] | None,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Run pipeline with debug adapter attached.

    Args:
        pipeline: Pipeline name.
        options: Run options with limit and run_type.
        mode: Debug mode ('interactive' or 'log').
        enabled_breakpoints: Breakpoints to enable.

    Returns:
        RunResult from pipeline execution.
    """
    del mode, enabled_breakpoints
    service = get_pipeline_runner_service(registry=registry)
    return await service.run(pipeline, options=options)

================================================================================
File: diagnostics.py
Path: cli\commands\diagnostics.py
================================================================================
"""Retained public diagnostics command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        diagnostics as diagnostics,
    )
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        get_observability_diagnostics_bundle as get_observability_diagnostics_bundle,
    )
    from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
        get_quarantine_manager as get_quarantine_manager,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.diagnostics.command")

================================================================================
File: __init__.py
Path: cli\commands\domains\__init__.py
================================================================================
"""Operational-domain partitions for CLI command implementations."""

from __future__ import annotations

================================================================================
File: __init__.py
Path: cli\commands\domains\composite\__init__.py
================================================================================
"""Canonical composite-run command domain package."""

from __future__ import annotations

__all__ = ["run_composite"]


def __getattr__(name: str) -> object:
    if name == "run_composite":
        from bioetl.interfaces.cli.commands.domains.composite.command import (
            run_composite,
        )

        return run_composite
    raise AttributeError(name)

================================================================================
File: command.py
Path: cli\commands\domains\composite\command.py
================================================================================
"""Run composite pipeline command for BioETL CLI.

Implements the composite pipeline execution command that orchestrates
multiple data sources (seed + enrichers) into a unified dataset.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    bootstrap_composite_runner as _bootstrap_composite_runner_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    load_composite_config as _load_composite_config_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    run_composite_async as _run_composite_async_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    run_composite_inner as _run_composite_inner_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    build_runtime_config,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    emit_composite_startup as _emit_composite_startup_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    exit_with_composite_result as _exit_with_composite_result_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    handle_run_composite_exception as _handle_run_composite_exception_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    run_composite_with_cli_policy as _run_composite_with_cli_policy_impl,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.domain.composite.config import CompositeConfig

__all__ = [
    "run_composite",
]


def _validate_composite_name(
    _ctx: click.Context, _param: click.Parameter, value: str
) -> str:
    """Validate composite pipeline name."""
    if not value:
        raise click.BadParameter("Composite pipeline name is required")
    return value


def load_composite_config(name: str) -> CompositeConfig:
    """Load composite config through the canonical execution helper seam."""
    return _load_composite_config_impl(name)


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
) -> CompositePipelineRunner:
    """Build composite runner through the canonical execution helper seam."""
    return _bootstrap_composite_runner_impl(config, runtime)


async def _run_composite_inner(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
) -> tuple[bool, str | None]:
    """Run composite pipeline execution logic."""
    result: tuple[bool, str | None] = await _run_composite_inner_impl(
        composite_name,
        runtime,
        load_config=load_composite_config,
        build_runner=bootstrap_composite_runner,
    )
    return result


async def _run_composite_async(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> tuple[bool, str | None]:
    """Run composite pipeline asynchronously with optional health server."""
    result: tuple[bool, str | None] = await _run_composite_async_impl(
        composite_name,
        runtime,
        health_server_enabled=health_server_enabled,
        health_port=health_port,
        run_inner=_run_composite_inner,
        metrics_starter=ensure_metrics_server_started,
        health_context_factory=health_server_context,
    )
    return result


def _handle_run_composite_exception(
    exc: BaseException,
    *,
    composite: str,
    reason_code: str,
) -> None:
    _handle_run_composite_exception_impl(
        exc,
        composite=composite,
        reason_code=reason_code,
    )


def _run_composite_with_cli_policy(
    *,
    composite: str,
    runtime: CompositeRuntimeConfig,
    health_server: bool,
    health_port: int,
) -> tuple[bool, str | None]:
    result: tuple[bool, str | None] = _run_composite_with_cli_policy_impl(
        composite=composite,
        runtime=runtime,
        health_server=health_server,
        health_port=health_port,
        run_async=_run_composite_async,
        exception_handler=lambda exc, composite_name, code: (
            _handle_run_composite_exception(
                exc,
                composite=composite_name,
                reason_code=code,
            )
        ),
    )
    return result


def _echo_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Emit startup information for composite run."""
    _emit_composite_startup_impl(
        composite=composite,
        dry_run=dry_run,
        resume=resume,
        cached_bronze_enabled=cached_bronze_enabled,
        health_server=health_server,
        health_port=health_port,
        info_printer=echo_info,
        warning_printer=echo_warning,
        health_info_printer=echo_health_server_info,
    )


def _exit_with_composite_result(success: bool, error_message: str | None) -> None:
    _exit_with_composite_result_impl(success, error_message)


@click.command(name="run-composite")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--composite",
    callback=_validate_composite_name,
    required=True,
    help="Composite pipeline name (e.g., 'publication')",
)
@click.option(  # type: ignore[untyped-decorator]
    "--resume",
    is_flag=True,
    help="Resume from last checkpoint state; not a strict exact replay",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Preview execution without writing data",
)
@click.option(  # type: ignore[untyped-decorator]
    "--seed-limit",
    type=int,
    help="Maximum records for seed pipeline",
)
@click.option(  # type: ignore[untyped-decorator]
    "--enrich-only",
    type=str,
    help="Run only specified enrichers (comma-separated)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--required-only",
    is_flag=True,
    help="Skip optional enrichers",
)
@click.option(  # type: ignore[untyped-decorator]
    "--force-enricher",
    type=str,
    help="Force re-run of specified enricher (ignores checkpoint)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--use-cached-bronze/--no-cached-bronze",
    "use_cached_bronze",
    default=False,
    help="Load data from Bronze cache instead of API",
    show_default=True,
)
@click.option(  # type: ignore[untyped-decorator]
    "--cached-bronze-date",
    type=str,
    default=None,
    help="Filter Bronze cache by date (YYYY-MM-DD)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--cached-bronze-path",
    type=click.Path(exists=True),
    default=None,
    help="Explicit path to Bronze cache directory",
)
@click.option(  # type: ignore[untyped-decorator]
    "--cached-bronze-enrichers/--no-cached-bronze-enrichers",
    "cached_bronze_enrichers",
    default=None,
    help="Override cached Bronze for enrichers (default: follow --use-cached-bronze)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--cached-bronze-dependencies/--no-cached-bronze-dependencies",
    "cached_bronze_dependencies",
    default=False,
    help="Override cached Bronze for dependencies (default: use API)",
    show_default=True,
)
@click.option(  # type: ignore[untyped-decorator]
    "--debug",
    is_flag=True,
    help="Enable DEBUG level logging",
)
@click.option(  # type: ignore[untyped-decorator]
    "--health-server/--no-health-server",
    "health_server",
    default=True,
    help="Enable/disable HTTP health server during execution.",
    show_default=True,
)
@click.option(  # type: ignore[untyped-decorator]
    "--health-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the HTTP health server.",
    show_default=True,
)
def run_composite(
    composite: str,
    resume: bool,
    dry_run: bool,
    seed_limit: int | None,
    enrich_only: str | None,
    required_only: bool,
    force_enricher: str | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    cached_bronze_enrichers: bool | None,
    cached_bronze_dependencies: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Run a composite pipeline that combines multiple data sources.

    Composite pipelines orchestrate a seed pipeline (e.g., ChEMBL publications)
    with multiple enricher pipelines (CrossRef, OpenAlex, PubMed, etc.) to
    create a unified, enriched dataset.

    Example:
        bioetl run-composite --composite publication --seed-limit 100

    Args:
        composite: Composite pipeline name (e.g., 'publication').
        resume: When True, resumes from the last saved checkpoint.
        dry_run: When True, runs the pipeline without writing data to storage.
        seed_limit: Maximum number of seed records to fetch; no limit if None.
        enrich_only: Comma-separated enricher names to run; all enrichers run
            if None.
        required_only: When True, optional enrichers are skipped.
        force_enricher: Enricher name to force-rerun, ignoring its checkpoint.
        use_cached_bronze: When True, loads data from the Bronze cache instead
            of calling the external API.
        cached_bronze_date: ISO date string (YYYY-MM-DD) used to filter cached
            Bronze files; not applied if None.
        cached_bronze_path: Explicit path to a Bronze cache directory; auto-
            resolved from settings if None.
        cached_bronze_enrichers: Override cached Bronze usage for enrichers only;
            follows ``use_cached_bronze`` if None.
        cached_bronze_dependencies: When True, dependency pipelines also load
            from the Bronze cache.
        debug: When True, sets log level to DEBUG for detailed output.
        health_server: When True, starts an HTTP health server during execution.
        health_port: TCP port for the HTTP health server.
    """
    runtime = build_runtime_config(
        resume=resume,
        dry_run=dry_run,
        seed_limit=seed_limit,
        enrich_only=enrich_only,
        required_only=required_only,
        force_enricher=force_enricher,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_enrichers=cached_bronze_enrichers,
        cached_bronze_dependencies=cached_bronze_dependencies,
    )
    _echo_composite_startup(
        composite=composite,
        dry_run=dry_run,
        resume=resume,
        cached_bronze_enabled=(
            runtime.use_cached_bronze
            or runtime.cached_bronze_enrichers is True
            or runtime.cached_bronze_dependencies
        ),
        health_server=health_server,
        health_port=health_port,
    )
    success, error_message = _run_composite_with_cli_policy(
        composite=composite,
        runtime=runtime,
        health_server=health_server,
        health_port=health_port,
    )
    _exit_with_composite_result(success, error_message)

================================================================================
File: execution.py
Path: cli\commands\domains\composite\execution.py
================================================================================
"""Execution helpers for the run-composite CLI command."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.result import CompositeResult


def load_composite_config(name: str) -> CompositeConfig:
    """Load composite config through composition on demand."""
    from bioetl.composition.composite_api import load_composite_config as _impl

    return _impl(name)


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
) -> CompositePipelineRunner:
    """Build composite runner through composition on demand."""
    from bioetl.composition.composite_api import bootstrap_composite_runner as _impl

    return _impl(config, runtime)


def build_run_composite_result(
    result: CompositeResult,
) -> tuple[bool, str | None]:
    """Map composite runner result to CLI success/error tuple."""
    if result.is_success:
        return True, None
    failed = result.failed_enrichers
    if failed:
        return False, f"Failed enrichers: {', '.join(failed)}"
    return False, "Composite pipeline failed"


async def run_composite_inner(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    *,
    load_config: Callable[[str], CompositeConfig] = load_composite_config,
    build_runner: Callable[
        [CompositeConfig, CompositeRuntimeConfig],
        CompositePipelineRunner,
    ] = bootstrap_composite_runner,
) -> tuple[bool, str | None]:
    """Run composite pipeline execution logic."""
    try:
        config = load_config(composite_name)
    except FileNotFoundError as exc:
        return False, str(exc)
    except ValueError as exc:
        return False, f"Invalid configuration: {exc}"

    runner = build_runner(config, runtime)

    try:
        return build_run_composite_result(await runner.run())
    except (BioETLError, OSError, RuntimeError, ValueError) as exc:
        return (
            False,
            (
                f"{exc} "
                f"(reason_code=CLI_COMPOSITE_RUNNER_ERROR, composite={composite_name}, "
                f"error_type={type(exc).__name__})"
            ),
        )


async def run_composite_async(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    *,
    run_inner: Callable[
        [str, CompositeRuntimeConfig],
        Awaitable[tuple[bool, str | None]],
    ] = run_composite_inner,
    metrics_starter: Callable[[], bool | None] = ensure_metrics_server_started,
    health_context_factory: Callable[
        ...,
        AbstractAsyncContextManager[object],
    ] = health_server_context,
) -> tuple[bool, str | None]:
    """Run composite pipeline asynchronously with optional health server."""
    metrics_starter()
    async with health_context_factory(
        enabled=health_server_enabled,
        port=health_port,
    ):
        return await run_inner(composite_name, runtime)

================================================================================
File: runtime.py
Path: cli\commands\domains\composite\runtime.py
================================================================================
"""Runtime option helpers for `run-composite` command."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning


def parse_enrich_only(enrich_only: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated `enrich_only` value into tuple.

    Args:
        enrich_only: Comma-separated enricher names from the CLI option
            (e.g., 'crossref,pubmed'), or None if the option was not set.

    Returns:
        Tuple of stripped enricher name strings, or None if the input is empty or None.
    """
    if not enrich_only:
        return None
    return tuple(item.strip() for item in enrich_only.split(","))


def build_runtime_config(
    *,
    resume: bool,
    dry_run: bool,
    seed_limit: int | None,
    enrich_only: str | None,
    required_only: bool,
    force_enricher: str | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    cached_bronze_enrichers: bool | None,
    cached_bronze_dependencies: bool,
) -> CompositeRuntimeConfig:
    """Build composite runtime config from CLI options.

    Args:
        resume: Whether to resume from the last checkpoint.
        dry_run: When True, no data is written to storage.
        seed_limit: Maximum number of records to fetch during the seed phase;
            no limit applied if None.
        enrich_only: Comma-separated list of enricher names to run; all enrichers
            run if None.
        required_only: When True, optional enrichers are skipped.
        force_enricher: Enricher name whose checkpoint is ignored for a forced re-run;
            no forced re-run if None.
        use_cached_bronze: When True, loads data from the Bronze cache instead of the API.
        cached_bronze_date: ISO date string (YYYY-MM-DD) used to filter cached Bronze files;
            not applied if None.
        cached_bronze_path: Explicit path to a Bronze cache directory; auto-resolved if None.
        cached_bronze_enrichers: Override cached Bronze usage for enrichers; follows
            ``use_cached_bronze`` if None.
        cached_bronze_dependencies: When True, dependency pipelines also use cached Bronze.

    Returns:
        CompositeRuntimeConfig ready for composite pipeline bootstrap.
    """
    return CompositeRuntimeConfig(
        resume=resume,
        dry_run=dry_run,
        enrich_only=parse_enrich_only(enrich_only),
        required_only=required_only,
        force_enricher=force_enricher,
        seed_limit=seed_limit,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_enrichers=cached_bronze_enrichers,
        cached_bronze_dependencies=cached_bronze_dependencies,
    )


def echo_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Print startup info for composite run.

    Args:
        composite: Composite pipeline name (e.g., 'publication').
        dry_run: When True, displays a dry-run warning in the output.
        resume: When True, displays a resume-mode notice in the output.
        cached_bronze_enabled: When True, prints a warning that cached Bronze
            on composite execution is outside the strict exact-replay boundary.
        health_server: Whether the HTTP health server is enabled.
        health_port: Port the health server is listening on.
    """
    echo_info(f"Starting composite pipeline: {composite}")
    if dry_run:
        echo_warning("Dry-run mode: no data will be written")
    if resume:
        echo_info("Resume mode: continuing from last checkpoint")
    if cached_bronze_enabled:
        echo_warning(
            "Cached Bronze inputs on composite execution are outside the strict "
            "exact-replay boundary; treat this run as rebuild/resume, not exact replay."
        )
    echo_health_server_info(health_server, health_port)

================================================================================
File: support.py
Path: cli\commands\domains\composite\support.py
================================================================================
"""Helper functions for the run-composite CLI command."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Coroutine

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    map_success_flag_to_exit_code,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = [
    "emit_composite_startup",
    "exit_with_composite_result",
    "handle_run_composite_exception",
    "run_composite_with_cli_policy",
]


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
) -> bool:
    """Push metrics through composition on demand."""
    from bioetl.composition.execution_api import push_metrics_to_gateway as _impl

    return bool(_impl(run_label=run_label, pipeline_name=pipeline_name))


def emit_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
    health_info_printer: Callable[[bool, int], None] = echo_health_server_info,
) -> None:
    """Emit startup information for composite execution."""
    info_printer(f"Starting composite pipeline: {composite}")
    if dry_run:
        warning_printer("Dry-run mode: no data will be written")
    if resume:
        info_printer("Resume mode: continuing from last checkpoint")
    if cached_bronze_enabled:
        warning_printer(
            "Cached Bronze inputs on composite execution are outside the strict "
            "exact-replay boundary; treat this run as rebuild/resume, not exact replay."
        )
    health_info_printer(health_server, health_port)


def handle_run_composite_exception(
    exc: BaseException,
    *,
    composite: str,
    reason_code: str,
) -> None:
    """Render a canonical CLI failure for run-composite."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="composite",
        subject_value=composite,
        domain_error_title="Composite execution failed with domain error",
        unexpected_error_title="Unexpected error during composite execution",
        interrupted_message="Composite pipeline interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def run_composite_with_cli_policy(
    *,
    composite: str,
    runtime: CompositeRuntimeConfig,
    health_server: bool,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    run_async: Callable[
        [str, CompositeRuntimeConfig, bool, int],
        Coroutine[object, object, tuple[bool, str | None]],
    ],
    exception_handler: Callable[[BaseException, str, str], None] | None = None,
) -> tuple[bool, str | None]:
    """Execute run-composite coroutine with shared CLI exception policy."""
    coro = run_async(
        composite,
        runtime,
        health_server,
        health_port,
    )
    success = False
    error_message: str | None = None
    handler = exception_handler or _default_exception_handler
    try:
        success, error_message = asyncio.run(coro)
    except BioETLError as exc:
        handler(exc, composite, "CLI_COMPOSITE_DOMAIN_ERROR")
    except KeyboardInterrupt as exc:
        handler(exc, composite, "CLI_COMPOSITE_SIGINT")
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handler(exc, composite, "CLI_COMPOSITE_UNEXPECTED_ERROR")
    finally:
        push_metrics_to_gateway(pipeline_name=f"composite_{composite}")
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return success, error_message


def exit_with_composite_result(success: bool, error_message: str | None) -> None:
    """Exit the CLI process using the canonical run-composite result mapping."""
    exit_code = map_success_flag_to_exit_code(success)
    if success:
        echo_info("Composite pipeline completed successfully")
        sys.exit(exit_code)
    echo_error("Composite pipeline failed", error_message or "Unknown error")
    sys.exit(exit_code)


def _default_exception_handler(
    exc: BaseException,
    composite: str,
    reason_code: str,
) -> None:
    handle_run_composite_exception(
        exc,
        composite=composite,
        reason_code=reason_code,
    )

================================================================================
File: __init__.py
Path: cli\commands\domains\diagnostics\__init__.py
================================================================================
"""Canonical diagnostics command domain package."""

from __future__ import annotations

__all__ = ["diagnostics"]


def __getattr__(name: str) -> object:
    if name == "diagnostics":
        from bioetl.interfaces.cli.commands.domains.diagnostics.command import (
            diagnostics,
        )

        return diagnostics
    raise AttributeError(name)

================================================================================
File: command.py
Path: cli\commands\domains\diagnostics\command.py
================================================================================
"""Unified operator-facing diagnostics entrypoint for BioETL CLI."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.checkpoint import _render_checkpoint_payload
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
    build_health_result_lines,
    render_health_results_json,
)
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _show_quarantine_stats,
)
from bioetl.interfaces.cli.commands.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.composition.observability_api import (
        MetricsOperatorProfile,
        ObservabilityDiagnosticsBundle,
    )
    from bioetl.domain.types import JsonDict

__all__ = [
    "COMMANDS",
    "diagnostics",
    "diagnostics_checkpoint",
    "diagnostics_guide",
    "diagnostics_health",
    "diagnostics_manifest",
    "diagnostics_metrics",
    "diagnostics_quarantine",
    "diagnostics_run",
    "get_metrics_operator_profile",
    "get_observability_diagnostics_bundle",
    "get_quarantine_manager",
]


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Load the canonical operator diagnostics bundle on demand."""
    from bioetl.interfaces.observability import (
        get_observability_diagnostics_bundle as _impl,
    )

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Load the canonical operator-facing metrics diagnostics profile."""
    from bioetl.interfaces.observability import get_metrics_operator_profile as _impl

    return _impl()


def get_quarantine_manager(pipeline: str) -> object:
    """Load the quarantine manager through composition on demand."""
    from bioetl.composition.resources_api import get_quarantine_manager as _impl

    return _impl(pipeline)


def _build_diagnostics_guide_lines() -> list[str]:
    """Return the canonical operator diagnostics routing guide."""
    return [
        "BioETL Diagnostics Guide",
        "  start_here: bioetl diagnostics guide",
        ("  metrics/admin: bioetl diagnostics metrics [--json]",),
        ("  health: bioetl diagnostics health [--provider <provider>] [--json]"),
        (
            "  run: bioetl diagnostics run --run-id <run-id> "
            "[--limit 100] [--format text|json|yaml]"
        ),
        (
            "  checkpoint: bioetl diagnostics checkpoint --pipeline <pipeline> "
            "[--run-id <run-id>] [--audit-limit 100] [--format text|json|yaml]"
        ),
        (
            "  manifest: bioetl diagnostics manifest <run-id|manifest-id> "
            "[--format text|json|yaml]"
        ),
        (
            "  quarantine: bioetl diagnostics quarantine --pipeline <pipeline> "
            "[--run-id <run-id>] [--group-by reason-signature] [--json]"
        ),
        "",
        "Observability verification workflow:",
        "  1. bioetl diagnostics metrics [--json]",
        "  2. bioetl diagnostics health [--json]",
        "  3. python -m scripts.engineering.qa report-observability-metric-inventory --json",
        (
            "  4. compare inventory output with "
            "grafana/prometheus-rules/bioetl_observability.yml and shipped dashboards"
        ),
        "",
        "Metrics server startup is auto-managed during pipeline runs when metrics are enabled.",
        "Pushgateway publication is best-effort on run completion; inspect current config with diagnostics metrics.",
        "",
        "Legacy command groups remain supported:",
        "  health check",
        "  checkpoint inspect",
        "  checkpoint audit-run",
        "  run-manifest show",
        "  quarantine stats",
    ]


def _echo_health_results(
    results: dict[str, dict[str, str | float | int | None]],
    *,
    output_json: bool,
) -> None:
    """Render provider health results with the canonical health formatting."""
    if output_json:
        click.echo(render_health_results_json(results))
    else:
        click.echo("Running health checks...")
        for line in build_health_result_lines(results):
            click.echo(line)
        if all_health_results_healthy(results):
            click.echo("\nAll providers healthy.")
        else:
            click.echo("\nSome providers unhealthy.")


def _render_guide_lines(lines: Iterable[str]) -> None:
    """Emit guide text lines in stable order."""
    for line in lines:
        click.echo(line)


def _build_metrics_profile_lines(profile: MetricsOperatorProfile) -> list[str]:
    """Render the canonical operator-facing metrics/admin workflow summary."""
    started_at = (
        profile.metrics_started_at.isoformat()
        if profile.metrics_started_at is not None
        else "not_running"
    )
    endpoint = profile.metrics_endpoint or "disabled"
    running = "running" if profile.metrics_server_running else "stopped"
    return [
        "BioETL Metrics Diagnostics",
        f"  metrics_enabled: {str(profile.metrics_enabled).lower()}",
        f"  metrics_server_enabled: {str(profile.metrics_server_enabled).lower()}",
        f"  metrics_server_status: {running}",
        f"  metrics_endpoint: {endpoint}",
        f"  metrics_started_at: {started_at}",
        f"  metrics_server_mode: {profile.metrics_server_mode}",
        f"  pushgateway_mode: {profile.pushgateway_mode}",
        f"  pushgateway_gateway: {profile.pushgateway_gateway}",
        f"  tracing_enabled: {str(profile.tracing_enabled).lower()}",
        f"  audit_enabled: {str(profile.audit_enabled).lower()}",
        "",
        "Operator workflow:",
        "  inspect metrics/admin state: bioetl diagnostics metrics [--json]",
        "  inspect provider health: bioetl diagnostics health [--json]",
        (
            "  reconcile metric inventory: "
            "python -m scripts.engineering.qa report-observability-metric-inventory --json"
        ),
        (
            "  compare rules/dashboards: "
            "grafana/prometheus-rules/bioetl_observability.yml + shipped dashboard JSON"
        ),
        "  inspect one run: bioetl diagnostics run --run-id <run-id>",
        "  inspect checkpoint state: bioetl diagnostics checkpoint --pipeline <pipeline>",
    ]


@click.group()  # type: ignore[untyped-decorator]
def diagnostics() -> None:
    """Unified operator diagnostics across health, checkpoints, manifests, and quarantine."""


@diagnostics.command("guide")  # type: ignore[untyped-decorator]
def diagnostics_guide() -> None:
    """Show the canonical diagnostics discovery and routing guide."""
    _render_guide_lines(_build_diagnostics_guide_lines())


@diagnostics.command("health")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--provider",
    "-p",
    multiple=True,
    help="Provider name(s) to check; omit to check all configured providers",
)
@click.option(  # type: ignore[untyped-decorator]
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def diagnostics_health(provider: tuple[str, ...], output_json: bool) -> None:
    """Run provider health diagnostics from the unified operator entrypoint."""
    bundle = get_observability_diagnostics_bundle()

    async def _run() -> JsonDict:
        providers_list = list(provider) if provider else None
        summary = await bundle.health_service.check_providers(providers=providers_list)
        return summary.to_dict()

    results = asyncio.run(_run())
    _echo_health_results(results, output_json=output_json)
    if output_json:
        return
    if not all_health_results_healthy(results):
        raise SystemExit(ExitCode.FAIL)


@diagnostics.command("metrics")  # type: ignore[untyped-decorator]
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
def diagnostics_metrics(output_json: bool) -> None:
    """Show the canonical metrics/admin observability workflow summary."""
    profile = get_metrics_operator_profile()
    if output_json:
        click.echo(json.dumps(profile.to_dict(), indent=2, default=str))
        return
    _render_guide_lines(_build_metrics_profile_lines(profile))


@diagnostics.command("run")  # type: ignore[untyped-decorator]
@click.option("--run-id", required=True, help="Pipeline RUN_ID to inspect")  # type: ignore[untyped-decorator]
@click.option("--limit", default=100, show_default=True, help="Maximum audit entries")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_run(run_id: str, limit: int, output_format: str) -> None:
    """Inspect one pipeline run across audit and run-manifest diagnostics surfaces."""
    bundle = get_observability_diagnostics_bundle()

    async def _inspect() -> None:
        try:
            result = await bundle.workflow_service.inspect_audit_run(
                run_id, limit=limit
            )
        except ValueError as exc:
            echo_error("Run diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@diagnostics.command("checkpoint")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
@click.option("--run-id", default=None, help="Optional RUN_ID override")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--audit-limit",
    default=100,
    show_default=True,
    help="Maximum audit entries",
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_checkpoint(
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Inspect checkpoint state with correlated audit and run-manifest context."""
    bundle = get_observability_diagnostics_bundle()

    async def _inspect() -> None:
        try:
            result = await bundle.workflow_service.inspect_checkpoint_workflow(
                pipeline,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        except ValueError as exc:
            echo_error("Checkpoint diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@diagnostics.command("manifest")  # type: ignore[untyped-decorator]
@click.argument("identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_manifest(identifier: str, output_format: str) -> None:
    """Inspect one run manifest and its ledger diagnostics."""
    bundle = get_observability_diagnostics_bundle()
    _emit_manifest_payload(
        bundle.run_manifest_service,
        identifier=identifier,
        output_format=output_format,
    )


def _emit_manifest_payload(
    service: RunManifestInspectionService,
    *,
    identifier: str,
    output_format: str,
) -> None:
    """Resolve one manifest and emit it using the canonical renderer."""
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run-manifest diagnostics failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@diagnostics.command("quarantine")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
@click.option("--error-code", help="Scope stats to one error code")  # type: ignore[untyped-decorator]
@click.option("--run-id", help="Scope stats to one pipeline run ID")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
@click.option(  # type: ignore[untyped-decorator]
    "--group-by",
    type=click.Choice(
        [
            "reason-code",
            "field",
            "rule-type",
            "operator",
            "reason-code-field",
            "reason-signature",
        ],
        case_sensitive=False,
    ),
    help="Focused Silver reject grouping for operator triage",
)
@click.option(  # type: ignore[untyped-decorator]
    "--top",
    type=int,
    default=10,
    show_default=True,
    help="Maximum grouping entries to display",
)
def diagnostics_quarantine(
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
    group_by: str | None,
    top: int,
) -> None:
    """Inspect quarantine statistics from the unified operator entrypoint."""
    bundle = get_observability_diagnostics_bundle()
    resolved_error_code = "FILTERED_OUT_SILVER" if silver_filter_only else error_code
    _show_quarantine_stats(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=resolved_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=bundle.run_manifest_service if run_id else None,
    )


COMMANDS = (
    diagnostics_guide,
    diagnostics_health,
    diagnostics_metrics,
    diagnostics_run,
    diagnostics_checkpoint,
    diagnostics_manifest,
    diagnostics_quarantine,
)

================================================================================
File: __init__.py
Path: cli\commands\domains\health\__init__.py
================================================================================
"""Canonical health command domain package."""

from __future__ import annotations

__all__ = ["health"]


def __getattr__(name: str) -> object:
    if name == "health":
        from bioetl.interfaces.cli.commands.domains.health.command import health

        return health
    raise AttributeError(name)

================================================================================
File: command.py
Path: cli\commands\domains\health\command.py
================================================================================
"""Health-check CLI commands and health-server entrypoints."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
    build_health_result_lines,
    build_health_server_info_lines,
    render_health_results_json,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.health_api import HealthServerDependencies
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config import Settings

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"
_HEALTH_CHECKS_ERROR_TITLE = "Error running health checks"
_HEALTH_CHECKS_INTERRUPTED_MESSAGE = "Health checks interrupted by user (Ctrl+C)"


def get_health_service() -> HealthService:
    """Load the health service through composition on demand."""
    from bioetl.composition.health_api import get_health_service as _impl

    return _impl()


def get_health_server_dependencies() -> HealthServerDependencies:
    """Load health server dependencies through composition on demand."""
    from bioetl.composition.health_api import (
        get_health_server_dependencies as _impl,
    )

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load quarantine service through composition on demand."""
    from bioetl.composition.health_api import get_quarantine_service as _impl

    return _impl()


def get_settings() -> Settings:
    """Load runtime settings on demand."""
    from bioetl.infrastructure.config import get_settings as _impl

    return _impl()


def _start_metrics_server_via_interface(
    *,
    port: int,
    addr: str,
    fail_fast: bool,
    retry_count: int,
    retry_delay: float,
    logger: LoggerPort,
) -> bool:
    """Start the metrics server through the canonical observability facade."""
    from bioetl.interfaces.observability import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


# Backward-compatible patch point for existing tests and callers.
start_metrics_server = _start_metrics_server_via_interface


def _handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with the shared CLI execution policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def _provider_subject(provider: tuple[str, ...]) -> str:
    """Build a stable provider subject label for error handling."""
    return ",".join(provider) if provider else "all"


def _echo_health_server_info(host: str, port: int) -> None:
    """Print startup information for the health server command."""
    for line in build_health_server_info_lines(host, port):
        click.echo(line)


def _start_health_observability(logger: LoggerPort | None = None) -> None:
    """Start the Prometheus metrics server for long-lived health mode."""
    settings = get_settings()
    if not (
        settings.observability.metrics_enabled
        and settings.observability.metrics_server_enabled
    ):
        if logger is not None:
            logger.info(
                "health_server_metrics_disabled",
                metrics_enabled=settings.observability.metrics_enabled,
                metrics_server_enabled=settings.observability.metrics_server_enabled,
            )
        return

    start_metrics = start_metrics_server
    started = start_metrics(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=settings.observability.metrics_fail_fast,
        retry_count=settings.observability.metrics_retry_count,
        retry_delay=settings.observability.metrics_retry_delay,
        logger=logger,
    )
    if logger is not None:
        logger.info(
            "health_server_metrics_ready",
            metrics_started=started,
            metrics_port=settings.metrics_port,
            metrics_addr=settings.metrics_addr,
        )


async def _run_health_server(host: str, port: int) -> None:
    """Start and keep the health server alive until interrupted.

    Args:
        host: IP address to bind the server to.
        port: TCP port for the health server to listen on.
    """
    from bioetl.interfaces.http.health_server import HealthServer

    deps = get_health_server_dependencies()
    _start_health_observability()
    quarantine_service: QuarantineService | None = None
    try:
        quarantine_service = get_quarantine_service()
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        # Why: Health probes must stay available even when quarantine storage
        # setup fails; explorer endpoints remain disabled in that case.
        quarantine_service = None
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        quarantine_service=quarantine_service,
    )
    try:
        await server.start()
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()
        if quarantine_service is not None:
            await quarantine_service.aclose()
        click.echo("\nHealth server stopped.")


def _execute_health_server(host: str, port: int) -> None:
    """Execute health server coroutine with CLI error policy.

    Args:
        host: IP address the server will bind to.
        port: TCP port the server will listen on.
    """
    coro = _run_health_server(host=host, port=port)
    try:
        asyncio.run(coro)
    except asyncio.CancelledError:
        # Why: tests and shutdown callers may use CancelledError as the stop
        # signal for the long-lived health server loop. The coroutine already
        # performs cleanup and emits the shutdown line in its finally block.
        return
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_DOMAIN_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_UNEXPECTED_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK)
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


async def _run_health_checks(provider: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """Execute health checks and return results as serializable dictionary.

    Args:
        provider: Tuple of provider names to check. Empty tuple checks all providers.

    Returns:
        Dict mapping provider names to their health check result dicts.
    """
    service = get_health_service()
    providers_list = list(provider) if provider else None
    summary = await service.check_providers(providers=providers_list)
    results: dict[str, dict[str, str]] = summary.to_dict()
    return results


def _execute_health_checks(
    provider: tuple[str, ...],
) -> dict[str, dict[str, str]] | None:
    """Execute health checks with CLI error policy and return results.

    Args:
        provider: Tuple of provider names to check. Empty tuple checks all providers.

    Returns:
        Dict mapping provider names to health check results, or None if an exception
        was handled and the process will exit.
    """
    providers_subject = _provider_subject(provider)
    coro = _run_health_checks(provider)
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_DOMAIN_ERROR",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_SIGINT",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_UNEXPECTED_ERROR",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _render_health_results(
    results: dict[str, dict[str, str]],
    *,
    output_json: bool,
) -> None:
    """Render health check output and exit with mapped status code.

    Args:
        results: Dict mapping provider names to health check result dicts.
        output_json: When True, outputs results as JSON; otherwise uses a
            human-readable text format.
    """
    all_healthy = all_health_results_healthy(results)
    if output_json:
        click.echo(render_health_results_json(results))
        sys.exit(ExitCode.OK if all_healthy else ExitCode.FAIL)

    for line in build_health_result_lines(results):
        click.echo(line)

    if all_healthy:
        click.echo("\nAll providers healthy.")
        sys.exit(ExitCode.OK)
    click.echo("\nSome providers unhealthy.")
    sys.exit(ExitCode.FAIL)


@click.group()  # type: ignore[untyped-decorator]
def health() -> None:
    """Health check and monitoring operations."""


@health.command("server")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--host",
    default="127.0.0.1",
    help="Host to bind to. Use 0.0.0.0 to expose externally.",
    show_default=True,
)
@click.option(  # type: ignore[untyped-decorator]
    "--port",
    "-p",
    default=8081,
    type=int,
    help="Port to listen on.",
    show_default=True,
)
def health_server_command(host: str, port: int) -> None:
    """Start the HTTP health server.

    Runs an HTTP server that exposes health check endpoints:

    \b
    - GET /health         - Overall health status
    - GET /health/live    - Kubernetes liveness probe
    - GET /health/ready   - Kubernetes readiness probe
    - GET /health/providers - Detailed provider status
    - GET /ops/quarantine/filtered-records - Silver reject list (read-only)
    - GET /ops/quarantine/filtered-record/{payload_hash} - Silver reject detail
    - GET /ops/quarantine/filtered-stats - Silver reject aggregates
    - GET /ops/quarantine/filter-options - Explorer variable options

    Example:
        bioetl health server --port 8081

    Args:
        host: IP address to bind the server to (e.g., '127.0.0.1' or '0.0.0.0').
        port: TCP port for the health server to listen on.
    """
    _echo_health_server_info(host, port)
    _execute_health_server(host, port)


@health.command("check")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--provider",
    "-p",
    multiple=True,
    help="Provider(s) to check. If not specified, checks all configured providers.",
)
@click.option(  # type: ignore[untyped-decorator]
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON.",
)
def health_check(provider: tuple[str, ...], output_json: bool) -> None:
    """Run health checks on data providers.

    Checks connectivity and health status of configured data providers
    (ChEMBL, PubChem, UniProt, etc.).

    Example:
        bioetl health check
        bioetl health check --provider chembl --provider pubchem
        bioetl health check --json

    Args:
        provider: Tuple of provider names to check (e.g., ('chembl', 'pubchem')).
            Checks all configured providers when empty.
        output_json: When True, outputs health check results as JSON.
    """
    click.echo("Running health checks...")
    results = _execute_health_checks(provider)
    if results is None:
        return
    _render_health_results(results, output_json=output_json)


COMMANDS = (health_server_command,)

__all__ = ["health"]

================================================================================
File: metrics_server_integration.py
Path: cli\commands\domains\health\metrics_server_integration.py
================================================================================
"""Metrics server integration for CLI commands.

Provides utilities for starting the Prometheus metrics HTTP server
alongside pipeline operations. The metrics server exposes Prometheus-compatible
metrics endpoint while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition layer for server startup, keeping side-effects out of bootstrap.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

__all__ = [
    "ensure_metrics_server_started",
    "metrics_server_context",
]


def ensure_metrics_server_started() -> bool:
    """Start the metrics server through composition on demand."""
    from bioetl.composition.execution_api import ensure_metrics_server_started as _impl

    return bool(_impl())


@contextmanager
def metrics_server_context() -> Iterator[bool]:
    """Context manager that ensures metrics server is started.

    Starts the Prometheus metrics HTTP server before yielding.
    The server runs as a daemon thread and doesn't need explicit shutdown.

    Yields:
        True if server was started, False if disabled.

    Example:
        with metrics_server_context():
            # Metrics server is running
            await run_pipeline()
        # Server continues running (daemon thread)

    Returns:
        Iterator over results.
    """
    # Re-exported from entrypoints, use directly
    started = ensure_metrics_server_started()
    yield started


COMMANDS = (metrics_server_context,)

================================================================================
File: rendering.py
Path: cli\commands\domains\health\rendering.py
================================================================================
"""Pure rendering helpers for health CLI commands."""

from __future__ import annotations

import json

__all__ = [
    "all_health_results_healthy",
    "build_health_result_lines",
    "build_health_server_info_lines",
    "render_health_results_json",
]


def build_health_server_info_lines(host: str, port: int) -> list[str]:
    """Build startup lines for the health server command."""
    return [
        f"Starting health server on http://{host}:{port}",
        "Endpoints:",
        f"  - http://{host}:{port}/health",
        f"  - http://{host}:{port}/health/live",
        f"  - http://{host}:{port}/health/ready",
        f"  - http://{host}:{port}/health/providers",
        "\nPress Ctrl+C to stop.",
    ]


def all_health_results_healthy(results: dict[str, dict[str, str]]) -> bool:
    """Return True when every provider result is healthy."""
    return all(
        result.get("status", "unknown") == "healthy" for result in results.values()
    )


def render_health_results_json(results: dict[str, dict[str, str]]) -> str:
    """Render health results as formatted JSON."""
    return json.dumps(results, indent=2)


def _health_status_icon(status: str) -> str:
    """Map provider health status to CLI icon."""
    if status == "healthy":
        return "[OK]"
    if status == "degraded":
        return "[WARN]"
    return "[FAIL]"


def build_health_result_lines(results: dict[str, dict[str, str]]) -> list[str]:
    """Build human-readable health check output lines."""
    lines: list[str] = []
    for provider, result in results.items():
        status = result.get("status", "unknown")
        line = f"  {_health_status_icon(status)} {provider}: {status}"
        if "latency_ms" in result:
            line += f" ({result['latency_ms']}ms)"
        if "error" in result:
            line += f" - {result['error']}"
        lines.append(line)
    return lines

================================================================================
File: server_integration.py
Path: cli\commands\domains\health\server_integration.py
================================================================================
"""Health server integration for CLI commands.

Provides utilities for running the health server alongside long-running
pipeline operations. The health server exposes Kubernetes-compatible
health probes while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition entrypoints for dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)

if TYPE_CHECKING:
    from bioetl.interfaces.http.health_server import HealthServer


# Default port for health server during pipeline operations
DEFAULT_HEALTH_SERVER_PORT = 8081


@asynccontextmanager
async def health_server_context(
    enabled: bool,
    host: str = "127.0.0.1",
    port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> AsyncIterator[HealthServer | None]:
    """Run health server for the context lifetime when enabled.

    Yields the running HealthServer for the duration of the async context,
    then stops it on exit. If the server fails to bind (port in use), a
    warning is printed and None is yielded so the pipeline continues.

    Args:
        enabled: When False, yields None immediately without starting a server.
        host: IP address to bind to. Defaults to localhost.
        port: TCP port to listen on. Defaults to DEFAULT_HEALTH_SERVER_PORT.
    """
    if not enabled:
        yield None
        return

    # Import here to avoid circular imports and keep interfaces layer clean
    from bioetl.composition.health_api import (
        get_health_server_dependencies,
        get_quarantine_service,
    )
    from bioetl.interfaces.http.health_server import HealthServer

    # Get dependencies from composition root (proper DI)
    deps = get_health_server_dependencies()
    try:
        quarantine_service = get_quarantine_service()
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        # Why: keep health probes available during pipeline runs even if
        # quarantine explorer dependencies are temporarily unavailable.
        quarantine_service = None

    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        quarantine_service=quarantine_service,
    )

    try:
        await server.start()
    except OSError:
        if quarantine_service is not None:
            await quarantine_service.aclose()
        click.echo(
            f"Warning: Health server failed to bind to {host}:{port} "
            f"(port in use). Pipeline will continue without health server.",
            err=True,
        )
        yield None
        return

    try:
        yield server
    finally:
        await server.stop()
        if quarantine_service is not None:
            await quarantine_service.aclose()


def add_health_server_options(cmd: click.Command) -> click.Command:
    """Add health server options to a Click command.

    Adds --health-server/--no-health-server and --health-port options
    to the given command.

    Args:
        cmd: Click command to add options to.

    Returns:
        Modified command with health server options.
    """
    cmd = click.option(
        "--health-server/--no-health-server",
        default=True,
        help="Enable/disable HTTP health server during execution (default: enabled).",
        show_default=True,
    )(cmd)

    cmd = click.option(
        "--health-port",
        type=int,
        default=DEFAULT_HEALTH_SERVER_PORT,
        help="Port for the HTTP health server.",
        show_default=True,
    )(cmd)

    return cmd


def echo_health_server_info(enabled: bool, port: int, host: str = "127.0.0.1") -> None:
    """Output health server status information.

    Args:
        enabled: Whether health server is enabled.
        port: Port the server is listening on.
        host: Host the server is bound to (default: 127.0.0.1 for security).
    """
    if enabled:
        click.echo(f"Health server: http://{host}:{port}/health")


COMMANDS = (add_health_server_options, echo_health_server_info, health_server_context)

__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "add_health_server_options",
    "echo_health_server_info",
    "health_server_context",
]

================================================================================
File: __init__.py
Path: cli\commands\domains\maintenance\__init__.py
================================================================================
"""Canonical maintenance command domain package."""

from __future__ import annotations

__all__ = ["maintenance"]


def __getattr__(name: str) -> object:
    if name == "maintenance":
        from bioetl.interfaces.cli.commands.domains.maintenance.command import (
            maintenance,
        )

        return maintenance
    raise AttributeError(name)

================================================================================
File: archive.py
Path: cli\commands\domains\maintenance\archive.py
================================================================================
"""Archive command for BioETL CLI.

Implements table archival to cold storage.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_info

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

__all__ = [
    "archive_command",
    "get_lifecycle_service",
]


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.resources_api import get_lifecycle_service as _impl

    return _impl()


def _handle_archive_failure(
    exc: BaseException,
    *,
    reason_code: str,
    table: str,
) -> None:
    """Handle archive command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_MAINTENANCE_ARCHIVE_DOMAIN_ERROR').
        table: Table name used as subject value in the structured error context.
    """
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="table",
        subject_value=table,
        domain_error_title="Maintenance archive failed with domain error",
        unexpected_error_title="Unexpected error during maintenance archive",
        interrupted_message="Maintenance archive interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


@click.command("archive")  # type: ignore[untyped-decorator]
@click.argument("table")  # type: ignore[untyped-decorator]
@click.argument("target_path")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--remove-source",
    is_flag=True,
    help="Remove source table after archiving",
)
def archive_command(table: str, target_path: str, remove_source: bool) -> None:
    """Archive Delta table to cold storage.

    TABLE: Table name to archive

    TARGET_PATH: Destination path for archive

    Examples:

        bioetl maintenance archive chembl.activity /archive/chembl

        bioetl maintenance archive chembl.activity /archive/chembl --remove-source

    Args:
        table: Table.
        target_path: File path for target.
        remove_source: Whether to remove source.
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        files_archived = await lifecycle.archive(
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        echo_info(f"Archived {files_archived} files to {target_path}")

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_DOMAIN_ERROR",
            table=table,
        )
    except KeyboardInterrupt as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_SIGINT",
            table=table,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_UNEXPECTED_ERROR",
            table=table,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

================================================================================
File: cleanup.py
Path: cli\commands\domains\maintenance\cleanup.py
================================================================================
"""Cleanup commands for BioETL CLI.

Implements Bronze layer cleanup per RULES.md retention policy.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.maintenance_api import get_bronze_cleanup_service
from bioetl.composition.resources_api import (
    preview_cleanup as preview_pipeline_cleanup,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_info,
    format_bytes,
)

__all__ = [
    "bronze_cleanup_command",
    "cleanup_preview_command",
    "get_bronze_cleanup_service",
    "preview_pipeline_cleanup",
]

_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE = (
    "Maintenance cleanup-preview failed with domain error"
)
_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE = (
    "Unexpected error during maintenance cleanup-preview"
)
_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE = (
    "Maintenance cleanup-preview interrupted by user (Ctrl+C)"
)


def _handle_cleanup_failure(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str = "target",
    subject_value: str = "bronze",
    domain_error_title: str = "Maintenance bronze-cleanup failed with domain error",
    unexpected_error_title: str = (
        "Unexpected error during maintenance bronze-cleanup"
    ),
    interrupted_message: str = (
        "Maintenance bronze-cleanup interrupted by user (Ctrl+C)"
    ),
) -> None:
    """Handle cleanup command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


@click.command("bronze-cleanup")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "-r",
    "--retention-days",
    default=90,
    help="Remove files older than N days",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed",
)
def bronze_cleanup_command(retention_days: int, dry_run: bool) -> None:
    """Clean up old Bronze files (RULES.md 2.1 retention, default 90 days).

    Examples:

        bioetl maintenance bronze-cleanup

        bioetl maintenance bronze-cleanup --dry-run

        bioetl maintenance bronze-cleanup -r 30

    Args:
        retention_days: Retention days.
        dry_run: Dry run mode flag.
    """
    service = get_bronze_cleanup_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(
                f"Cleanup Bronze files older than {retention_days} days"
            )
        result = await service.cleanup(retention_days=retention_days, dry_run=dry_run)
        action = "Would remove" if dry_run else "Removed"
        echo_info(
            f"{action} {result.files_removed} files ({format_bytes(result.bytes_freed)})"
        )
        echo_info(f"{action} {result.directories_removed} empty directories")

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_UNEXPECTED_ERROR",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


@click.command("cleanup-preview")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline",
    required=True,
    help="Pipeline name to preview (e.g., chembl_activity)",
)
def cleanup_preview_command(pipeline: str) -> None:
    """Preview Silver/Gold cleanup scope for a pipeline (dry-run only).

    Examples:

        bioetl maintenance cleanup-preview --pipeline chembl_activity
    """

    async def _run() -> None:
        preview_result = await preview_pipeline_cleanup(pipeline)
        echo_dry_run_prefix(f"Cleanup preview for pipeline: {pipeline}")
        echo_cleanup_preview(preview_result)

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_DOMAIN_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_SIGINT",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

================================================================================
File: command.py
Path: cli\commands\domains\maintenance\command.py
================================================================================
"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module is a thin orchestrator that imports and registers commands.
"""

from __future__ import annotations

import click

from bioetl.interfaces.cli.commands.domains.maintenance.archive import archive_command
from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
    bronze_cleanup_command,
    cleanup_preview_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.plan import plan_command
from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
    vacuum_all_command,
    vacuum_command,
)

__all__ = [
    "maintenance",
]


@click.group()  # type: ignore[untyped-decorator]
def maintenance() -> None:
    """Maintenance operations for Delta tables."""


# Register all maintenance subcommands
maintenance.add_command(vacuum_command)
maintenance.add_command(vacuum_all_command)
maintenance.add_command(archive_command)
maintenance.add_command(bronze_cleanup_command)
maintenance.add_command(cleanup_preview_command)
maintenance.add_command(plan_command)

================================================================================
File: plan.py
Path: cli\commands\domains\maintenance\plan.py
================================================================================
"""Contract migration planner command for BioETL CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services import ContractMigrationService

__all__ = [
    "get_contract_migration_service",
    "plan_command",
]

_NONE_LINE = "  none"


def get_contract_migration_service() -> ContractMigrationService:
    """Load the contract migration service through composition on demand."""
    from bioetl.composition.maintenance_api import (
        get_contract_migration_service as _impl,
    )

    return _impl()


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_block(value: object) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    if isinstance(value, list):
        if not value:
            return ["[]"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    return [_format_scalar(value)]


def _append_section(
    lines: list[str],
    title: str,
    items: Iterable[tuple[str, object]],
) -> None:
    filtered = [(label, value) for label, value in items if value not in (None, [], {})]
    if not filtered:
        return
    if lines:
        lines.append("")
    lines.append(title)
    for label, value in filtered:
        rendered = _format_block(value)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)


def _append_transitions(lines: list[str], transitions: object) -> None:
    if not isinstance(transitions, list):
        return
    if lines:
        lines.append("")
    lines.append("Transitions")
    if not transitions:
        lines.append(_NONE_LINE)
        return
    for entry in transitions:
        if not isinstance(entry, dict):
            lines.append(f"  - {_format_scalar(entry)}")
            continue
        line = (
            "  - "
            f"{_format_scalar(entry.get('from_version'))} -> "
            f"{_format_scalar(entry.get('to_version'))}"
        )
        if entry.get("migration_guide") is not None:
            line += f" (guide: {_format_scalar(entry.get('migration_guide'))})"
        if entry.get("affects_hash") is True:
            line += " [affects_hash]"
        lines.append(line)


def _append_required_actions(lines: list[str], required_actions: object) -> None:
    if not isinstance(required_actions, list):
        return
    if lines:
        lines.append("")
    lines.append("Required Actions")
    if not required_actions:
        lines.append(_NONE_LINE)
        return
    for action in required_actions:
        if not isinstance(action, dict):
            lines.append(f"  - {_format_scalar(action)}")
            continue
        title = _format_scalar(action.get("title"))
        code = _format_scalar(action.get("code"))
        description = _format_scalar(action.get("description"))
        lines.append(f"  - {title} [{code}]")
        lines.append(f"    {description}")


def _append_notes(lines: list[str], notes: object) -> None:
    if not isinstance(notes, list):
        return
    if lines:
        lines.append("")
    lines.append("Notes")
    if not notes:
        lines.append(_NONE_LINE)
        return
    for note in notes:
        lines.append(f"  - {_format_scalar(note)}")


def _render_plan_payload(payload: dict[str, object]) -> str:
    lines: list[str] = []
    _append_section(
        lines,
        "Contract Migration Plan",
        (
            ("pipeline_name", payload.get("pipeline_name")),
            ("provider", payload.get("provider")),
            ("entity_type", payload.get("entity_type")),
            ("contract_ref", payload.get("contract_ref")),
            ("active_version", payload.get("active_version")),
            ("rollout_mode", payload.get("rollout_mode")),
            ("affects_hash", payload.get("affects_hash")),
            ("read_order", payload.get("read_order")),
            ("write_versions", payload.get("write_versions")),
            ("shadow_versions", payload.get("shadow_versions")),
            ("supported_versions", payload.get("supported_versions")),
        ),
    )
    _append_transitions(lines, payload.get("transitions"))
    _append_required_actions(lines, payload.get("required_actions"))
    _append_notes(lines, payload.get("notes"))
    return "\n".join(lines)


def _handle_plan_failure(
    exc: BaseException, *, pipeline: str, reason_code: str
) -> None:
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title="Contract migration planning failed with domain error",
        unexpected_error_title="Unexpected error during maintenance plan",
        interrupted_message="Maintenance plan interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


@click.command("plan")  # type: ignore[untyped-decorator]
@click.argument("pipeline")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    show_default=True,
    help="Output format for the planner payload.",
)
def plan_command(pipeline: str, output_format: str) -> None:
    """Plan contract migration actions for a pipeline.

    PIPELINE: Registered pipeline name (for example, ``chembl_activity``).
    """
    service = get_contract_migration_service()
    try:
        plan = service.plan_pipeline(pipeline)
        emit_inspection_payload(
            plan.to_payload(),
            output_format,
            text_renderer=_render_plan_payload,
        )
    except BioETLError as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_UNEXPECTED_ERROR",
        )

================================================================================
File: vacuum.py
Path: cli\commands\domains\maintenance\vacuum.py
================================================================================
"""Vacuum commands for BioETL CLI.

Implements vacuum operations for Delta tables storage reclamation.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    echo_vacuum_all_summary,
    echo_vacuum_result,
)

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.vacuum_service import VacuumService

__all__ = [
    "get_lifecycle_service",
    "get_vacuum_service",
    "vacuum_all_command",
    "vacuum_command",
]

_VACUUM_DOMAIN_ERROR_TITLE = "Maintenance vacuum failed with domain error"
_VACUUM_UNEXPECTED_ERROR_TITLE = "Unexpected error during maintenance vacuum"
_VACUUM_INTERRUPTED_MESSAGE = "Maintenance vacuum interrupted by user (Ctrl+C)"

_VACUUM_ALL_DOMAIN_ERROR_TITLE = "Maintenance vacuum-all failed with domain error"
_VACUUM_ALL_UNEXPECTED_ERROR_TITLE = "Unexpected error during maintenance vacuum-all"
_VACUUM_ALL_INTERRUPTED_MESSAGE = "Maintenance vacuum-all interrupted by user (Ctrl+C)"


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.resources_api import get_lifecycle_service as _impl

    return _impl()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through composition on demand."""
    from bioetl.composition.maintenance_api import get_vacuum_service as _impl

    return _impl()


def _handle_maintenance_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle maintenance command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_MAINTENANCE_VACUUM_DOMAIN_ERROR').
        target: Target identifier (e.g., table name or layer) used in error context.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.
        interrupted_message: Message displayed when KeyboardInterrupt is caught.
    """
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


@click.command("vacuum")  # type: ignore[untyped-decorator]
@click.argument("table")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
def vacuum_command(table: str, retention_days: int, dry_run: bool) -> None:
    """Vacuum Delta table to reclaim storage space.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        bioetl maintenance vacuum chembl.activity

        bioetl maintenance vacuum chembl.activity --dry-run

        bioetl maintenance vacuum chembl.activity -r 30

    Args:
        table: Table.
        retention_days: Retention days.
        dry_run: Dry run mode flag.
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(f"Would vacuum {table} (retention: {retention_days}d)")

        files_removed = await lifecycle.vacuum(
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        if dry_run:
            echo_info(f"Would remove {files_removed} files")
        else:
            echo_info(f"Removed {files_removed} files")

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_DOMAIN_ERROR",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_SIGINT",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_UNEXPECTED_ERROR",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


@click.command("vacuum-all")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(  # type: ignore[untyped-decorator]
    "--layer",
    type=click.Choice(["all", "silver", "gold"]),
    default="all",
    help="Which layer to vacuum (default: all)",
)
def vacuum_all_command(retention_days: int, dry_run: bool, layer: str) -> None:
    """Vacuum all Delta tables to reclaim storage space.

    Runs VACUUM on all registered Silver and Gold tables.

    Examples:

        bioetl maintenance vacuum-all

        bioetl maintenance vacuum-all --dry-run

        bioetl maintenance vacuum-all -r 30

        bioetl maintenance vacuum-all --layer silver

    Args:
        retention_days: Retention days.
        dry_run: Dry run mode flag.
        layer: Layer.
    """
    service = get_vacuum_service()
    tables_to_vacuum = service.collect_tables(layer)

    if not tables_to_vacuum:
        echo_info("No tables found to vacuum.")
        return

    async def _run() -> None:
        result = await service.vacuum_all(
            tables=tables_to_vacuum,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        for table_result in result.results:
            echo_vacuum_result(table_result, dry_run)

        echo_vacuum_all_summary(result)

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_DOMAIN_ERROR",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_SIGINT",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_UNEXPECTED_ERROR",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

================================================================================
File: __init__.py
Path: cli\commands\domains\quarantine\__init__.py
================================================================================
"""Canonical quarantine command domain package."""

from __future__ import annotations

__all__ = ["quarantine"]


def __getattr__(name: str) -> object:
    if name == "quarantine":
        from bioetl.interfaces.cli.commands.domains.quarantine.command import quarantine

        return quarantine
    raise AttributeError(name)

================================================================================
File: _run_scope_stats.py
Path: cli\commands\domains\quarantine\_run_scope_stats.py
================================================================================
"""Run-scoped quarantine statistics enrichment helpers."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types import JsonDict

__all__ = [
    "RunManifestInspectionServiceProtocol",
    "enrich_run_scoped_stats",
]


class RunManifestInspectionResultProtocol(Protocol):
    """Protocol for manifest inspection payloads used in CLI enrichment."""

    @property
    def ledger_entries(self) -> tuple[object, ...]:
        """Return the associated ledger entries."""


class RunManifestInspectionServiceProtocol(Protocol):
    """Protocol for control-plane manifest lookup used by quarantine CLI."""

    def show(self, identifier: str) -> RunManifestInspectionResultProtocol:
        """Resolve one manifest or run identifier."""


def _resolve_run_scoped_bronze_records(
    run_manifest_service: RunManifestInspectionServiceProtocol | None,
    *,
    run_id: str | None,
) -> int | None:
    """Resolve a Bronze denominator for one run from control-plane ledger data."""
    if run_manifest_service is None or run_id is None:
        return None
    try:
        inspection = run_manifest_service.show(run_id)
    except ValueError:
        return None

    bronze_records: int | None = None
    for entry in inspection.ledger_entries:
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def enrich_run_scoped_stats(
    stats: JsonDict,
    *,
    run_id: str | None,
    run_manifest_service: RunManifestInspectionServiceProtocol | None,
) -> JsonDict:
    """Add run-scoped metadata and optional Bronze denominator to stats."""
    if run_id is None:
        return stats

    stats["run_scope"] = {"run_id": run_id}
    silver = stats.get("silver_filter_rejects")
    if not isinstance(silver, dict):
        return stats

    bronze_records = _resolve_run_scoped_bronze_records(
        run_manifest_service,
        run_id=run_id,
    )
    if bronze_records is None:
        return stats

    silver_total = silver.get("total_count")
    if not isinstance(silver_total, int):
        return stats

    silver["bronze_records"] = bronze_records
    if bronze_records > 0:
        silver["bronze_ratio"] = silver_total / bronze_records
        silver["bronze_ratio_pct"] = (silver_total / bronze_records) * 100
    return stats

================================================================================
File: command.py
Path: cli\commands\domains\quarantine\command.py
================================================================================
"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
Provides error recovery dashboard functionality (ERR-001).
"""

from __future__ import annotations

import click

from bioetl.composition.control_plane_api import (
    get_run_manifest_service,
)
from bioetl.composition.health_api import (
    get_quarantine_service,
)
from bioetl.composition.resources_api import get_quarantine_manager
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _inspect_quarantine,
    _purge_quarantine,
    _replay_quarantine,
    _resolve_quarantine_record,
    _show_quarantine_stats,
)

SILVER_FILTER_ERROR_CODE = "FILTERED_OUT_SILVER"


@click.group()  # type: ignore[untyped-decorator]
def quarantine() -> None:
    """Manage quarantine (failed records)."""


@quarantine.command("inspect")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--limit", type=int, default=100, help="Maximum records to show"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Filter by error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id",
    help="Scope inspection to one pipeline run ID",
)
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
def quarantine_inspect(
    pipeline: str,
    limit: int,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
) -> None:
    """Inspect quarantined records for a pipeline."""
    resolved_error_code = SILVER_FILTER_ERROR_CODE if silver_filter_only else error_code
    _inspect_quarantine(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        limit=limit,
        error_code=resolved_error_code,
        run_id=run_id,
    )


@quarantine.command("stats")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--json", "output_json", is_flag=True, help="Output as JSON"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Scope stats to one error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id",
    help="Scope stats to one pipeline run ID",
)
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
@click.option(  # type: ignore[untyped-decorator]
    "--group-by",
    type=click.Choice(
        [
            "reason-code",
            "field",
            "rule-type",
            "operator",
            "reason-code-field",
            "reason-signature",
        ],
        case_sensitive=False,
    ),
    help="Focused Silver reject grouping for operator triage",
)
@click.option(  # type: ignore[untyped-decorator]
    "--top",
    type=int,
    default=10,
    show_default=True,
    help="Maximum grouping entries to display",
)
def quarantine_stats(
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
    group_by: str | None,
    top: int,
) -> None:
    """Show quarantine statistics dashboard for a pipeline."""
    resolved_error_code = SILVER_FILTER_ERROR_CODE if silver_filter_only else error_code
    _show_quarantine_stats(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=resolved_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=get_run_manifest_service() if run_id else None,
    )


@quarantine.command("replay")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Filter by error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--max-age-days", type=int, default=7, help="Max age of records to replay"
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run", is_flag=True, help="Show records without replaying"
)
def quarantine_replay(
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay (retry) quarantined records."""
    _replay_quarantine(
        get_quarantine_service(),
        pipeline=pipeline,
        error_code=error_code,
        max_age_days=max_age_days,
        dry_run=dry_run,
    )


@quarantine.command("purge")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--older-than-days", type=int, default=30, help="Delete records older than N days"
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run", is_flag=True, help="Show count without deleting"
)
@click.option(  # type: ignore[untyped-decorator]
    "--force", is_flag=True, help="Skip confirmation prompt"
)
def quarantine_purge(
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records."""
    _purge_quarantine(
        get_quarantine_service(),
        pipeline=pipeline,
        older_than_days=older_than_days,
        dry_run=dry_run,
        force=force,
    )


@quarantine.command("resolve")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--payload-hash", required=True, help="Payload hash of record to resolve"
)
@click.option(  # type: ignore[untyped-decorator]
    "--status", type=click.Choice(["IGNORED", "REPROCESSED"]), default="IGNORED"
)
def quarantine_resolve(pipeline: str, payload_hash: str, status: str) -> None:
    """Mark a quarantine record as resolved."""
    _resolve_quarantine_record(
        get_quarantine_service(),
        pipeline=pipeline,
        payload_hash=payload_hash,
        status=status,
    )


COMMANDS = (
    quarantine_inspect,
    quarantine_purge,
    quarantine_replay,
    quarantine_resolve,
    quarantine_stats,
)

__all__ = [
    "get_quarantine_manager",
    "get_quarantine_service",
    "quarantine",
]

================================================================================
File: execution.py
Path: cli\commands\domains\quarantine\execution.py
================================================================================
"""Execution policy helpers for quarantine CLI commands."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TypeVar

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

__all__ = [
    "QuarantineExecutionPolicy",
    "run_quarantine_async",
    "run_quarantine_sync",
]

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class QuarantineExecutionPolicy:
    """Typed execution policy for one quarantine CLI operation."""

    pipeline: str
    reason_prefix: str
    domain_error_title: str
    unexpected_error_title: str
    interrupted_message: str = "Quarantine command interrupted by user (Ctrl+C)"


def _handle_quarantine_failure(
    exc: BaseException,
    *,
    policy: QuarantineExecutionPolicy,
    reason_suffix: str,
) -> None:
    """Handle quarantine command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=f"{policy.reason_prefix}_{reason_suffix}",
        subject_key="pipeline",
        subject_value=policy.pipeline,
        domain_error_title=policy.domain_error_title,
        unexpected_error_title=policy.unexpected_error_title,
        interrupted_message=policy.interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def run_quarantine_async(
    coro: Coroutine[object, object, _T],
    *,
    policy: QuarantineExecutionPolicy,
) -> _T | None:
    """Run an async quarantine coroutine with typed exception policy."""
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="UNEXPECTED_ERROR",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def run_quarantine_sync(
    fn: Callable[[], _T],
    *,
    policy: QuarantineExecutionPolicy,
) -> _T | None:
    """Run a synchronous quarantine callable with typed exception policy."""
    try:
        return fn()
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="UNEXPECTED_ERROR",
        )
    return None

================================================================================
File: rendering.py
Path: cli\commands\domains\quarantine\rendering.py
================================================================================
"""Pure rendering helpers for quarantine CLI commands."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = [
    "build_purge_preview_lines",
    "build_quarantine_grouped_lines",
    "build_quarantine_stats_lines",
    "build_replay_preview_lines",
]


_GROUP_BY_TITLES = {
    "reason-code": "Reason Code",
    "field": "Field",
    "rule-type": "Rule Type",
    "operator": "Operator",
    "reason-code-field": "Reason Code + Field",
    "reason-signature": "Stable Signature",
}

_GROUP_BY_KEYS = {
    "reason-code": "by_reason_code",
    "field": "by_field",
    "rule-type": "by_rule_type",
    "operator": "by_operator",
    "reason-code-field": "by_reason_code_field",
    "reason-signature": "by_reason_signature",
}


def _append_group_lines(
    lines: list[str],
    *,
    values: dict[str, int],
    total: int,
    title: str,
    top: int,
) -> None:
    """Append one ranked grouping block to the output lines."""
    if not values:
        return
    lines.append(f"\n  {title}:")
    for label, count in sorted(
        values.items(),
        key=lambda item: (-item[1], item[0]),
    )[:top]:
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"    - {label}: {count} ({pct:.1f}%)")


def _append_error_code_lines(lines: list[str], *, by_error: object, total: int) -> None:
    if not isinstance(by_error, dict) or not by_error:
        return
    lines.append("\n  By Error Code:")
    for code, count in sorted(by_error.items(), key=lambda item: -item[1]):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"    - {code}: {count} ({pct:.1f}%)")


def _append_status_lines(lines: list[str], *, by_status: object, total: int) -> None:
    if not isinstance(by_status, dict) or not by_status:
        return
    lines.append("\n  By Status:")
    for status, count in sorted(by_status.items()):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"    - {status}: {count} ({pct:.1f}%)")


def _append_all_silver_filter_groupings(
    lines: list[str],
    *,
    silver_filter_stats: dict[str, object],
    silver_total: int,
    top: int,
) -> None:
    for title, key in (
        ("By Reason Code", "by_reason_code"),
        ("By Field", "by_field"),
        ("By Rule Type", "by_rule_type"),
        ("By Operator", "by_operator"),
        ("By Reason Code + Field", "by_reason_code_field"),
    ):
        values = silver_filter_stats.get(key, {})
        if not isinstance(values, dict):
            continue
        _append_group_lines(
            lines,
            values=values,
            total=silver_total,
            title=title,
            top=top,
        )


def _append_focused_silver_filter_grouping(
    lines: list[str],
    *,
    silver_filter_stats: dict[str, object],
    silver_total: int,
    top: int,
    group_by: str,
) -> None:
    values = silver_filter_stats.get(_GROUP_BY_KEYS[group_by], {})
    if isinstance(values, dict) and values:
        lines.append("\n  Focused Silver Reject Grouping:")
        _append_group_lines(
            lines,
            values=values,
            total=silver_total,
            title=_GROUP_BY_TITLES[group_by],
            top=top,
        )
        return
    lines.append("\n  Focused Silver Reject Grouping: no structured values available.")


def _append_silver_filter_lines(
    lines: list[str],
    *,
    silver_filter_stats: object,
    total: int,
    top: int,
    group_by: str | None,
) -> None:
    if not isinstance(silver_filter_stats, dict):
        return
    silver_total = silver_filter_stats.get("total_count", 0)
    if not isinstance(silver_total, int) or silver_total <= 0:
        return
    pct = (silver_total / total * 100) if total > 0 else 0
    lines.append(
        f"\n  Silver Filter Rejects: {silver_total} ({pct:.1f}% of quarantine)"
    )
    bronze_records = silver_filter_stats.get("bronze_records")
    bronze_ratio_pct = silver_filter_stats.get("bronze_ratio_pct")
    if (
        isinstance(bronze_records, int)
        and bronze_records > 0
        and isinstance(bronze_ratio_pct, (int, float))
    ):
        lines.append(
            f"  Silver Rejects vs Bronze: {silver_total}/{bronze_records} ({bronze_ratio_pct:.1f}%)"
        )
    if group_by is None:
        _append_all_silver_filter_groupings(
            lines,
            silver_filter_stats=silver_filter_stats,
            silver_total=silver_total,
            top=top,
        )
        return
    _append_focused_silver_filter_grouping(
        lines,
        silver_filter_stats=silver_filter_stats,
        silver_total=silver_total,
        top=top,
        group_by=group_by,
    )


def build_quarantine_stats_lines(stats: JsonDict, *, pipeline: str) -> list[str]:
    """Build human-readable quarantine statistics lines."""
    return build_quarantine_grouped_lines(stats, pipeline=pipeline, top=10)


def build_quarantine_grouped_lines(
    stats: JsonDict,
    *,
    pipeline: str,
    top: int,
    group_by: str | None = None,
) -> list[str]:
    """Build quarantine statistics with optional focused Silver reject grouping."""
    lines = [
        "",
        f"{'=' * 50}",
        f"  Quarantine Dashboard: {pipeline}",
        f"{'=' * 50}",
    ]
    run_scope = stats.get("run_scope")
    if isinstance(run_scope, dict):
        run_id = run_scope.get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            lines.append(f"\n  Run ID Scope: {run_id}")

    total = stats.get("total_count", stats.get("total_records", 0))
    lines.append(f"\n  Total Records: {total}")
    _append_error_code_lines(
        lines, by_error=stats.get("by_error_code", {}), total=total
    )
    _append_status_lines(lines, by_status=stats.get("by_status", {}), total=total)
    _append_silver_filter_lines(
        lines,
        silver_filter_stats=stats.get("silver_filter_rejects", {}),
        total=total,
        top=top,
        group_by=group_by,
    )

    lines.append(f"\n{'=' * 50}\n")
    return lines


def build_replay_preview_lines(records: list[JsonDict]) -> list[str]:
    """Build dry-run preview lines for quarantine replay."""
    lines = [f"\nWould replay {len(records)} record(s):\n"]
    for index, record in enumerate(records[:10], 1):
        payload_hash = record.get("payload_hash")
        hash_display = payload_hash[:16] if isinstance(payload_hash, str) else "—"
        lines.append(
            f"  {index}. Error: {record.get('error_code')} | Hash: {hash_display}..."
        )
    if len(records) > 10:
        lines.append(f"  ... and {len(records) - 10} more")
    return lines


def build_purge_preview_lines(
    *, older_than_days: int, total_count: object
) -> list[str]:
    """Build dry-run preview lines for quarantine purge."""
    return [
        f"\nWould purge records older than {older_than_days} days.",
        f"Current total in quarantine: {total_count}",
        "\nUse without --dry-run to actually purge.",
    ]

================================================================================
File: support.py
Path: cli\commands\domains\quarantine\support.py
================================================================================
"""Shared helpers for quarantine CLI commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Protocol, TypeVar

import click

from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.interfaces.cli.commands.domains.quarantine._run_scope_stats import (
    RunManifestInspectionServiceProtocol,
    enrich_run_scoped_stats,
)
from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
    QuarantineExecutionPolicy,
    run_quarantine_async,
    run_quarantine_sync,
)
from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
    build_purge_preview_lines,
    build_quarantine_grouped_lines,
    build_replay_preview_lines,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_info,
    echo_quarantine_record,
)

_T = TypeVar("_T")

__all__ = [
    "_inspect_quarantine",
    "_purge_quarantine",
    "_replay_quarantine",
    "_resolve_quarantine_record",
    "_show_quarantine_stats",
]


class _QuarantineManager(Protocol):
    """Protocol for quarantine manager methods used by CLI."""

    async def inspect(
        self,
        limit: int,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> list[JsonDict]:
        """Return quarantined records."""
        ...

    async def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict:
        """Return aggregate quarantine statistics."""
        ...


class _QuarantineService(Protocol):
    """Protocol for quarantine service methods used by CLI."""

    def replay(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        max_age_days: int,
    ) -> list[JsonDict]:
        """Find records eligible for replay."""
        ...

    def mark_as_reprocessed(self, records: list[JsonDict]) -> int:
        """Mark replay candidates as reprocessed."""
        ...

    async def get_stats(self, pipeline: str) -> JsonDict:
        """Return stats for purge preview."""
        ...

    def purge(self, *, pipeline: str, older_than_days: int) -> int:
        """Purge old quarantine records."""
        ...

    def update_status(self, payload_hash: str, status: QuarantineRecordStatus) -> bool:
        """Update one quarantine record status."""
        ...


@dataclass(frozen=True, slots=True)
class _QuarantineCommandContext:
    """Shared execution context for one quarantine CLI command."""

    pipeline: str

    def run_async(
        self,
        coro: Coroutine[object, object, _T],
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> _T | None:
        """Run one async quarantine operation with a consistent policy."""
        return run_quarantine_async(
            coro,
            policy=self._build_policy(
                reason_prefix=reason_prefix,
                domain_error_title=domain_error_title,
                unexpected_error_title=unexpected_error_title,
            ),
        )

    def run_sync(
        self,
        fn: Callable[[], _T],
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> _T | None:
        """Run one sync quarantine operation with a consistent policy."""
        return run_quarantine_sync(
            fn,
            policy=self._build_policy(
                reason_prefix=reason_prefix,
                domain_error_title=domain_error_title,
                unexpected_error_title=unexpected_error_title,
            ),
        )

    def _build_policy(
        self,
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> QuarantineExecutionPolicy:
        """Build the shared execution policy for one operation."""
        return QuarantineExecutionPolicy(
            pipeline=self.pipeline,
            reason_prefix=reason_prefix,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )


def _render_stats_dashboard(
    stats: JsonDict,
    *,
    pipeline: str,
    top: int,
    group_by: str | None,
) -> None:
    """Render human-readable quarantine statistics."""
    for line in build_quarantine_grouped_lines(
        stats,
        pipeline=pipeline,
        top=top,
        group_by=group_by,
    ):
        click.echo(line)


def _inspect_quarantine(
    manager: _QuarantineManager,
    *,
    pipeline: str,
    limit: int,
    error_code: str | None,
    run_id: str | None = None,
) -> None:
    """Inspect quarantined records for one pipeline."""
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")
    context = _QuarantineCommandContext(pipeline=pipeline)

    async def _inspect() -> list[JsonDict]:
        inspect_kwargs: dict[str, object] = {
            "limit": limit,
            "error_code": error_code,
        }
        if run_id is not None:
            inspect_kwargs["run_id"] = run_id
        return await manager.inspect(**inspect_kwargs)

    records = context.run_async(
        _inspect(),
        reason_prefix="CLI_QUARANTINE_INSPECT",
        domain_error_title="Failed to inspect quarantine with domain error",
        unexpected_error_title="Unexpected error during quarantine inspect",
    )
    if records is None:
        return
    if not records:
        echo_info("No records found.")
        return
    for record in records:
        echo_quarantine_record(record)


def _show_quarantine_stats(
    manager: _QuarantineManager,
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    top: int = 10,
    group_by: str | None = None,
    run_id: str | None = None,
    run_manifest_service: RunManifestInspectionServiceProtocol | None = None,
) -> None:
    """Display quarantine statistics for one pipeline."""
    context = _QuarantineCommandContext(pipeline=pipeline)

    async def _stats() -> JsonDict:
        return await manager.get_stats(error_code=error_code, run_id=run_id)

    stats = context.run_async(
        _stats(),
        reason_prefix="CLI_QUARANTINE_STATS",
        domain_error_title="Failed to get stats",
        unexpected_error_title="Failed to get stats",
    )
    if stats is None:
        return
    stats = enrich_run_scoped_stats(
        stats,
        run_id=run_id,
        run_manifest_service=run_manifest_service,
    )
    if output_json:
        click.echo(json.dumps(stats, indent=2))
        return
    _render_stats_dashboard(stats, pipeline=pipeline, top=top, group_by=group_by)


def _replay_quarantine(
    service: _QuarantineService,
    *,
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay or preview replay for quarantine records."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    records = context.run_sync(
        lambda: service.replay(
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        ),
        reason_prefix="CLI_QUARANTINE_REPLAY",
        domain_error_title="Failed to replay quarantine records with domain error",
        unexpected_error_title="Unexpected error during quarantine replay",
    )
    if records is None:
        return
    if not records:
        echo_info("No records found for replay.")
        return
    if dry_run:
        for line in build_replay_preview_lines(records):
            click.echo(line)
        return

    click.echo(f"\nReplaying {len(records)} record(s)...")
    marked_count = context.run_sync(
        lambda: service.mark_as_reprocessed(records),
        reason_prefix="CLI_QUARANTINE_REPLAY_MARK",
        domain_error_title="Failed to mark replayed records with domain error",
        unexpected_error_title="Unexpected error during quarantine replay mark",
    )
    if marked_count is None:
        return
    click.echo(f"Marked {marked_count} record(s) as REPROCESSED.")
    echo_info("Records are ready for reprocessing by the pipeline.")


def _purge_quarantine(
    service: _QuarantineService,
    *,
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records or preview the purge."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    if dry_run:

        async def _get_stats() -> JsonDict:
            return await service.get_stats(pipeline)

        stats = context.run_async(
            _get_stats(),
            reason_prefix="CLI_QUARANTINE_PURGE_PREVIEW",
            domain_error_title="Failed to preview quarantine purge with domain error",
            unexpected_error_title="Unexpected error during quarantine purge preview",
        )
        if stats is None:
            return
        total = stats.get("total_count", 0)
        for line in build_purge_preview_lines(
            older_than_days=older_than_days,
            total_count=total,
        ):
            click.echo(line)
        return

    if not force:
        click.confirm(
            f"Delete quarantine records older than {older_than_days} days for {pipeline}?",
            abort=True,
        )

    count = context.run_sync(
        lambda: service.purge(
            pipeline=pipeline,
            older_than_days=older_than_days,
        ),
        reason_prefix="CLI_QUARANTINE_PURGE",
        domain_error_title="Failed to purge quarantine records with domain error",
        unexpected_error_title="Unexpected error during quarantine purge",
    )
    if count is None:
        return
    click.echo(f"Purged {count} record(s) from quarantine.")


def _resolve_quarantine_record(
    service: _QuarantineService,
    *,
    pipeline: str,
    payload_hash: str,
    status: str,
) -> None:
    """Resolve one quarantine record by payload hash."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    success = context.run_sync(
        lambda: service.update_status(
            payload_hash,
            QuarantineRecordStatus[status],
        ),
        reason_prefix="CLI_QUARANTINE_RESOLVE",
        domain_error_title="Failed to resolve quarantine record with domain error",
        unexpected_error_title="Unexpected error during quarantine resolve",
    )
    if success is None:
        return
    if success:
        click.echo(f"Record {payload_hash} marked as {status}.")
        return
    echo_error(f"Record not found: {payload_hash}")
    sys.exit(ExitCode.FAIL)

================================================================================
File: __init__.py
Path: cli\commands\domains\run\__init__.py
================================================================================
"""Canonical run-command domain package."""

from __future__ import annotations

__all__ = ["run"]


def __getattr__(name: str) -> object:
    if name == "run":
        from bioetl.interfaces.cli.commands.domains.run.command import run

        return run
    raise AttributeError(name)

================================================================================
File: command.py
Path: cli\commands\domains\run\command.py
================================================================================
"""Run command for BioETL CLI."""

from __future__ import annotations

import asyncio
import sys
from functools import partial
from typing import TYPE_CHECKING, NoReturn

import click

from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started as _ensure_metrics_server_started_impl,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info as _echo_health_server_info_impl,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    health_server_context as _health_server_context_impl,
)
from bioetl.interfaces.cli.commands.domains.run.command_entrypoint import (
    build_run_click_command,
)
from bioetl.interfaces.cli.commands.domains.run.command_policy import (
    RunCommandInput,
    handle_cli_failure,
    map_status_to_exit_code,
    run_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run.result_flow import (
    finalize_run_result as _finalize_run_result_impl,
)
from bioetl.interfaces.cli.commands.domains.run.result_flow import (
    present_run_health_info as _present_run_health_info_impl,
)
from bioetl.interfaces.cli.commands.domains.run.result_presenter import (
    echo_run_result as _echo_run_result,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    build_run_command_input as _build_run_command_input_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    build_run_pipeline_callable as _build_run_pipeline_callable_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    run_pipeline_async as _run_pipeline_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    run_prepared_request_async as _run_prepared_request_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run.service_access import (
    get_cli_run_orchestration_service as _get_cli_run_orchestration_service_impl,
)
from bioetl.interfaces.cli.commands.domains.run.support import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    resolve_context_registry,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services import RunOptions, RunResult
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        CliRunOptionsInput,
        RunExecutionRequest,
    )
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "build_run_options",
    "execute_run",
    "get_cli_run_orchestration_service",
    "handle_cli_failure",
    "run",
    "validate_options",
]

# Inventory of retained run-command seams. Update tests alongside intentional changes.
_RUN_CANONICAL_BOUNDARY_SEAMS = (
    "get_cli_run_orchestration_service",
    "_build_run_command_input",
    "_build_run_pipeline_callable",
    "_map_status_to_exit_code",
    "_present_run_health_info",
    "_finalize_run_result",
    "_run_pipeline_async",
    "_run_prepared_request_async",
)

_RUN_COMPATIBILITY_SEAMS = (
    "_get_runner_logger",
    "_handle_destructive_run_confirmation",
    "_validate_start_offset",
    "echo_health_server_info",
    "ensure_metrics_server_started",
    "health_server_context",
    "get_pipeline_runner_service",
)


def get_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Return process-local run orchestration service (lazy cached accessor seam)."""
    return _get_cli_run_orchestration_service_impl()


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> object:
    """Resolve the pipeline runner service lazily for runtime helpers."""
    from bioetl.composition.execution_api import (
        get_pipeline_runner_service as _impl,
    )

    return _impl(registry=registry)


def _exit_with_code(code: int | str | None = None) -> NoReturn:
    """Typed wrapper around sys.exit for policy flow injection."""
    sys.exit(code)


def validate_options(start_offset: int | None, run_type: str, resume: bool) -> None:
    """Validate --start-offset constraints; sys.exit on error."""
    validation = get_cli_run_orchestration_service().validate_start_offset(
        start_offset=start_offset,
        run_type=run_type,
        resume=resume,
    )
    if validation.is_valid:
        return
    if validation.error_message is not None:
        echo_error(validation.error_message)
        sys.exit(ExitCode.CONFIG_ERROR)


def build_run_options(options_input: CliRunOptionsInput) -> RunOptions:
    """Build RunOptions from CLI parameters."""
    return get_cli_run_orchestration_service().build_options(options_input)


def execute_run(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Execute run and flush metrics at command boundary."""
    from bioetl.composition.execution_api import push_metrics_to_gateway

    def _flush_metrics_safely(*, pipeline_name: str) -> None:
        try:
            push_metrics_to_gateway(pipeline_name=pipeline_name)
        except Exception:
            # Metrics publication must never turn a completed CLI run into failure.
            return

    return get_cli_run_orchestration_service().execute_pipeline(
        request=request,
        run_pipeline_async=_build_run_pipeline_callable(
            registry=registry,
            run_pipeline_async_callable=_run_pipeline_async,
        ),
        run_coroutine=asyncio.run,
        flush_metrics=_flush_metrics_safely,
    )


# PATCH_POINT: retained thin helper aliases for tests and CLI patch seams.
_build_run_command_input = _build_run_command_input_impl
_map_status_to_exit_code = map_status_to_exit_code
_build_run_pipeline_callable = _build_run_pipeline_callable_impl
_get_pipeline_runner_service_impl = get_pipeline_runner_service


def _present_run_health_info(request: RunExecutionRequest) -> None:
    """Render health-server info for a prepared run request."""
    _present_run_health_info_impl(
        request,
        info_presenter=echo_health_server_info,
    )


def _finalize_run_result(result: RunResult) -> None:
    """Render CLI run result and terminate with the canonical exit code."""
    _finalize_run_result_impl(
        result,
        presenter=_echo_run_result,
        status_mapper=_map_status_to_exit_code,
        exit_func=_exit_with_code,
    )


def _run_command_with_cli_policy(
    ctx: click.Context,
    cli_input: RunCommandInput,
) -> None:
    """Execute the prepared run command through the canonical CLI policy path."""
    registry = resolve_context_registry(ctx)
    service = get_cli_run_orchestration_service()
    run_command_flow(
        cli_input=cli_input,
        service=service,
        execute_run=partial(execute_run, registry=registry),
        health_info_presenter=_present_run_health_info,
        result_finalizer=_finalize_run_result,
        exit_func=_exit_with_code,
    )


async def _run_pipeline_async(
    pipeline: str,
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Run pipeline asynchronously via service."""
    return await _run_pipeline_async_impl(
        pipeline,
        options,
        health_server_enabled=health_server_enabled,
        health_port=health_port,
        registry=registry,
        metrics_starter=ensure_metrics_server_started,
        health_context_factory=health_server_context,
        runner_service_factory=get_pipeline_runner_service,
    )


async def _run_prepared_request_async(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Execute a prepared CLI run request via the canonical async runtime path."""
    return await _run_prepared_request_async_impl(
        request,
        registry=registry,
        run_pipeline_async_callable=_run_pipeline_async,
    )


def _run_callback(
    ctx: click.Context,
    pipeline: str,
    run_type: str,
    resume: bool,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    health_server: bool,
    health_port: int,
    enable_tracing: bool | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    exact_replay: bool = False,
) -> None:
    """Canonical callback implementation for the run Click command."""
    if exact_replay and not use_cached_bronze:
        echo_warning(
            "Strict exact replay requires snapshot-backed cached Bronze inputs; "
            "without --use-cached-bronze this run is outside the strict exact-replay boundary."
        )
    cli_input_kwargs = {
        "pipeline": pipeline,
        "run_type": run_type,
        "resume": resume,
        "start_offset": start_offset,
        "limit": limit,
        "input_csv": input_csv,
        "filter_column": filter_column,
        "filter_field": filter_field,
        "dry_run": dry_run,
        "yes": yes,
        "vacuum_after_run": vacuum_after_run,
        "vacuum_retention_days": vacuum_retention_days,
        "debug": debug,
        "health_server": health_server,
        "health_port": health_port,
        "enable_tracing": enable_tracing,
        "use_cached_bronze": use_cached_bronze,
        "cached_bronze_date": cached_bronze_date,
        "cached_bronze_path": cached_bronze_path,
        "replay_of_run_id": replay_of_run_id,
        "replay_of_manifest_id": replay_of_manifest_id,
    }
    if exact_replay:
        cli_input_kwargs["exact_replay"] = True

    dispatch_cli_callback(
        ctx,
        build_cli_input=lambda: _build_run_command_input(**cli_input_kwargs),
        run_with_cli_policy=_run_command_with_cli_policy,
    )


run = build_run_click_command(
    validate_pipeline_name=validate_pipeline_name,
    default_health_server_port=DEFAULT_HEALTH_SERVER_PORT,
    run_callback=_run_callback,
)


# ---------------------------------------------------------------------------
# PATCH_POINT: compatibility-only re-exports for tests and legacy patch seams.
# ---------------------------------------------------------------------------
echo_health_server_info = _echo_health_server_info_impl
ensure_metrics_server_started = _ensure_metrics_server_started_impl
health_server_context = _health_server_context_impl
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_validate_start_offset = validate_options

================================================================================
File: command_entrypoint.py
Path: cli\commands\domains\run\command_entrypoint.py
================================================================================
"""Click entrypoint builder for the run CLI command."""

from __future__ import annotations

from collections.abc import Callable

import click

from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    with_debug_option,
    with_dry_run_option,
    with_health_server_options,
    with_limit_option,
    with_run_type_option,
    with_yes_option,
)

CommandCallback = Callable[..., object]
CommandDecorator = Callable[[CommandCallback], CommandCallback]
CommandDecoratorFactory = Callable[..., CommandDecorator]


def _add_core_options(
    validate_pipeline_name: Callable[..., object],
) -> Callable:
    """Add core CLI options to the command."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--pipeline",
            callback=validate_pipeline_name,
            required=True,
            help="Pipeline to run",
        )(cmd)
        cmd = with_run_type_option("Type of run")(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--resume",
            is_flag=True,
            help="Resume from last checkpoint state; not a strict exact replay",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--start-offset",
            type=int,
            default=None,
            help="Start extraction from specific record offset (skips checkpoint). "
            "Use after crash to resume from known position.",
        )(cmd)
        return cmd

    return decorator


def _add_filter_options() -> Callable:
    """Add filter-related CLI options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_limit_option("Maximum number of records to process")(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--input-csv",
            type=click.Path(exists=True),
            help="Path to CSV file with filter IDs",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--filter-column",
            type=str,
            help="Column name in CSV containing filter IDs (default: 'id')",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--filter-field",
            type=str,
            help="API field name to filter by (default: 'molecule_chembl_id')",
        )(cmd)
        return cmd

    return decorator


def _add_execution_options() -> Callable:
    """Add execution control options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_dry_run_option(
            "Preview cleanup without execution (for rebuild/backfill)"
        )(cmd)
        cmd = with_yes_option("Skip confirmation prompt for rebuild/backfill")(cmd)
        return cmd

    return decorator


def _add_vacuum_options() -> Callable:
    """Add Delta table vacuum options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--vacuum-after-run",
            is_flag=True,
            default=None,
            help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--vacuum-retention-days",
            type=int,
            default=None,
            help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
        )(cmd)
        return cmd

    return decorator


def _add_debug_options(default_health_server_port: int) -> Callable:
    """Add debugging and monitoring options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_debug_option()(cmd)
        cmd = with_health_server_options(default_health_server_port)(cmd)
        return cmd

    return decorator


def _add_tracing_options() -> Callable:
    """Add tracing configuration options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--tracing/--no-tracing",
            "enable_tracing",
            default=None,
            help="Override distributed tracing for this run",
        )(cmd)
        return cmd

    return decorator


def _add_cache_options() -> Callable:
    """Add Bronze cache options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--use-cached-bronze/--no-cached-bronze",
            "use_cached_bronze",
            default=False,
            help="Load data from Bronze cache instead of API",
            show_default=True,
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--cached-bronze-date",
            type=str,
            default=None,
            help="Filter Bronze cache by date (YYYY-MM-DD)",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--cached-bronze-path",
            type=click.Path(exists=True),
            default=None,
            help="Explicit path to Bronze cache directory",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--exact-replay/--no-exact-replay",
            "exact_replay",
            default=False,
            help="Request strict exact replay with snapshot-backed inputs; not the same as --resume or rebuild",
            show_default=True,
        )(cmd)
        return cmd

    return decorator


def _add_replay_parentage_options() -> Callable:
    """Add explicit replay ancestry options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--replay-of-run-id",
            type=str,
            default=None,
            help="Explicit parent run_id when this execution is an exact replay",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--replay-of-manifest-id",
            type=str,
            default=None,
            help="Explicit parent manifest_id when this execution is an exact replay",
        )(cmd)
        return cmd

    return decorator


def build_run_click_command(
    *,
    validate_pipeline_name: Callable[..., object],
    default_health_server_port: int,
    run_callback: Callable[..., None],
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run``."""

    @click.command()  # type: ignore[untyped-decorator]
    @click.pass_context  # type: ignore[untyped-decorator]
    def run_command(ctx: click.Context, **kwargs) -> None:
        """Run an ETL pipeline."""
        run_callback(ctx, **kwargs)

    # Apply all option groups
    run_command = _add_core_options(validate_pipeline_name)(run_command)
    run_command = _add_filter_options()(run_command)
    run_command = _add_execution_options()(run_command)
    run_command = _add_vacuum_options()(run_command)
    run_command = _add_debug_options(default_health_server_port)(run_command)
    run_command = _add_tracing_options()(run_command)
    run_command = _add_cache_options()(run_command)
    run_command = _add_replay_parentage_options()(run_command)

    return run_command


__all__ = ["build_run_click_command"]

================================================================================
File: command_policy.py
Path: cli\commands\domains\run\command_policy.py
================================================================================
"""Policy helpers for run command error handling and control flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn, Protocol

import click

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.run.support import (
    handle_destructive_run_confirmation,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    ExecutionFailureReasonCodes,
    execute_with_cli_failure_policy,
    finalize_cli_execution,
    map_run_status_to_exit_code,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        RunExecutionRequest,
    )
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

__all__ = [
    "RunCommandInput",
    "execute_run_step",
    "finalize_run_step",
    "handle_cli_failure",
    "handle_destructive_step",
    "map_status_to_exit_code",
    "prepare_run_request",
    "run_command_flow",
]


class RunExecutorCallable(Protocol):
    """Callable contract for synchronous pipeline execution from CLI."""

    def __call__(self, request: RunExecutionRequest) -> RunResult: ...


class ResultPresenterCallable(Protocol):
    """Callable contract to render run result output."""

    def __call__(self, result: RunResult) -> None: ...


class ResultFinalizerCallable(Protocol):
    """Callable contract to present a run result and terminate accordingly."""

    def __call__(self, result: RunResult) -> None: ...


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


class HealthInfoPresenterCallable(Protocol):
    """Callable contract to render health-server info for a prepared request."""

    def __call__(self, request: RunExecutionRequest) -> None: ...


@dataclass(frozen=True, slots=True)
class RunCommandInput:
    """Normalized CLI inputs for the run command control flow."""

    pipeline: str
    run_type: str
    resume: bool
    start_offset: int | None
    limit: int | None
    input_csv: str | None
    filter_column: str | None
    filter_field: str | None
    dry_run: bool
    yes: bool
    vacuum_after_run: bool | None
    vacuum_retention_days: int | None
    debug: bool
    health_server: bool
    health_port: int
    enable_tracing: bool | None
    use_cached_bronze: bool
    cached_bronze_date: str | None
    cached_bronze_path: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    exact_replay: bool = False


def prepare_run_request(
    *,
    service: CliRunOrchestrationService,
    command_input: RunCommandInput,
    exit_func: ExitCallable,
) -> RunExecutionRequest:
    """Validate raw CLI inputs and build the prepared request for execution."""
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        CliRunOptionsInput,
        CliRunPreparationInput,
    )

    preparation = service.prepare_execution_request(
        CliRunPreparationInput(
            pipeline=command_input.pipeline,
            options=CliRunOptionsInput(
                run_type=command_input.run_type,
                resume=command_input.resume,
                start_offset=command_input.start_offset,
                limit=command_input.limit,
                input_csv=command_input.input_csv,
                filter_column=command_input.filter_column,
                filter_field=command_input.filter_field,
                dry_run=command_input.dry_run,
                vacuum_after_run=command_input.vacuum_after_run,
                vacuum_retention_days=command_input.vacuum_retention_days,
                debug=command_input.debug,
                enable_tracing=command_input.enable_tracing,
                use_cached_bronze=command_input.use_cached_bronze,
                cached_bronze_date=command_input.cached_bronze_date,
                cached_bronze_path=command_input.cached_bronze_path,
                replay_of_run_id=command_input.replay_of_run_id,
                replay_of_manifest_id=command_input.replay_of_manifest_id,
                exact_replay=command_input.exact_replay,
            ),
            health_server=command_input.health_server,
            health_port=command_input.health_port,
        )
    )
    if preparation.request is not None:
        return preparation.request
    if preparation.error_message is not None:
        echo_error(preparation.error_message)
    exit_func(ExitCode.CONFIG_ERROR)
    raise RuntimeError("unreachable: exit_func is expected to terminate")


def handle_cli_failure(
    exc: BaseException,
    *,
    pipeline: str,
    reason_code: str,
) -> None:
    """Handle CLI failures with consistent reason_code semantics.

    Routes cleanup-preview errors to a simplified formatter and delegates all
    other exceptions to the shared execution_policy handler which calls sys.exit.

    Args:
        exc: Exception caught at the CLI command boundary.
        pipeline: Pipeline name for structured error context.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_RUN_DOMAIN_ERROR').
    """
    if reason_code.startswith("CLI_CLEANUP_PREVIEW"):
        echo_error(
            "Error previewing cleanup",
            (
                f"{exc} "
                f"(reason_code={reason_code}, pipeline={pipeline}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        return

    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title="Pipeline execution failed with domain error",
        unexpected_error_title="Unexpected error during pipeline execution",
        interrupted_message="Pipeline interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def map_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map pipeline status and error type to CLI exit code.

    Args:
        status: PipelineRunResult enum value (SUCCESS, FAILED, SHUTDOWN, DRY_RUN).
        error_type: Exception class name from the failed run; used to select a
            specific exit code when status is FAILED. None for non-failure statuses.

    Returns:
        ExitCode corresponding to the pipeline run status and optional error type.
    """
    return map_run_status_to_exit_code(status, error_type)


def handle_destructive_step(
    *,
    pipeline: str,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Run destructive confirmation/preview step with CLI error policy.

    Args:
        pipeline: Pipeline name for confirmation messages and error context.
        run_type: Type of run (e.g., 'rebuild', 'backfill'); only those types trigger
            the confirmation/preview flow.
        dry_run: When True, shows a cleanup preview and returns False without running.
        yes: When True, skips the interactive confirmation prompt.

    Returns:
        True if pipeline execution should continue, False if cancelled or dry-run
        preview was shown.
    """
    try:
        return handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes)
    except click.Abort:
        raise
    except BioETLError as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
        )
        return False
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
        )
        return False


def run_command_flow(
    *,
    cli_input: RunCommandInput,
    service: CliRunOrchestrationService,
    execute_run: RunExecutorCallable,
    health_info_presenter: HealthInfoPresenterCallable,
    result_finalizer: ResultFinalizerCallable,
    exit_func: ExitCallable,
) -> None:
    """Execute the full run-command policy flow from normalized CLI input."""
    if not handle_destructive_step(
        pipeline=cli_input.pipeline,
        run_type=cli_input.run_type,
        dry_run=cli_input.dry_run,
        yes=cli_input.yes,
    ):
        return

    request = prepare_run_request(
        service=service,
        command_input=cli_input,
        exit_func=exit_func,
    )
    finalize_cli_execution(
        health_info_presenter=lambda: health_info_presenter(request),
        execute=lambda: execute_run_step(
            request=request,
            execute_run=execute_run,
        ),
        result_finalizer=result_finalizer,
    )


def execute_run_step(
    *,
    request: RunExecutionRequest,
    execute_run: RunExecutorCallable,
) -> RunResult:
    """Run pipeline execution step with CLI failure mapping.

    Delegates to the provided executor and maps all exception types to
    structured CLI failure handling (which calls sys.exit on failure).

    Args:
        request: Prepared CLI run request.
        execute_run: Callable that synchronously runs the pipeline and returns RunResult.

    Returns:
        RunResult with pipeline execution status and metrics.
    """
    result = execute_with_cli_failure_policy(
        lambda: execute_run(request),
        subject=request.pipeline,
        reason_codes=ExecutionFailureReasonCodes(
            config="CLI_RUN_CONFIG_ERROR",
            domain="CLI_RUN_DOMAIN_ERROR",
            interrupted="CLI_RUN_SIGINT",
            unexpected="CLI_RUN_UNEXPECTED_ERROR",
        ),
        failure_handler=lambda exc, subject, reason_code: handle_cli_failure(
            exc,
            pipeline=subject,
            reason_code=reason_code,
        ),
    )
    if result is not None:
        return result
    raise RuntimeError("unreachable: handle_cli_failure is expected to terminate")


def finalize_run_step(
    *,
    run_result: RunResult,
    result_finalizer: ResultFinalizerCallable,
) -> None:
    """Finalize CLI execution for a completed run result.

    Args:
        run_result: RunResult from the completed pipeline execution.
        result_finalizer: Callable that renders the result and terminates the CLI.
    """
    result_finalizer(run_result)

================================================================================
File: result_flow.py
Path: cli\commands\domains\run\result_flow.py
================================================================================
"""Private result/presentation helpers for CLI run command finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
    )
    from bioetl.interfaces.cli.exit_codes import ExitCode


def present_run_health_info(
    request: RunExecutionRequest,
    *,
    info_presenter: Callable[[bool, int], None] = echo_health_server_info,
) -> None:
    """Render health-server info for a prepared run request."""
    info_presenter(request.health_server, request.health_port)


def finalize_run_result(
    result: RunResult,
    *,
    presenter: Callable[[RunResult], None],
    status_mapper: Callable[[PipelineRunResult, str | None], ExitCode],
    exit_func: Callable[[int | str | None], NoReturn],
) -> NoReturn:
    """Present run result and exit using mapped status code."""
    presenter(result)
    exit_func(status_mapper(result.status, result.error_type))

================================================================================
File: result_presenter.py
Path: cli\commands\domains\run\result_presenter.py
================================================================================
"""Presentation helpers for run command output."""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = ["echo_run_result"]


def echo_run_result(result: RunResult) -> None:
    """Output run result message and execution counters.

    Prints a human-readable summary of the pipeline run to stdout (or stderr
    for failures). Covers SUCCESS, DRY_RUN, SHUTDOWN, and FAILED statuses.

    Args:
        result: RunResult containing pipeline status, record counts, and run metadata.
    """
    short_run_id = result.run_id[:8] if len(result.run_id) > 8 else result.run_id

    if result.status == PipelineRunResult.SUCCESS:
        echo_info(f"Pipeline completed successfully (run_id: {short_run_id})")
        echo_info(f"  - Bronze records:      {result.records_fetched}")
        echo_info(f"  - Silver records:      {result.records_silver}")
        if result.records_gold > 0:
            echo_info(f"  - Gold records:        {result.records_gold}")
        if result.records_filtered_out > 0:
            echo_info(f"  - Silver filter rejects: {result.records_filtered_out}")
        else:
            echo_info("  - Silver filter rejects: 0")
        if result.records_quarantined > 0:
            echo_info(f"  - Quarantined (DQ):    {result.records_quarantined}")
        else:
            echo_info("  - Quarantined (DQ):    0")
        return

    if result.status == PipelineRunResult.DRY_RUN:
        echo_info(f"Dry-run completed (no changes made) (run_id: {short_run_id})")
        return

    if result.status == PipelineRunResult.SHUTDOWN:
        echo_warning(f"Pipeline was gracefully shut down (run_id: {short_run_id})")
        echo_info(f"  - Processed so far:    {result.records_fetched}")
        return

    if result.status == PipelineRunResult.FAILED:
        echo_error(
            f"Pipeline failed (run_id: {short_run_id})",
            result.error_message or "Unknown error",
        )
        echo_info(f"  - Processed before failure: {result.records_fetched}")

================================================================================
File: runtime_helpers.py
Path: cli\commands\domains\run\runtime_helpers.py
================================================================================
"""Private runtime helpers for CLI run command orchestration."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)
from bioetl.interfaces.cli.commands.domains.run.command_policy import RunCommandInput

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Protocol

    from bioetl.application.services.execution.cli_run_orchestration_contracts import (
        RunPreparedPipelineCallable,
    )
    from bioetl.composition.registry_api import PipelineRegistry

    class PipelineRunnerService(Protocol):
        """Protocol for pipeline runner services used by CLI runtime helpers."""

        async def run(
            self,
            pipeline: str,
            *,
            options: RunOptions,
        ) -> RunResult: ...


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Resolve the pipeline runner service lazily for CLI runtime helpers."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as _impl

    return _impl(registry=registry)


def build_run_command_input(
    *,
    pipeline: str,
    run_type: str,
    resume: bool,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    health_server: bool,
    health_port: int,
    enable_tracing: bool | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
    exact_replay: bool = False,
) -> RunCommandInput:
    """Build normalized CLI payload for policy-based execution."""
    return RunCommandInput(
        pipeline=pipeline,
        run_type=run_type,
        resume=resume,
        start_offset=start_offset,
        limit=limit,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        dry_run=dry_run,
        yes=yes,
        vacuum_after_run=vacuum_after_run,
        vacuum_retention_days=vacuum_retention_days,
        debug=debug,
        health_server=health_server,
        health_port=health_port,
        enable_tracing=enable_tracing,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        exact_replay=exact_replay,
    )


async def run_pipeline_async(
    pipeline: str,
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
    *,
    metrics_starter: Callable[[], bool | None] = ensure_metrics_server_started,
    health_context_factory: Callable[
        ..., AbstractAsyncContextManager[object]
    ] = health_server_context,
    runner_service_factory: Callable[
        ..., PipelineRunnerService
    ] = get_pipeline_runner_service,
) -> RunResult:
    """Execute run pipeline request through service with health/metrics context."""
    metrics_starter()
    async with health_context_factory(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = runner_service_factory(registry=registry)
        return await service.run(pipeline, options=options)


async def run_prepared_request_async(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
    *,
    run_pipeline_async_callable: Callable[
        ..., Awaitable[RunResult]
    ] = run_pipeline_async,
) -> RunResult:
    """Execute a prepared request through the canonical runtime helper path."""
    return await run_pipeline_async_callable(
        request.pipeline,
        request.options,
        health_server_enabled=request.health_server,
        health_port=request.health_port,
        registry=registry,
    )


def build_run_pipeline_callable(
    registry: PipelineRegistry | None = None,
    *,
    run_pipeline_async_callable: Callable[
        ..., Awaitable[RunResult]
    ] = run_pipeline_async,
) -> RunPreparedPipelineCallable:
    """Return a stable async callable for prepared execution requests."""

    async def _run(request: RunExecutionRequest) -> RunResult:
        return await run_prepared_request_async(
            request,
            registry=registry,
            run_pipeline_async_callable=run_pipeline_async_callable,
        )

    return _run

================================================================================
File: service_access.py
Path: cli\commands\domains\run\service_access.py
================================================================================
"""Private service accessor seam for CLI run command orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

_cli_run_orchestration_service: CliRunOrchestrationService | None = None


def get_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Return process-local run orchestration service (lazy cached accessor seam)."""
    global _cli_run_orchestration_service
    if _cli_run_orchestration_service is None:
        from bioetl.application.services.execution.cli_run_orchestration_service import (
            CliRunOrchestrationService,
        )

        _cli_run_orchestration_service = CliRunOrchestrationService()
    return _cli_run_orchestration_service


__all__ = ["get_cli_run_orchestration_service"]

================================================================================
File: support.py
Path: cli\commands\domains\run\support.py
================================================================================
"""Helper functions for the run command.

Provides validation, confirmation, and preview utilities for pipeline execution.
These are CLI-layer responsibilities separated for maintainability.
"""

from __future__ import annotations

import asyncio
import io
import sys
from functools import cache
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError

__all__ = [
    "build_cli_registry",
    "get_runner_logger",
    "handle_destructive_run_confirmation",
    "preview_cleanup",
    "resolve_context_registry",
    "show_cleanup_preview",
    "validate_pipeline_name",
]
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    build_failure_context,
    render_failure_context,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_warning,
)

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.ports import LoggerPort


@cache
def _load_pipeline_registry_type() -> type[PipelineRegistry]:
    """Resolve PipelineRegistry lazily so command imports stay lightweight."""
    from bioetl.composition.registry_api import PipelineRegistry

    return PipelineRegistry


def build_cli_registry() -> PipelineRegistry:
    """Compatibility seam for tests that patch CLI registry construction."""
    from bioetl.interfaces.cli.registry_helpers import build_cli_registry as _impl

    return _impl()


async def preview_cleanup(pipeline: str) -> object:
    """Compatibility seam for cleanup preview patched by CLI dry-run tests."""
    from bioetl.composition.resources_api import preview_cleanup as _impl

    return await _impl(pipeline)


def resolve_context_registry(
    click_context: click.Context | None = None,
) -> PipelineRegistry | None:
    """Return the explicit registry carried by Click context, if any."""
    if click_context is None:
        click_context = click.get_current_context(silent=True)
    if click_context is None or click_context.obj is None:
        return None
    pipeline_registry_type = _load_pipeline_registry_type()
    if not isinstance(click_context.obj, pipeline_registry_type):
        return None
    return click_context.obj


def validate_pipeline_name(
    click_context: click.Context | None,
    _param: click.Parameter | None,
    value: str,
) -> str:
    """Validate pipeline name against the registry at runtime.

    Args:
        click_context: Click context; if ``click_context.obj`` is a ``PipelineRegistry``,
            it is used directly, otherwise falls back to a fresh CLI registry.
        _param: Click parameter (unused).
        value: Pipeline name to validate.

    Returns:
        Validated pipeline name.

    Raises:
        click.BadParameter: If pipeline name is not in registry.
    """
    registry = resolve_context_registry(click_context)
    if registry is None:
        registry = build_cli_registry()
    available = registry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


def get_runner_logger(runner: PipelineRunner) -> LoggerPort | None:
    """Get logger from runner with fallback.

    Args:
        runner: PipelineRunner instance.

    Returns:
        Logger instance (LoggerPort) or None if not found.
    """
    logger = getattr(runner, "logger", None)
    if logger is None:
        logger = getattr(runner, "_logger", None)
    return logger


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Args:
        pipeline: Pipeline name.
    """
    preview_result = await preview_cleanup(pipeline)
    echo_cleanup_preview(preview_result)


def show_cleanup_preview(pipeline: str) -> None:
    """Show cleanup preview synchronously.

    Args:
        pipeline: Pipeline name.
    """
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except BioETLError as exc:
        failure_context = build_failure_context(
            exc,
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
        )
        echo_error(
            "Error previewing cleanup",
            render_failure_context(failure_context),
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        failure_context = build_failure_context(
            exc,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
        )
        echo_error(
            "Error previewing cleanup",
            render_failure_context(failure_context),
        )


def handle_destructive_run_confirmation(
    pipeline: str, run_type: str, dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for rebuild/backfill runs.

    Args:
        pipeline: Pipeline name.
        run_type: Type of run.
        dry_run: Whether this is a dry run.
        yes: Whether to skip confirmation.

    Returns:
        True if should continue with pipeline execution, False if should exit early.
    """
    if run_type not in ("rebuild", "backfill"):
        return True

    if dry_run:
        echo_dry_run_prefix(f"Would clear data for pipeline: {pipeline}")
        echo_dry_run_prefix(f"Run type: {run_type}")
        show_cleanup_preview(pipeline)
        return False

    if not yes:
        echo_warning(f"{run_type} will clear existing data for {pipeline}.")
        stdin = click.get_text_stream("stdin")
        try:
            interactive_stdin = stdin.isatty()
        except (AttributeError, OSError, ValueError, io.UnsupportedOperation):
            interactive_stdin = False
        if not interactive_stdin:
            raise click.Abort()
        if not click.confirm("Do you want to continue?", default=None):
            echo_info("Operation cancelled.")
            sys.exit(ExitCode.OK)

    return True

================================================================================
File: __init__.py
Path: cli\commands\domains\run_all\__init__.py
================================================================================
"""Canonical run-all command domain package."""

from __future__ import annotations

__all__ = ["run_all"]


def __getattr__(name: str) -> object:
    if name == "run_all":
        from bioetl.interfaces.cli.commands.domains.run_all.command import run_all

        return run_all
    raise AttributeError(name)

================================================================================
File: command.py
Path: cli\commands\domains\run_all\command.py
================================================================================
"""Run-all CLI command."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.application.services import (
    RunOptions,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.domains.run.support import resolve_context_registry
from bioetl.interfaces.cli.commands.domains.run_all.command_entrypoint import (
    build_run_all_click_command,
)
from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
    build_run_all_command_input,
    exit_with_code,
    handle_run_all_cli_failure,
    run_all_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    RunAllBatchExecutionRequest,
    RunAllPolicyRequest,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    run_all_pipelines_async as _run_all_pipelines_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    run_batch_with_policy as _run_batch_with_policy_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    emit_run_all_listing,
    emit_run_all_preview,
    should_prompt_for_destructive_run,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    determine_batch_exit_code as _determine_exit_code,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    echo_batch_summary as _echo_batch_summary_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    filter_pipelines_by_provider as _filter_pipelines_by_provider,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    get_available_providers as _get_available_providers,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    handle_destructive_confirmation as _handle_destructive_confirmation_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    validate_provider as _validate_provider,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info
from bioetl.interfaces.cli.registry_helpers import build_cli_registry

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as _impl

    return _impl(registry=registry)


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server.

    Args:
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server_enabled: When True, starts the HTTP health server before
            pipeline execution. Defaults to True.
        health_port: TCP port the health server listens on. Defaults to
            DEFAULT_HEALTH_SERVER_PORT.

    Returns:
        BatchRunResult aggregating results from all pipeline runs.
    """
    return await _run_all_pipelines_async_impl(
        RunAllBatchExecutionRequest(
            pipelines=pipelines,
            options=options,
            health_server_enabled=health_server_enabled,
            health_port=health_port,
            registry=registry,
        ),
        get_pipeline_runner_service_fn=get_pipeline_runner_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        health_server_context_factory=health_server_context,
    )


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary.

    Args:
        result: BatchRunResult with aggregate counts for the completed batch.
        dry_run: When True, prints a dry-run preview summary instead of execution stats.
    """
    _echo_batch_summary_impl(
        result=result,
        dry_run=dry_run,
        info_printer=echo_info,
        error_printer=echo_error,
    )


def _handle_destructive_confirmation(
    run_type: str, pipelines: list[str], dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for destructive operations.

    Args:
        run_type: Type of run; only 'rebuild' and 'backfill' trigger the confirmation
            prompt.
        pipelines: List of pipeline names that will be affected by the operation.
        dry_run: When True, skips the confirmation prompt.
        yes: When True, bypasses the interactive confirmation prompt.

    Returns:
        True if should continue, False if cancelled.
    """
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return True
    return _handle_destructive_confirmation_impl(
        run_type=run_type,
        pipelines=pipelines,
        dry_run=dry_run,
        yes=yes,
        confirm_fn=click.confirm,
        info_printer=echo_info,
        exit_func=exit_with_code,
    )


def _run_batch_with_policy(
    *,
    source: str,
    pipelines: list[str],
    options: RunOptions,
    health_server: bool,
    health_port: int,
    registry: PipelineRegistry | None = None,
) -> BatchRunResult | None:
    """Execute async batch run with typed exception policy.

    Args:
        source: Provider name used in error context for structured failure handling.
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server: When True, enables the HTTP health server during execution.
        health_port: TCP port the health server listens on.

    Returns:
        BatchRunResult on success, None if an exception was handled and process will exit.
    """
    return _run_batch_with_policy_impl(
        RunAllPolicyRequest(
            source=source,
            execution=RunAllBatchExecutionRequest(
                pipelines=pipelines,
                options=options,
                health_server_enabled=health_server,
                health_port=health_port,
                registry=registry,
            ),
        ),
        get_pipeline_runner_service_fn=get_pipeline_runner_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        health_server_context_factory=health_server_context,
        run_coro=asyncio.run,
        handle_failure=lambda exc, source, reason_code: handle_run_all_cli_failure(
            exc,
            source=source,
            reason_code=reason_code,
        ),
    )


def _run_all_callback(
    click_context: click.Context,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Canonical callback implementation for the run-all Click command."""
    dispatch_cli_callback(
        click_context,
        build_cli_input=lambda: build_run_all_command_input(
            source=source,
            run_type=run_type,
            limit=limit,
            dry_run=dry_run,
            yes=yes,
            list_only=list_only,
            debug=debug,
            health_server=health_server,
            health_port=health_port,
        ),
        run_with_cli_policy=_run_all_with_cli_policy,
    )


def _run_all_with_cli_policy(
    click_context: click.Context,
    cli_input: RunAllCommandInput,
) -> None:
    """Resolve registry and execute the prepared run-all policy flow."""
    registry = resolve_context_registry(click_context)
    run_all_command_flow(
        cli_input=cli_input,
        registry=registry,
        destructive_confirmation=_handle_destructive_confirmation,
        listing_emitter=emit_run_all_listing,
        preview_emitter=emit_run_all_preview,
        health_info_presenter=echo_health_server_info,
        execute_batch=_run_batch_with_policy,
        summary_presenter=_echo_batch_summary,
        determine_exit_code=_determine_exit_code,
        exit_func=exit_with_code,
    )


run_all = build_run_all_click_command(
    default_health_server_port=DEFAULT_HEALTH_SERVER_PORT,
    run_callback=_run_all_callback,
)


__all__ = [
    "BatchRunResult",
    "_determine_exit_code",
    "_filter_pipelines_by_provider",
    "_get_available_providers",
    "_validate_provider",
    "build_cli_registry",
    "run_all",
]

================================================================================
File: command_entrypoint.py
Path: cli\commands\domains\run_all\command_entrypoint.py
================================================================================
"""Click entrypoint builder for the run-all CLI command."""

from __future__ import annotations

from collections.abc import Callable

import click

from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    with_debug_option,
    with_dry_run_option,
    with_health_server_options,
    with_limit_option,
    with_run_type_option,
    with_yes_option,
)


def build_run_all_click_command(
    *,
    default_health_server_port: int,
    run_callback: Callable[..., None],
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run-all``."""

    @click.command("run-all")  # type: ignore[untyped-decorator]
    @click.option(  # type: ignore[untyped-decorator]
        "--source",
        required=True,
        help="Provider name (e.g., chembl, pubchem, uniprot)",
    )
    @with_run_type_option("Type of run for all pipelines")
    @with_limit_option("Maximum records per pipeline")
    @with_dry_run_option("Preview mode - show pipelines without execution")
    @with_yes_option("Skip confirmation prompt for rebuild/backfill")
    @click.option(  # type: ignore[untyped-decorator]
        "--list-only",
        is_flag=True,
        help="List pipelines for the source without running them",
    )
    @with_debug_option("Enable DEBUG level logging")
    @with_health_server_options(default_health_server_port)
    @click.pass_context  # type: ignore[untyped-decorator]
    def run_all_command(
        click_context: click.Context,
        source: str,
        run_type: str,
        limit: int | None,
        dry_run: bool,
        yes: bool,
        list_only: bool,
        debug: bool,
        health_server: bool,
        health_port: int,
    ) -> None:
        """Run all registered pipelines for one provider sequentially."""
        run_callback(
            click_context,
            source=source,
            run_type=run_type,
            limit=limit,
            dry_run=dry_run,
            yes=yes,
            list_only=list_only,
            debug=debug,
            health_server=health_server,
            health_port=health_port,
        )

    return run_all_command


__all__ = ["build_run_all_click_command"]

================================================================================
File: command_policy.py
Path: cli\commands\domains\run_all\command_policy.py
================================================================================
"""Policy helpers for run-all command control flow."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import NoReturn, Protocol

from bioetl.application.services import RunOptions
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    PipelineRegistryView,
    RunAllExecutionPlan,
    resolve_run_all_execution_plan,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    finalize_cli_execution,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "RunAllCommandInput",
    "build_run_all_command_input",
    "exit_with_code",
    "finalize_batch_step",
    "handle_run_all_cli_failure",
    "prepare_run_all_execution_plan",
    "run_all_command_flow",
]


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


class ListingEmitterCallable(Protocol):
    """Callable contract for list-only run-all output."""

    def __call__(self, *, source: str, pipelines: list[str]) -> None: ...


class PreviewEmitterCallable(Protocol):
    """Callable contract for pre-execution run-all preview output."""

    def __call__(self, *, source: str, pipelines: list[str], dry_run: bool) -> None: ...


class DestructiveConfirmationCallable(Protocol):
    """Callable contract for destructive-run confirmation flow."""

    def __call__(
        self,
        run_type: str,
        pipelines: list[str],
        dry_run: bool,
        yes: bool,
    ) -> bool: ...


class HealthInfoPresenterCallable(Protocol):
    """Callable contract for health-server presentation."""

    def __call__(self, enabled: bool, port: int) -> None: ...


class BatchExecutorCallable(Protocol):
    """Callable contract for synchronous run-all batch execution."""

    def __call__(
        self,
        *,
        source: str,
        pipelines: list[str],
        options: RunOptions,
        health_server: bool,
        health_port: int,
        registry: PipelineRegistry | None = None,
    ) -> BatchRunResult | None: ...


class BatchSummaryPresenterCallable(Protocol):
    """Callable contract for rendering the completed batch summary."""

    def __call__(self, result: BatchRunResult, dry_run: bool) -> None: ...


class BatchExitCodeCallable(Protocol):
    """Callable contract for mapping a batch result to the final exit code."""

    def __call__(self, result: BatchRunResult) -> ExitCode: ...


@dataclass(frozen=True, slots=True)
class RunAllCommandInput:
    """Normalized CLI inputs for the run-all command control flow."""

    source: str
    run_type: str
    limit: int | None
    dry_run: bool
    yes: bool
    list_only: bool
    debug: bool
    health_server: bool
    health_port: int


def exit_with_code(code: int | str | None = None) -> NoReturn:
    """Typed wrapper around sys.exit for policy-flow injection."""
    sys.exit(code)


def build_run_all_command_input(
    *,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> RunAllCommandInput:
    """Build normalized CLI input payload for run_all_command_flow."""
    return RunAllCommandInput(
        source=source,
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        yes=yes,
        list_only=list_only,
        debug=debug,
        health_server=health_server,
        health_port=health_port,
    )


def handle_run_all_cli_failure(
    exc: BaseException,
    *,
    source: str,
    reason_code: str,
) -> None:
    """Handle run-all CLI failures with consistent reason_code semantics."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="source",
        subject_value=source,
        domain_error_title="Batch execution failed with domain error",
        unexpected_error_title="Unexpected error during batch execution",
        interrupted_message="Batch run interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def prepare_run_all_execution_plan(
    *,
    cli_input: RunAllCommandInput,
    registry: PipelineRegistryView | None = None,
    exit_func: ExitCallable,
) -> RunAllExecutionPlan:
    """Validate run-all inputs and build the prepared execution plan."""
    execution_plan, error_msg = resolve_run_all_execution_plan(
        source=cli_input.source,
        run_type=cli_input.run_type,
        limit=cli_input.limit,
        dry_run=cli_input.dry_run,
        debug=cli_input.debug,
        registry=registry,
    )
    if execution_plan is not None:
        return execution_plan
    if error_msg is not None:
        echo_error("Provider error", error_msg)
    exit_func(ExitCode.FAIL)
    raise RuntimeError("unreachable: exit_func is expected to terminate")


def finalize_batch_step(
    *,
    batch_result: BatchRunResult,
    dry_run: bool,
    summary_presenter: BatchSummaryPresenterCallable,
    determine_exit_code: BatchExitCodeCallable,
    exit_func: ExitCallable,
) -> None:
    """Present the completed batch result and terminate with its exit code."""
    summary_presenter(batch_result, dry_run)
    exit_func(determine_exit_code(batch_result))


def run_all_command_flow(
    *,
    cli_input: RunAllCommandInput,
    registry: PipelineRegistry | None,
    destructive_confirmation: DestructiveConfirmationCallable,
    listing_emitter: ListingEmitterCallable,
    preview_emitter: PreviewEmitterCallable,
    health_info_presenter: HealthInfoPresenterCallable,
    execute_batch: BatchExecutorCallable,
    summary_presenter: BatchSummaryPresenterCallable,
    determine_exit_code: BatchExitCodeCallable,
    exit_func: ExitCallable,
) -> None:
    """Execute the full run-all control flow from normalized CLI input."""
    execution_plan = prepare_run_all_execution_plan(
        cli_input=cli_input,
        registry=registry,
        exit_func=exit_func,
    )
    pipelines = execution_plan.pipelines

    if cli_input.list_only:
        listing_emitter(source=cli_input.source, pipelines=pipelines)
        exit_func(ExitCode.OK)

    destructive_confirmation(
        cli_input.run_type,
        pipelines,
        cli_input.dry_run,
        cli_input.yes,
    )
    preview_emitter(
        source=cli_input.source,
        pipelines=pipelines,
        dry_run=cli_input.dry_run,
    )
    finalize_cli_execution(
        health_info_presenter=lambda: health_info_presenter(
            cli_input.health_server,
            cli_input.health_port,
        ),
        execute=lambda: execute_batch(
            source=cli_input.source,
            pipelines=pipelines,
            options=execution_plan.options,
            health_server=cli_input.health_server,
            health_port=cli_input.health_port,
            registry=registry,
        ),
        result_finalizer=lambda batch_result: finalize_batch_step(
            batch_result=batch_result,
            dry_run=cli_input.dry_run,
            summary_presenter=summary_presenter,
            determine_exit_code=determine_exit_code,
            exit_func=exit_func,
        ),
    )

================================================================================
File: execution.py
Path: cli\commands\domains\run_all\execution.py
================================================================================
"""Execution helpers for the run-all CLI command."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunnerService,
    RunOptions,
    RunResult,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    record_pipeline_failure,
    record_pipeline_result,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliFailureHandler,
    ExecutionFailureReasonCodes,
    execute_with_cli_failure_policy,
)

_EnsureMetricsServerStartedFn = Callable[[], object]
_HealthServerContextFactory = Callable[..., AbstractAsyncContextManager[object]]
_RunAllFailureHandler = CliFailureHandler
_RunAllCoroutineRunner = Callable[
    [Coroutine[object, object, BatchRunResult]],
    BatchRunResult,
]


class _GetPipelineRunnerServiceFn(Protocol):
    """Callable protocol for resolving the pipeline runner service."""

    def __call__(
        self,
        *,
        registry: PipelineRegistry | None = None,
    ) -> PipelineRunnerService:
        """Return the pipeline runner service for the selected registry."""
        ...


@dataclass(frozen=True, slots=True)
class RunAllBatchExecutionRequest:
    """Input for one run-all batch execution."""

    pipelines: list[str]
    options: RunOptions
    health_server_enabled: bool = True
    health_port: int = DEFAULT_HEALTH_SERVER_PORT
    registry: PipelineRegistry | None = None


@dataclass(frozen=True, slots=True)
class RunAllPolicyRequest:
    """Input for one run-all CLI policy execution."""

    source: str
    execution: RunAllBatchExecutionRequest


async def _run_pipeline_async(
    service: PipelineRunnerService,
    pipeline: str,
    options: RunOptions,
) -> RunResult:
    """Run a single pipeline asynchronously."""
    return await service.run(pipeline, options=options)


async def _run_pipelines_batch(
    service: PipelineRunnerService,
    pipelines: list[str],
    options: RunOptions,
) -> BatchRunResult:
    """Run pipelines sequentially within one service context."""
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            pipeline_run_result = await _run_pipeline_async(service, pipeline, options)
            if record_pipeline_result(
                batch_result=batch_result,
                pipeline=pipeline,
                result=pipeline_run_result,
            ):
                break
        except PipelineNotFoundError as exc:
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: not found",
                detail=str(exc),
            )
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            error_msg = (
                f"{exc} (reason_code=CLI_RUN_ALL_PIPELINE_ERROR, "
                f"pipeline={pipeline}, error_type={type(exc).__name__})"
            )
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: unexpected error",
                detail=error_msg,
            )

    return batch_result


async def run_all_pipelines_async(
    request: RunAllBatchExecutionRequest,
    *,
    get_pipeline_runner_service_fn: _GetPipelineRunnerServiceFn,
    ensure_metrics_server_started_fn: _EnsureMetricsServerStartedFn,
    health_server_context_factory: _HealthServerContextFactory,
) -> BatchRunResult:
    """Run all pipelines sequentially with the configured CLI integrations."""
    ensure_metrics_server_started_fn()

    async with health_server_context_factory(
        enabled=request.health_server_enabled,
        port=request.health_port,
    ):
        service = get_pipeline_runner_service_fn(registry=request.registry)
        return await _run_pipelines_batch(service, request.pipelines, request.options)


def run_batch_with_policy(
    request: RunAllPolicyRequest,
    *,
    get_pipeline_runner_service_fn: _GetPipelineRunnerServiceFn,
    ensure_metrics_server_started_fn: _EnsureMetricsServerStartedFn,
    health_server_context_factory: _HealthServerContextFactory,
    run_coro: _RunAllCoroutineRunner,
    handle_failure: _RunAllFailureHandler,
) -> BatchRunResult | None:
    """Execute the run-all batch with typed CLI exception handling."""
    coro = run_all_pipelines_async(
        request.execution,
        get_pipeline_runner_service_fn=get_pipeline_runner_service_fn,
        ensure_metrics_server_started_fn=ensure_metrics_server_started_fn,
        health_server_context_factory=health_server_context_factory,
    )
    try:
        return execute_with_cli_failure_policy(
            lambda: run_coro(coro),
            subject=request.source,
            reason_codes=ExecutionFailureReasonCodes(
                config="CLI_RUN_ALL_CONFIG_ERROR",
                domain="CLI_RUN_ALL_DOMAIN_ERROR",
                interrupted="CLI_RUN_ALL_SIGINT",
                unexpected="CLI_RUN_ALL_UNEXPECTED_ERROR",
            ),
            failure_handler=handle_failure,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

================================================================================
File: support.py
Path: cli\commands\domains\run_all\support.py
================================================================================
"""Internal helper functions for the run-all CLI command."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NoReturn, Protocol, cast

import click

from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    map_batch_run_result_to_exit_code,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = [
    "BatchRunResult",
    "RunAllExecutionPlan",
    "create_run_all_options",
    "determine_batch_exit_code",
    "echo_batch_summary",
    "emit_destructive_confirmation_preview",
    "emit_run_all_listing",
    "emit_run_all_preview",
    "filter_pipelines_by_provider",
    "get_available_providers",
    "handle_destructive_confirmation",
    "record_pipeline_failure",
    "record_pipeline_result",
    "resolve_run_all_execution_plan",
    "resolve_run_all_registry",
    "should_prompt_for_destructive_run",
    "validate_provider",
]


class _BatchRunAccumulator(Protocol):
    """Minimal mutable contract needed for run-all batch result updates."""

    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[RunResult]
    failed_pipelines: list[str]


@dataclass
class BatchRunResult:
    """Result of running multiple pipelines."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[RunResult] = field(default_factory=list)
    failed_pipelines: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        """Check if all pipelines succeeded."""
        return self.failed == 0 and self.total > 0


@dataclass(frozen=True, slots=True)
class RunAllExecutionPlan:
    """Resolved pipelines and RunOptions for one run-all invocation."""

    pipelines: list[str]
    options: RunOptions


class PipelineRegistryView(Protocol):
    """Minimal registry contract used by run-all helper functions."""

    def list_pipelines(self) -> list[str]:
        """Return all registered pipeline names visible to the CLI."""
        ...


def _list_registered_pipelines(
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Return registered pipeline names from the resolved registry view."""
    return resolve_run_all_registry(registry).list_pipelines()


def _record_success(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a successful pipeline run."""
    batch_result.succeeded += 1
    echo_info(f"[OK] {pipeline}: completed successfully")
    return False


def _record_dry_run(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a dry-run preview result."""
    batch_result.skipped += 1
    echo_info(f"[DRY] {pipeline}: dry-run (no changes)")
    return False


def _record_shutdown(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a graceful shutdown result and stop the batch."""
    batch_result.skipped += 1
    echo_warning(f"[STOP] {pipeline}: gracefully shut down")
    return True


def resolve_run_all_registry(
    registry: PipelineRegistryView | None = None,
) -> PipelineRegistryView:
    """Resolve the registry view for run-all helper functions."""
    if registry is not None:
        return registry

    ctx = click.get_current_context(silent=True)
    candidate = getattr(ctx, "obj", None) if ctx is not None else None
    if candidate is None or not hasattr(candidate, "list_pipelines"):
        raise RuntimeError("run-all helpers require an explicit PipelineRegistry")
    return cast(PipelineRegistryView, candidate)


def get_available_providers(
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Get sorted list of unique provider names from registered pipelines."""
    pipelines = _list_registered_pipelines(registry=registry)
    providers = {p.split("_")[0] for p in pipelines if "_" in p}
    return sorted(providers)


def filter_pipelines_by_provider(
    provider: str,
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Filter registered pipelines by provider prefix."""
    all_pipelines = _list_registered_pipelines(registry=registry)
    return sorted([name for name in all_pipelines if name.startswith(f"{provider}_")])


def validate_provider(
    provider: str,
    registry: PipelineRegistryView | None = None,
) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines."""
    available_providers = get_available_providers(registry=registry)
    if not available_providers:
        return False, "No pipelines are registered."
    pipelines = filter_pipelines_by_provider(provider, registry=registry)
    if not pipelines:
        return False, (
            f"No pipelines found for provider '{provider}'. "
            f"Available providers: {', '.join(available_providers)}"
        )
    return True, None


def create_run_all_options(
    *,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    debug: bool,
) -> RunOptions:
    """Build canonical RunOptions for the run-all command."""
    return RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )


def resolve_run_all_execution_plan(
    *,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    debug: bool,
    registry: PipelineRegistryView | None = None,
) -> tuple[RunAllExecutionPlan | None, str | None]:
    """Resolve validated provider pipelines and canonical RunOptions."""
    is_valid, error = validate_provider(source, registry=registry)
    if not is_valid:
        return None, error

    return (
        RunAllExecutionPlan(
            pipelines=filter_pipelines_by_provider(source, registry=registry),
            options=create_run_all_options(
                run_type=run_type,
                limit=limit,
                dry_run=dry_run,
                debug=debug,
            ),
        ),
        None,
    )


def emit_run_all_listing(*, source: str, pipelines: list[str]) -> None:
    """Emit list-only output for provider pipelines."""
    echo_info(f"Pipelines for provider '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info(f"\nTotal: {len(pipelines)} pipeline(s)")


def should_prompt_for_destructive_run(
    *,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Return whether the CLI should prompt before destructive execution."""
    return run_type in ("rebuild", "backfill") and not dry_run and not yes


def emit_destructive_confirmation_preview(
    *,
    run_type: str,
    pipelines: list[str],
) -> None:
    """Emit the confirmation preview shown before destructive operations."""
    echo_warning(f"{run_type} will clear existing data for {len(pipelines)} pipelines.")
    echo_info("Pipelines to be affected:")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")


def handle_destructive_confirmation(
    *,
    run_type: str,
    pipelines: list[str],
    dry_run: bool,
    yes: bool,
    confirm_fn: Callable[[str], bool] = click.confirm,
    info_printer: Callable[..., None] = echo_info,
    exit_func: Callable[[int | str | None], NoReturn] = sys.exit,
) -> bool:
    """Handle confirmation flow for destructive run-all operations."""
    should_continue = True
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return should_continue

    emit_destructive_confirmation_preview(
        run_type=run_type,
        pipelines=pipelines,
    )

    should_continue = confirm_fn("\nDo you want to continue?")
    if not should_continue:
        info_printer("Operation cancelled.")
        exit_func(ExitCode.OK)
    return should_continue


def emit_run_all_preview(
    *,
    source: str,
    pipelines: list[str],
    dry_run: bool,
) -> None:
    """Emit the preview shown before running provider pipelines."""
    prefix = "[DRY-RUN] Would run" if dry_run else "Running"
    echo_info(f"{prefix} {len(pipelines)} pipeline(s) for '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")


def record_pipeline_result(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    result: RunResult,
) -> bool:
    """Record one pipeline result and return whether the batch should stop."""
    batch_result.results.append(result)

    if result.status == PipelineRunResult.SUCCESS:
        return _record_success(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.DRY_RUN:
        return _record_dry_run(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.SHUTDOWN:
        return _record_shutdown(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.FAILED:
        record_pipeline_failure(
            batch_result=batch_result,
            pipeline=pipeline,
            title=f"[FAIL] {pipeline}: failed",
            detail=result.error_message or "Unknown error",
        )

    return False


def record_pipeline_failure(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    title: str,
    detail: str,
) -> None:
    """Record a failed pipeline and emit a consistent error message."""
    batch_result.failed += 1
    batch_result.failed_pipelines.append(pipeline)
    echo_error(title, detail)


def determine_batch_exit_code(result: _BatchRunAccumulator) -> ExitCode:
    """Determine the CLI exit code from aggregate batch state."""
    return map_batch_run_result_to_exit_code(result)


def echo_batch_summary(
    *,
    result: _BatchRunAccumulator,
    dry_run: bool,
    info_printer: Callable[..., None] = echo_info,
    error_printer: Callable[..., None] = echo_error,
) -> None:
    """Emit batch run summary using injected output sinks."""
    info_printer("\n" + "=" * 50)
    if dry_run:
        info_printer(f"Dry-run complete: {result.total} pipelines previewed")
    else:
        info_printer(f"Batch run complete: {result.total} pipelines")
        info_printer(f"  Succeeded: {result.succeeded}")
        if result.failed > 0:
            info_printer(f"  Failed: {result.failed}")
        if result.skipped > 0:
            info_printer(f"  Skipped: {result.skipped}")
    if result.failed_pipelines:
        error_printer("Failed pipelines:", ", ".join(result.failed_pipelines))

================================================================================
File: __init__.py
Path: cli\commands\domains\shared\__init__.py
================================================================================
"""Shared policy helpers for CLI command domains."""

from __future__ import annotations

================================================================================
File: callback_dispatch.py
Path: cli\commands\domains\shared\callback_dispatch.py
================================================================================
"""Shared thin callback dispatch for Click command entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import click

_InputT = TypeVar("_InputT")


def dispatch_cli_callback(
    click_context: click.Context,
    *,
    build_cli_input: Callable[[], _InputT],
    run_with_cli_policy: Callable[[click.Context, _InputT], None],
) -> None:
    """Build normalized CLI input and hand it off to the policy layer."""
    cli_input = build_cli_input()
    run_with_cli_policy(click_context, cli_input)

================================================================================
File: click_options.py
Path: cli\commands\domains\shared\click_options.py
================================================================================
"""Reusable Click option decorators for orchestration command entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

import click

_CommandParams = ParamSpec("_CommandParams")
_CommandReturn = TypeVar("_CommandReturn")


def _cast_command(
    func: Callable[_CommandParams, _CommandReturn],
) -> Callable[_CommandParams, _CommandReturn]:
    return func


def with_run_type_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--run-type`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--run-type",
            type=click.Choice(["incremental", "backfill", "rebuild"]),
            default="incremental",
            help=help_text,
        )(func)
    )


def with_limit_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--limit`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--limit",
            type=int,
            help=help_text,
        )(func)
    )


def with_dry_run_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--dry-run`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--dry-run",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_yes_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical destructive-confirmation bypass option."""
    return lambda func: _cast_command(
        click.option(
            "--yes",
            "-y",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_debug_option(
    help_text: str = "Enable DEBUG level logging for detailed output",
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--debug`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--debug",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_health_server_options(
    default_health_server_port: int,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical health-server option pair to a Click command."""

    def decorator(
        func: Callable[_CommandParams, _CommandReturn],
    ) -> Callable[_CommandParams, _CommandReturn]:
        func = _cast_command(
            click.option(
                "--health-port",
                type=int,
                default=default_health_server_port,
                help="Port for the HTTP health server.",
                show_default=True,
            )(func)
        )
        return _cast_command(
            click.option(
                "--health-server/--no-health-server",
                "health_server",
                default=True,
                help="Enable/disable HTTP health server during execution.",
                show_default=True,
            )(func)
        )

    return decorator

================================================================================
File: execution_policy.py
Path: cli\commands\domains\shared\execution_policy.py
================================================================================
"""Shared CLI execution policy for orchestration commands.

Centralizes command-level error handling and exit-code mapping for:
- run
- run-all
- run-composite
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.exit_codes import ExitCode, get_exit_code_for_exception
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

__all__ = [
    "CLI_ENTRYPOINT_TYPED_ERRORS",
    "BatchRunResultProtocol",
    "ExecutionFailureReasonCodes",
    "build_failure_context",
    "execute_with_cli_failure_policy",
    "finalize_cli_execution",
    "handle_cli_failure",
    "map_batch_run_result_to_exit_code",
    "map_run_status_to_exit_code",
    "map_success_flag_to_exit_code",
    "render_failure_context",
]

_ResultT = TypeVar("_ResultT")

CLI_ENTRYPOINT_TYPED_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    TimeoutError,
)

_FAILED_STATUS_EXIT_OVERRIDES: Mapping[str, ExitCode] = {
    "ValueError": ExitCode.CONFIG_ERROR,
    "FileNotFoundError": ExitCode.EX_NOINPUT,
    "ConfigValidationError": ExitCode.CONFIG_ERROR,
    "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
    "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
    "LockAcquisitionError": ExitCode.LOCK_ERROR,
    "LockLostError": ExitCode.LOCK_ERROR,
    "StorageError": ExitCode.STORAGE_ERROR,
    "NetworkError": ExitCode.NETWORK_ERROR,
    "RateLimitError": ExitCode.NETWORK_ERROR,
    "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
}


class BatchRunResultProtocol(Protocol):
    """Protocol for batch run result objects used in exit-code mapping."""

    @property
    def failed(self) -> int:
        """Return the number of failed runs."""
        ...

    @property
    def total(self) -> int:
        """Return the total number of runs."""
        ...

    @property
    def results(self) -> Sequence[object]:
        """Return the individual run results."""
        ...


class CliFailureHandler(Protocol):
    """Callable contract for structured CLI failure handling."""

    def __call__(
        self,
        exc: BaseException,
        subject: str,
        reason_code: str,
    ) -> None:
        """Handle one exception for one logical command subject."""
        ...


@dataclass(frozen=True, slots=True)
class ExecutionFailureReasonCodes:
    """Reason-code bundle for typed CLI exception handling."""

    config: str
    domain: str
    interrupted: str
    unexpected: str


def map_run_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map single pipeline status to CLI exit code.

    Args:
        status: PipelineRunResult enum value (SUCCESS, DRY_RUN, SHUTDOWN, or FAILED).
        error_type: Exception class name from the failed run; used to select a
            specific exit code when status is FAILED. None for non-failure statuses.

    Returns:
        ExitCode corresponding to the pipeline run status and error type.
    """
    if status in (PipelineRunResult.SUCCESS, PipelineRunResult.DRY_RUN):
        return ExitCode.OK
    if status == PipelineRunResult.SHUTDOWN:
        return ExitCode.SIGINT
    if error_type is not None:
        return _FAILED_STATUS_EXIT_OVERRIDES.get(error_type, ExitCode.PIPELINE_ERROR)
    return ExitCode.PIPELINE_ERROR


def map_batch_run_result_to_exit_code(batch_result: BatchRunResultProtocol) -> ExitCode:
    """Map batched pipeline result to CLI exit code.

    Args:
        batch_result: BatchRunResultProtocol with failed count, total count, and
            individual run result objects.

    Returns:
        ExitCode based on the number of failures and shutdown signals in the batch.
    """
    if batch_result.failed > 0:
        return ExitCode.PIPELINE_ERROR
    if any(
        getattr(result, "status", None) == PipelineRunResult.SHUTDOWN
        for result in batch_result.results
    ):
        return ExitCode.SIGINT
    if batch_result.total > 0:
        return ExitCode.OK
    return ExitCode.SIGINT


def map_success_flag_to_exit_code(
    success: bool,
    *,
    failure_exit_code: ExitCode = ExitCode.PIPELINE_ERROR,
) -> ExitCode:
    """Map boolean command outcome to CLI exit code.

    Args:
        success: When True, returns ExitCode.OK; when False, returns failure_exit_code.
        failure_exit_code: Exit code to return on failure; defaults to
            ExitCode.PIPELINE_ERROR.

    Returns:
        ExitCode.OK if success is True, otherwise the specified failure_exit_code.
    """
    if success:
        return ExitCode.OK
    return failure_exit_code


def execute_with_cli_failure_policy(
    action: Callable[[], _ResultT],
    *,
    subject: str,
    reason_codes: ExecutionFailureReasonCodes,
    failure_handler: CliFailureHandler,
) -> _ResultT | None:
    """Execute one command action with the canonical typed-failure ladder."""
    try:
        return action()
    except PipelineNotFoundError as exc:
        failure_handler(exc, subject, reason_codes.config)
    except BioETLError as exc:
        failure_handler(exc, subject, reason_codes.domain)
    except KeyboardInterrupt as exc:
        failure_handler(exc, subject, reason_codes.interrupted)
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        failure_handler(exc, subject, reason_codes.unexpected)
    return None


def finalize_cli_execution(
    *,
    health_info_presenter: Callable[[], None],
    execute: Callable[[], _ResultT | None],
    result_finalizer: Callable[[_ResultT], None],
) -> None:
    """Run the prepared health -> execute -> finalize command shell."""
    health_info_presenter()
    result = execute()
    if result is None:
        return
    result_finalizer(result)


def build_failure_context(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> dict[str, object]:
    """Build structured context for CLI failure diagnostics.

    Args:
        exc: Exception to build context from; BioETLError instances use their
            own structured context method.
        reason_code: Machine-readable code attached to error context (e.g.,
            'CLI_RUN_DOMAIN_ERROR').
        subject_key: Key name for the structured context field (e.g., 'pipeline').
        subject_value: Value for the structured context field (e.g., 'chembl_activity').

    Returns:
        Dictionary with structured error context including message, reason_code,
        subject key/value, and error type.
    """
    if isinstance(exc, BioETLError):
        structured_context: dict[str, object] = exc.to_structured_context(
            reason_code=reason_code,
            **{subject_key: subject_value},
        )
        return structured_context

    return {
        "message": str(exc),
        "reason_code": reason_code,
        subject_key: subject_value,
        "error_type": type(exc).__name__,
    }


def render_failure_context(context: Mapping[str, object]) -> str:
    """Render a structured failure context as stable human-readable text.

    Args:
        context: Structured failure context mapping with at least a 'message' key
            and optional metadata fields.

    Returns:
        Human-readable string combining the message and sorted metadata fields.
    """
    message = str(context.get("message", ""))
    keys = [key for key in context if key != "message"]
    keys.sort()
    metadata = ", ".join(f"{key}={context[key]}" for key in keys)
    if not metadata:
        return message
    if not message:
        return metadata
    return f"{message} ({metadata})"


def _format_failure_detail(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> str:
    failure_context = build_failure_context(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
    )
    return render_failure_context(failure_context)


def handle_cli_failure(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
    default_exit_code: ExitCode = ExitCode.FAIL,
) -> None:
    """Handle command-level exceptions with a consistent policy.

    Maps the exception type to the appropriate exit code, formats a structured
    error message, echoes it to stderr, and calls sys.exit() with the mapped code.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code attached to error context (e.g.,
            'CLI_COMPOSITE_DOMAIN_ERROR').
        subject_key: Key name for the structured context field (e.g., 'pipeline').
        subject_value: Value for the structured context field (e.g., 'chembl_activity').
        domain_error_title: Title shown for BioETLError exceptions.
        unexpected_error_title: Title shown for non-domain exceptions.
        interrupted_message: Message shown when KeyboardInterrupt is caught.
        default_exit_code: Fallback exit code when no specific code is determined.
            Defaults to ExitCode.FAIL.
    """
    if isinstance(exc, PipelineNotFoundError):
        echo_error("Pipeline not found", str(exc))
        sys.exit(ExitCode.CONFIG_ERROR)

    if isinstance(exc, KeyboardInterrupt):
        echo_warning(interrupted_message)
        sys.exit(ExitCode.SIGINT)

    detail = _format_failure_detail(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
    )

    if isinstance(exc, BioETLError):
        domain_exit = get_exit_code_for_exception(exc)
        if domain_exit == ExitCode.FAIL:
            domain_exit = default_exit_code
        echo_error(domain_error_title, detail)
        sys.exit(domain_exit)

    exit_code = get_exit_code_for_exception(exc)
    if exit_code == ExitCode.FAIL:
        exit_code = default_exit_code
    echo_error(unexpected_error_title, detail)
    sys.exit(exit_code)

================================================================================
File: export.py
Path: cli\commands\export.py
================================================================================
"""Export commands for BioETL CLI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.export_support import (
    ExportFormat,
    _build_export_options,
    _list_tables_or_exit,
    _require_table_argument,
    _run_export,
    _run_preview,
)

if TYPE_CHECKING:
    from bioetl.application.services import ExportService

__all__ = ["ExportFormat", "export_command"]


def get_export_service() -> ExportService:
    """Load the export service through composition on demand."""
    from bioetl.composition.control_plane_api import get_export_service as _impl

    return _impl()


@click.command("export")  # type: ignore[untyped-decorator]
@click.argument("table", required=False)  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--list",
    "list_tables",
    is_flag=True,
    help="List all available Delta tables",
)
@click.option(  # type: ignore[untyped-decorator]
    "--preview",
    is_flag=True,
    help="Show table schema and sample data",
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "xlsx", "tsv"]),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--layer",
    "-l",
    type=click.Choice(["silver", "gold"]),
    default="silver",
    help="Medallion layer to export from (default: silver)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: data/exports)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--limit",
    type=int,
    help="Maximum number of rows to export",
)
@click.option(  # type: ignore[untyped-decorator]
    "--columns",
    "-c",
    help="Comma-separated list of columns to include",
)
def export_command(
    table: str | None,
    list_tables: bool,
    preview: bool,
    output_format: str,
    layer: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> None:
    """Export Delta Lake tables.

    `table` must use `provider.entity` format (for example `chembl.activity`).
    Use `--list` to display available tables and `--preview` for schema/sample.
    """
    service = get_export_service()

    if list_tables:
        _list_tables_or_exit(service, layer=layer)
        return

    resolved_table = _require_table_argument(table)

    if preview:
        _run_preview(service=service, table=resolved_table, layer=layer)
        return

    options = _build_export_options(
        output_format=output_format,
        output=output,
        limit=limit,
        columns=columns,
    )
    _run_export(service=service, table=resolved_table, layer=layer, options=options)

================================================================================
File: export_support.py
Path: cli\commands\export_support.py
================================================================================
"""Shared helpers for the export CLI command."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast

from bioetl.application.services import (
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_table_list,
)

__all__ = [
    "ExportFormat",
    "_ExportCommandService",
    "_build_export_options",
    "_list_tables_or_exit",
    "_require_table_argument",
    "_run_export",
    "_run_preview",
]

ExportFormat = Literal["csv", "xlsx", "tsv"]
_T = TypeVar("_T")


class _ExportCommandService(Protocol):
    """Service protocol for export CLI commands."""

    async def preview(self, table_name: str, layer: str = "silver") -> TablePreview:
        """Return a preview of the given table."""
        ...

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Export the given table to the specified format."""
        ...

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """List available tables for export."""
        ...


def _handle_export_failure(
    exc: BaseException,
    *,
    reason_code: str,
    table: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> None:
    """Handle export command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="table",
        subject_value=table,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message="Export interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def _run_export_async(
    coro: Coroutine[object, object, _T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
    handle_file_not_found: bool = False,
) -> _T | None:
    """Run an async export coroutine with shared CLI exception handling."""
    try:
        return asyncio.run(coro)
    except FileNotFoundError as exc:
        if handle_file_not_found:
            echo_error(str(exc))
            raise SystemExit(ExitCode.FAIL) from None
        raise
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _run_export_sync(
    fn: Callable[[], _T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> _T | None:
    """Run a sync export callable with shared CLI exception handling."""
    try:
        return fn()
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    return None


def _resolve_list_layer(layer: str) -> str:
    """Map CLI layer value to service list scope."""
    return layer if layer != "silver" else "all"


def _require_table_argument(table: str | None) -> str:
    """Validate table argument for non-list operations."""
    if table:
        return table
    echo_error("TABLE argument is required (or use --list to see available tables)")
    raise SystemExit(ExitCode.FAIL)


def _parse_columns(columns: str | None) -> list[str] | None:
    """Parse comma-separated columns from CLI option."""
    if not columns:
        return None
    return [column.strip() for column in columns.split(",")]


def _parse_export_format(output_format: str) -> ExportFormat:
    """Parse output format value into strict ExportFormat literal."""
    if output_format in {"csv", "xlsx", "tsv"}:
        return cast("ExportFormat", output_format)
    return "csv"


def _build_export_options(
    output_format: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> ExportOptions:
    """Build validated ExportOptions from CLI parameters."""
    return ExportOptions(
        format=_parse_export_format(output_format),
        output_path=output,
        limit=limit,
        columns=_parse_columns(columns),
    )


def _run_preview(
    service: _ExportCommandService,
    table: str,
    layer: str,
) -> None:
    """Execute async preview operation from sync CLI context."""

    async def _preview() -> TablePreview:
        return await service.preview(table, layer=layer)

    table_preview = _run_export_async(
        _preview(),
        table=table,
        reason_prefix="CLI_EXPORT_PREVIEW",
        domain_error_title="Export preview failed with domain error",
        unexpected_error_title="Unexpected error during export preview",
        handle_file_not_found=True,
    )
    if table_preview is not None:
        echo_export_preview(table_preview)


def _run_export(
    service: _ExportCommandService,
    table: str,
    layer: str,
    options: ExportOptions,
) -> None:
    """Execute async export operation from sync CLI context."""

    async def _export() -> ExportResult:
        return await service.export(table, layer=layer, options=options)

    result = _run_export_async(
        _export(),
        table=table,
        reason_prefix="CLI_EXPORT_RUN",
        domain_error_title="Export failed with domain error",
        unexpected_error_title="Unexpected error during export",
    )
    if result is None:
        return
    echo_export_result(result)
    if not result.success:
        raise SystemExit(ExitCode.FAIL)


def _list_tables_or_exit(
    service: _ExportCommandService,
    *,
    layer: str,
) -> None:
    """Handle table listing mode."""
    tables = _run_export_sync(
        lambda: service.list_tables(layer=_resolve_list_layer(layer)),
        table=f"<list:{layer}>",
        reason_prefix="CLI_EXPORT_LIST",
        domain_error_title="Export table listing failed with domain error",
        unexpected_error_title="Unexpected error during export table listing",
    )
    if tables is None:
        return
    if not tables:
        echo_info("No Delta tables found.")
        return
    echo_table_list(tables)

================================================================================
File: health.py
Path: cli\commands\health.py
================================================================================
"""Retained public health command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.command import (
        get_health_server_dependencies as get_health_server_dependencies,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        get_health_service as get_health_service,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health as health,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health_check as health_check,
    )
    from bioetl.interfaces.cli.commands.domains.health.command import (
        health_server_command as health_server_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.health.command")

================================================================================
File: health_rendering.py
Path: cli\commands\health_rendering.py
================================================================================
"""Compatibility support seam for health rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        all_health_results_healthy as all_health_results_healthy,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        build_health_result_lines as build_health_result_lines,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        build_health_server_info_lines as build_health_server_info_lines,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        render_health_results_json as render_health_results_json,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.health.rendering")

================================================================================
File: health_server_integration.py
Path: cli\commands\health_server_integration.py
================================================================================
"""Compatibility support seam for health-server integration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        DEFAULT_HEALTH_SERVER_PORT as DEFAULT_HEALTH_SERVER_PORT,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        add_health_server_options as add_health_server_options,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        echo_health_server_info as echo_health_server_info,
    )
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        health_server_context as health_server_context,
    )

alias_module(
    __name__, "bioetl.interfaces.cli.commands.domains.health.server_integration"
)

================================================================================
File: inspection_output.py
Path: cli\commands\inspection_output.py
================================================================================
"""Public inspection-output helpers for nested CLI command modules."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._inspection_output import emit_inspection_payload

__all__ = ["emit_inspection_payload"]

================================================================================
File: lineage.py
Path: cli\commands\lineage.py
================================================================================
"""Lineage inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )

__all__ = [
    "COMMANDS",
    "explain_command",
    "lineage",
    "show_fragment_command",
    "trace_command",
]

_NONE_BULLET = "  - none"


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage inspection service through composition on demand."""
    from bioetl.composition.control_plane_api import get_lineage_service as _impl

    return _impl()


def _render_node_lines(nodes: list[object]) -> list[str]:
    """Render node payloads as compact human-readable bullet lines."""
    lines: list[str] = []
    for item in nodes:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        node_type = item.get("node_type", "?")
        node_id = item.get("node_id", "?")
        label = item.get("label")
        suffix = f" label={label}" if label not in (None, "") else ""
        lines.append(f"  - {node_type}: {node_id}{suffix}")
    return lines or [_NONE_BULLET]


def _render_relation_lines(relations: list[object]) -> list[str]:
    """Render trace relations as compact human-readable bullet lines."""
    lines: list[str] = []
    for item in relations:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        node = item.get("node", {})
        fragment_id = item.get("fragment_id", "?")
        stored_fragment_id = item.get("stored_fragment_id")
        edge_type = item.get("edge_type", "?")
        fragment_suffix = ""
        if stored_fragment_id not in (None, "", fragment_id):
            fragment_suffix = f" occurrence={stored_fragment_id}"
        if isinstance(node, dict):
            node_id = node.get("node_id", "?")
            label = node.get("label")
            suffix = f" label={label}" if label not in (None, "") else ""
            lines.append(
                f"  - {edge_type} via {fragment_id}{fragment_suffix}: {node_id}{suffix}"
            )
            continue
        lines.append(f"  - {edge_type} via {fragment_id}{fragment_suffix}: {node}")
    return lines or [_NONE_BULLET]


def _render_fragment_payload(payload: dict[str, object]) -> str:
    """Render one fragment inspection payload in human-readable form."""
    fragment = payload.get("fragment", {})
    if not isinstance(fragment, dict):
        return json.dumps(payload, indent=2, default=str)
    lines = [
        "Lineage Fragment",
        f"  fragment_id: {fragment.get('fragment_id')}",
        f"  stored_fragment_id: {fragment.get('stored_fragment_id')}",
        f"  run_id: {fragment.get('run_id')}",
        f"  manifest_id: {fragment.get('manifest_id')}",
        f"  created_at: {fragment.get('created_at')}",
        f"  nodes: {len(fragment.get('nodes', [])) if isinstance(fragment.get('nodes'), list) else 0}",
        f"  edges: {len(fragment.get('edges', [])) if isinstance(fragment.get('edges'), list) else 0}",
        "",
        "Nodes",
    ]
    nodes = fragment.get("nodes")
    if isinstance(nodes, list):
        lines.extend(_render_node_lines(nodes))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_trace_payload(payload: dict[str, object]) -> str:
    """Render one trace payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    stored_fragment_ids = payload.get("stored_fragment_ids")
    stored_fragment_count = (
        len(stored_fragment_ids) if isinstance(stored_fragment_ids, list) else 0
    )
    lines = [
        "Lineage Trace",
        f"  dataset_ref: {payload.get('dataset_ref')}",
        f"  fragments: {fragment_count}",
        f"  stored_fragments: {stored_fragment_count}",
        "",
        "Upstream",
    ]
    upstream = payload.get("upstream")
    if isinstance(upstream, list):
        lines.extend(_render_relation_lines(upstream))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Downstream"])
    downstream = payload.get("downstream")
    if isinstance(downstream, list):
        lines.extend(_render_relation_lines(downstream))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_explain_payload(payload: dict[str, object]) -> str:
    """Render one run explanation payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    stored_fragment_ids = payload.get("stored_fragment_ids")
    stored_fragment_count = (
        len(stored_fragment_ids) if isinstance(stored_fragment_ids, list) else 0
    )
    lines = [
        "Lineage Run",
        f"  identifier: {payload.get('identifier')}",
        f"  run_id: {payload.get('run_id')}",
        f"  manifest_id: {payload.get('manifest_id')}",
        f"  fragments: {fragment_count}",
        f"  stored_fragments: {stored_fragment_count}",
        "",
        "Produced Datasets",
    ]
    produced_datasets = payload.get("produced_datasets")
    if isinstance(produced_datasets, list):
        lines.extend(_render_node_lines(produced_datasets))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Produced Bronze Batches"])
    produced_bronze_batches = payload.get("produced_bronze_batches")
    if isinstance(produced_bronze_batches, list):
        lines.extend(_render_node_lines(produced_bronze_batches))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Transforms"])
    transforms = payload.get("transforms")
    if isinstance(transforms, list):
        lines.extend(_render_node_lines(transforms))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Source Systems"])
    source_systems = payload.get("source_systems")
    if isinstance(source_systems, list):
        lines.extend(_render_node_lines(source_systems))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Source Requests"])
    source_requests = payload.get("source_requests")
    if isinstance(source_requests, list):
        lines.extend(_render_node_lines(source_requests))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "fragment" in payload:
        return _render_fragment_payload(payload)
    if "dataset_ref" in payload:
        return _render_trace_payload(payload)
    if "identifier" in payload:
        return _render_explain_payload(payload)
    return json.dumps(payload, indent=2, default=str)


def _resolve_explain_identifier(
    *,
    run_id: str | None,
    manifest_id: str | None,
) -> str | None:
    """Resolve exactly one explain identifier from CLI options."""
    if bool(run_id) == bool(manifest_id):
        return None
    return run_id if run_id is not None else manifest_id


@click.group()  # type: ignore[untyped-decorator]
def lineage() -> None:
    """Inspect persisted lineage fragments and run traceability."""


@lineage.command("show-fragment")  # type: ignore[untyped-decorator]
@click.argument("fragment_id")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_fragment_command(fragment_id: str, output_format: str) -> None:
    """Show one lineage fragment by FRAGMENT_ID."""
    service = get_lineage_service()
    try:
        result = service.show_fragment(fragment_id)
    except ValueError as exc:
        echo_error("Lineage fragment not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


@lineage.command("trace")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--dataset-ref",
    required=True,
    help="Canonical dataset/node ref, e.g. silver:chembl.activity@12",
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def trace_command(dataset_ref: str, output_format: str) -> None:
    """Trace immediate upstream and downstream lineage for one dataset ref."""
    service = get_lineage_service()
    try:
        result = service.trace(dataset_ref)
    except ValueError as exc:
        echo_error("Lineage trace not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


@lineage.command("explain")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--run-id", default=None, help="Resolve lineage by RUN_ID"
)
@click.option(  # type: ignore[untyped-decorator]
    "--manifest-id", default=None, help="Resolve lineage by MANIFEST_ID"
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def explain_command(
    run_id: str | None,
    manifest_id: str | None,
    output_format: str,
) -> None:
    """Explain the lineage graph attached to one run or manifest."""
    identifier = _resolve_explain_identifier(run_id=run_id, manifest_id=manifest_id)
    if identifier is None:
        echo_error(
            "Lineage explain failed",
            "Provide exactly one of --run-id or --manifest-id",
        )
        return

    service = get_lineage_service()
    try:
        result = service.explain_run(identifier)
    except ValueError as exc:
        echo_error("Lineage run explanation not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


COMMANDS = (
    explain_command,
    show_fragment_command,
    trace_command,
)

================================================================================
File: lock.py
Path: cli\commands\lock.py
================================================================================
"""Lock management commands for BioETL CLI.

Implements lock release and inspection commands.
Note: Uses in-memory locking - operations only affect current process.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from uuid import UUID

import click

from bioetl.domain.types import RunID
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services.lock_service import LockService

__all__ = [
    "COMMANDS",
    "check_command",
    "lock",
    "release_command",
]


@click.group()  # type: ignore[untyped-decorator]
def lock() -> None:
    """Manage pipeline locks."""


def get_lock_service() -> LockService:
    """Load the lock service through composition on demand."""
    from bioetl.composition.control_plane_api import get_lock_service as _impl

    return _impl()


@lock.command("release")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name (lock key)"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id", required=True, help="Run ID that holds the lock"
)
@click.option(  # type: ignore[untyped-decorator]
    "--exclusive", is_flag=True, help="Release exclusive lock"
)
def release_command(pipeline: str, run_id: str, exclusive: bool) -> None:
    """Release a pipeline lock.

    Use this to clean up stale locks from crashed processes.
    Only works if the specified run-id holds the lock.

    Examples:

        bioetl lock release --pipeline chembl_activity --run-id abc123

        bioetl lock release --pipeline chembl_activity --run-id abc123 --exclusive

    Args:
        pipeline: Pipeline.
        run_id: Pipeline run identifier.
        exclusive: Whether to exclusive.
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        released = await service.release_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
            exclusive=exclusive,
        )

        if released:
            echo_info(f"Lock released for {pipeline}")
        else:
            echo_warning(f"Lock not released (not held by run-id {run_id})")

    asyncio.run(_run())


@lock.command("check")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name (lock key)"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id", required=True, help="Run ID to check"
)
def check_command(pipeline: str, run_id: str) -> None:
    """Check if a lock is held by a specific run-id.

    Examples:

        bioetl lock check --pipeline chembl_activity --run-id abc123

    Args:
        pipeline: Pipeline.
        run_id: Pipeline run identifier.
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        is_held = await service.check_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
        )

        if is_held:
            echo_info(f"Lock for {pipeline} IS held by run-id {run_id}")
        else:
            echo_info(f"Lock for {pipeline} is NOT held by run-id {run_id}")

    asyncio.run(_run())


COMMANDS = (release_command, check_command)

================================================================================
File: maintenance.py
Path: cli\commands\maintenance.py
================================================================================
"""Retained public maintenance command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.command import (
        maintenance as maintenance,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.command")

================================================================================
File: metrics_server_integration.py
Path: cli\commands\metrics_server_integration.py
================================================================================
"""Compatibility support seam for metrics-server integration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
        ensure_metrics_server_started as ensure_metrics_server_started,
    )
    from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
        metrics_server_context as metrics_server_context,
    )

alias_module(
    __name__,
    "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration",
)

================================================================================
File: plan.py
Path: cli\commands\plan.py
================================================================================
"""Retained public plan command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.plan import (
        get_contract_migration_service as get_contract_migration_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.plan import (
        plan_command as plan_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.plan")

================================================================================
File: quarantine.py
Path: cli\commands\quarantine.py
================================================================================
"""Retained public quarantine command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        get_quarantine_manager as get_quarantine_manager,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        get_quarantine_service as get_quarantine_service,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.command import (
        quarantine as quarantine,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.command")

================================================================================
File: quarantine_execution.py
Path: cli\commands\quarantine_execution.py
================================================================================
"""Compatibility support seam for quarantine execution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        QuarantineExecutionPolicy as QuarantineExecutionPolicy,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        run_quarantine_async as run_quarantine_async,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        run_quarantine_sync as run_quarantine_sync,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.execution")

================================================================================
File: quarantine_rendering.py
Path: cli\commands\quarantine_rendering.py
================================================================================
"""Compatibility support seam for quarantine rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
        build_purge_preview_lines as build_purge_preview_lines,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
        build_quarantine_stats_lines as build_quarantine_stats_lines,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
        build_replay_preview_lines as build_replay_preview_lines,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.rendering")

================================================================================
File: quarantine_support.py
Path: cli\commands\quarantine_support.py
================================================================================
"""Compatibility support seam for quarantine helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _inspect_quarantine as _inspect_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _purge_quarantine as _purge_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _replay_quarantine as _replay_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _resolve_quarantine_record as _resolve_quarantine_record,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _show_quarantine_stats as _show_quarantine_stats,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.support")

================================================================================
File: run.py
Path: cli\commands\run.py
================================================================================
"""Retained public run command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.command import (
        build_run_options as build_run_options,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        execute_run as execute_run,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        get_cli_run_orchestration_service as get_cli_run_orchestration_service,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import (
        handle_cli_failure as handle_cli_failure,
    )
    from bioetl.interfaces.cli.commands.domains.run.command import run as run
    from bioetl.interfaces.cli.commands.domains.run.command import (
        validate_options as validate_options,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run.command")

================================================================================
File: run_all.py
Path: cli\commands\run_all.py
================================================================================
"""Retained public run-all command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run_all.command import (
        get_pipeline_runner_service as get_pipeline_runner_service,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command import (
        run_all as run_all,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.run_all.command")

================================================================================
File: run_composite.py
Path: cli\commands\run_composite.py
================================================================================
"""Retained public run-composite command seam over the canonical domain module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        bootstrap_composite_runner as bootstrap_composite_runner,
    )
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        load_composite_config as load_composite_config,
    )
    from bioetl.interfaces.cli.commands.domains.composite.command import (
        run_composite as run_composite,
    )

    _CompositeRuntimeConfigType = CompositeRuntimeConfig

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.composite.command")

================================================================================
File: run_manifest.py
Path: cli\commands\run_manifest.py
================================================================================
"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "COMMANDS",
    "diff_command",
    "run_manifest",
    "show_command",
]


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_run_manifest_service as _impl,
    )

    return cast("RunManifestInspectionService", _impl())


@click.group()  # type: ignore[untyped-decorator]
def run_manifest() -> None:
    """Inspect control-plane run manifests and ledger history."""


@run_manifest.command("show")  # type: ignore[untyped-decorator]
@click.argument("identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_command(identifier: str, output_format: str) -> None:
    """Show one manifest by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("diff")  # type: ignore[untyped-decorator]
@click.argument("left_identifier")  # type: ignore[untyped-decorator]
@click.argument("right_identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diff_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Diff two manifests resolved by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.diff(left_identifier, right_identifier)
    except ValueError as exc:
        echo_error("Run manifest diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


COMMANDS = (
    diff_command,
    show_command,
)

================================================================================
File: run_manifest_output.py
Path: cli\commands\run_manifest_output.py
================================================================================
"""Public seam for run-manifest text rendering helpers."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._run_manifest_output import render_text_payload

__all__ = ["render_text_payload"]

================================================================================
File: vacuum.py
Path: cli\commands\vacuum.py
================================================================================
"""Retained public vacuum command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        get_lifecycle_service as get_lifecycle_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        get_vacuum_service as get_vacuum_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        vacuum_all_command as vacuum_all_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
        vacuum_command as vacuum_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.vacuum")

================================================================================
File: exit_codes.py
Path: cli\exit_codes.py
================================================================================
"""Standardized CLI exit codes for BioETL.

Exit codes follow Unix conventions and sysexits.h standards:
- 0: Success (EX_OK)
- 1: General errors (EX_FAIL)
- 64-78: Reserved for standard exit codes

Custom BioETL codes (80-99) for specific scenarios.

References:
- BSD sysexits.h: https://man.freebsd.org/cgi/man.cgi?query=sysexits
- POSIX: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Standardized exit codes for CLI commands.

    Follows Unix conventions with custom BioETL-specific codes.
    """

    # Success
    OK = 0  # Successful execution

    # General errors (1-63 reserved)
    FAIL = 1  # Unspecified error

    # Standard sysexits.h codes (64-78)
    EX_USAGE = 64  # Command line usage error
    EX_DATAERR = 65  # Data format error
    EX_NOINPUT = 66  # Cannot open input
    EX_NOUSER = 67  # Addressee unknown
    EX_NOHOST = 68  # Host name unknown
    EX_UNAVAILABLE = 69  # Service unavailable
    EX_SOFTWARE = 70  # Internal software error
    EX_OSERR = 71  # System error (e.g., can't fork)
    EX_OSFILE = 72  # Critical OS file missing
    EX_CANTCREAT = 73  # Can't create output file
    EX_IOERR = 74  # Input/output error
    EX_TEMPFAIL = 75  # Temporary failure; user can retry
    EX_PROTOCOL = 76  # Remote error in protocol
    EX_NOPERM = 77  # Permission denied
    EX_CONFIG = 78  # Configuration error

    # BioETL-specific codes (80-99)
    CONFIG_ERROR = 80  # Pipeline configuration error
    INIT_ERROR = 81  # Initialization failure
    PIPELINE_ERROR = 82  # Pipeline execution error
    DATA_QUALITY_ERROR = 83  # Data quality threshold exceeded
    LOCK_ERROR = 84  # Lock acquisition/validation failure
    STORAGE_ERROR = 85  # Storage operation failure
    NETWORK_ERROR = 86  # Network/API error
    CHECKPOINT_ERROR = 87  # Checkpoint save/load failure

    # Signal-related (128 + signal number)
    SIGINT = 130  # Interrupted by SIGINT (Ctrl+C) [128 + 2]
    SIGTERM = 143  # Terminated by SIGTERM [128 + 15]


# Mapping of exception types to exit codes
# Used by CLI error handlers to determine appropriate exit codes
EXCEPTION_EXIT_CODES: dict[str, ExitCode] = {
    # Critical errors
    "CriticalError": ExitCode.FAIL,
    "InfrastructureError": ExitCode.STORAGE_ERROR,
    "LockAcquisitionError": ExitCode.LOCK_ERROR,
    "LockLostError": ExitCode.LOCK_ERROR,
    "StorageError": ExitCode.STORAGE_ERROR,
    # Configuration errors
    "ValueError": ExitCode.CONFIG_ERROR,
    "FileNotFoundError": ExitCode.EX_NOINPUT,
    "ConfigValidationError": ExitCode.CONFIG_ERROR,
    # Data quality errors
    "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
    "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
    "SchemaViolationError": ExitCode.DATA_QUALITY_ERROR,
    # Network errors
    "NetworkError": ExitCode.NETWORK_ERROR,
    "RateLimitError": ExitCode.NETWORK_ERROR,
    "ApiError": ExitCode.NETWORK_ERROR,
    "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
    # Recoverable errors (temporary failures)
    "RecoverableError": ExitCode.EX_TEMPFAIL,
    "RetryExhaustedError": ExitCode.EX_TEMPFAIL,
    # Shutdown
    "PipelineShutdownError": ExitCode.SIGINT,
    "KeyboardInterrupt": ExitCode.SIGINT,
}


def get_exit_code_for_exception(exc: BaseException) -> ExitCode:
    """Get the appropriate exit code for an exception.

    Args:
        exc: The exception to get exit code for.

    Returns:
        The appropriate ExitCode, defaulting to FAIL for unknown exceptions.

    """
    exc_type_name = type(exc).__name__

    # Check direct mapping first
    if exc_type_name in EXCEPTION_EXIT_CODES:
        return EXCEPTION_EXIT_CODES[exc_type_name]

    # Check MRO for parent class mappings
    for base_class in type(exc).__mro__:
        base_name = base_class.__name__
        if base_name in EXCEPTION_EXIT_CODES:
            return EXCEPTION_EXIT_CODES[base_name]

    return ExitCode.FAIL


__all__ = [
    "EXCEPTION_EXIT_CODES",
    "ExitCode",
    "get_exit_code_for_exception",
]

================================================================================
File: formatters.py
Path: cli\formatters.py
================================================================================
"""CLI output formatters for BioETL.

Provides formatting utilities for CLI output. These are pure presentation
functions without business logic - they only transform data into
human-readable format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services import (
        ColumnInfo,
        ExportResult,
        TableInfo,
        TablePreview,
        TableVacuumResult,
        VacuumAllResult,
    )


__all__ = [
    "echo_checkpoint",
    "echo_cleanup_preview",
    "echo_dry_run_prefix",
    "echo_error",
    "echo_export_preview",
    "echo_export_result",
    "echo_info",
    "echo_quarantine_record",
    "echo_table_list",
    "echo_vacuum_all_summary",
    "echo_vacuum_result",
    "echo_warning",
    "format_bytes",
]


def format_bytes(b: int) -> str:
    """Format bytes as human-readable string.

    Args:
        b: Number of bytes.

    Returns:
        Human-readable string (e.g., "1.5 GB", "256 KB").
    """
    for unit, divisor in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if b >= divisor:
            return f"{b / divisor:.2f} {unit}"
    return f"{b} bytes"


def echo_cleanup_preview(preview: CleanupPreview) -> None:
    """Output cleanup preview information.

    Args:
        preview: CleanupPreview with information about what would be cleared.
    """
    click.echo("\nFiles/directories that would be cleared:")

    if preview.silver.exists:
        click.echo(
            f"  Silver: {preview.silver.path} ({preview.silver.file_count} files)"
        )
    else:
        click.echo(f"  Silver: {preview.silver.path} (does not exist)")

    if preview.gold:
        if preview.gold.exists:
            click.echo(f"  Gold: {preview.gold.path} ({preview.gold.file_count} files)")
        else:
            click.echo(f"  Gold: {preview.gold.path} (does not exist)")

    click.echo(f"\nTotal items that would be cleared: ~{preview.total_files}")
    click.echo("\nNo changes were made (dry-run mode).")


def echo_vacuum_result(result: TableVacuumResult, dry_run: bool) -> None:
    """Output vacuum result for a single table.

    Args:
        result: TableVacuumResult with operation outcome.
        dry_run: Whether this was a dry run.
    """
    prefix = "[DRY-RUN] " if dry_run else ""
    action = "Would vacuum" if dry_run else "Vacuuming"

    click.echo(f"{prefix}{action} {result.layer}/{result.table_name}...")

    if result.error:
        click.echo(f"  Error: {result.error}", err=True)
    else:
        result_verb = "Would remove" if dry_run else "Removed"
        click.echo(f"  {result_verb} {result.files_removed} files")


def echo_vacuum_all_summary(result: VacuumAllResult) -> None:
    """Output summary for vacuum-all operation.

    Args:
        result: VacuumAllResult with aggregated statistics.
    """
    result_verb = "would remove" if result.dry_run else "removed"
    click.echo(f"\nTotal: {result_verb} {result.total_files_removed} files")

    if result.failed_tables:
        click.echo(f"Failed tables: {', '.join(result.failed_tables)}", err=True)


def echo_quarantine_record(
    record: JsonDict,  # Any: CLI/HTTP response values are heterogeneous
) -> None:  # Any: quarantine record has heterogeneous values
    """Output a single quarantine record.

    Args:
        record: Dictionary with quarantine record data.
    """
    error_code = record.get("error_code") or "UNKNOWN"
    payload_hash = record.get("payload_hash")
    dq_status = record.get("dq_status") or "UNKNOWN"
    ingestion_ts = record.get("ingestion_ts")
    payload = record.get("payload")
    payload_display = payload if payload is not None else "—"
    header_parts = [f"Error: {error_code}", f"Status: {dq_status}"]
    if isinstance(payload_hash, str) and payload_hash:
        header_parts.append(f"Hash: {payload_hash[:16]}...")
    if ingestion_ts:
        header_parts.append(f"Ingested: {ingestion_ts}")
    click.echo(" | ".join(header_parts))

    error_details = record.get("error_details")
    if isinstance(error_details, dict) and error_details:
        if error_details.get("message"):
            click.echo(f"Reason: {error_details['message']}")
        for label, key in (
            ("Reason Code", "reason_code"),
            ("Rule Type", "rule_type"),
            ("Field", "field"),
            ("Operator", "operator"),
            ("Expected", "expected"),
            ("Actual", "actual"),
        ):
            value = error_details.get(key)
            if value is None or value == "":
                continue
            click.echo(f"{label}: {value}")

    click.echo(f"Payload: {payload_display}")
    click.echo("")


def echo_checkpoint(checkpoint: str) -> None:
    """Output a single checkpoint entry.

    Args:
        checkpoint: Checkpoint identifier string.
    """
    click.echo(f"- {checkpoint}")


def echo_error(message: str, detail: str | None = None) -> None:
    """Output error message to stderr.

    Args:
        message: Main error message.
        detail: Optional additional detail.
    """
    if detail:
        click.echo(f"{message}: {detail}", err=True)
    else:
        click.echo(message, err=True)


def echo_info(message: str) -> None:
    """Output informational message.

    Args:
        message: Message to output.
    """
    click.echo(message)


def echo_warning(message: str) -> None:
    """Output warning message.

    Args:
        message: Warning message to output.
    """
    click.echo(f"WARNING: {message}")


def echo_dry_run_prefix(message: str) -> None:
    """Output message with dry-run prefix.

    Args:
        message: Message to prefix with [DRY-RUN].
    """
    click.echo(f"[DRY-RUN] {message}")


# =============================================================================
# Export formatters
# =============================================================================


def echo_table_list(tables: list[TableInfo]) -> None:
    """Output list of available Delta tables.

    Args:
        tables: List of TableInfo objects to display.
    """
    click.echo("\nAvailable Delta tables:\n")

    current_layer = ""
    for table in tables:
        if table.layer != current_layer:
            current_layer = table.layer
            click.echo(f"  {current_layer.upper()}:")

        click.echo(f"    {table.name}")

    click.echo()


def _format_preview_row(
    row: dict[str, object],
    columns: Sequence[ColumnInfo],
    max_cols: int = 5,
) -> str:
    """Format a single sample row for preview display."""
    values = []
    for col in columns[:max_cols]:
        val = str(row.get(col.name, ""))
        values.append(f"{val[:30]}..." if len(val) > 30 else val)
    if len(columns) > max_cols:
        values.append("...")
    return " | ".join(values)


def echo_export_preview(preview: TablePreview) -> None:
    """Output table preview with schema and sample data.

    Args:
        preview: TablePreview with schema and sample rows.
    """
    click.echo(f"\nTable: {preview.table_name} ({preview.layer})")
    click.echo(f"Rows: {preview.row_count:,}")
    click.echo(f"\nSchema ({len(preview.columns)} columns):")

    for col in preview.columns:
        nullable = " (nullable)" if col.nullable else ""
        click.echo(f"  {col.name}: {col.type}{nullable}")

    if not preview.sample_rows:
        click.echo()
        return

    click.echo(f"\nSample data ({len(preview.sample_rows)} rows):")
    click.echo("-" * 60)

    if preview.columns:
        col_names = [c.name for c in preview.columns[:5]]
        if len(preview.columns) > 5:
            col_names.append("...")
        click.echo(" | ".join(col_names))
        click.echo("-" * 60)

    for row in preview.sample_rows:
        click.echo(_format_preview_row(row, preview.columns))

    click.echo()


def echo_export_result(result: ExportResult) -> None:
    """Output export operation result.

    Args:
        result: ExportResult with export outcome.
    """
    if result.success:
        click.echo(f"\nExported {result.row_count:,} rows to {result.format.upper()}")
        click.echo(f"Output: {result.output_path}")
    else:
        click.echo(f"\nExport failed: {result.error}", err=True)

================================================================================
File: main.py
Path: cli\main.py
================================================================================
"""Main CLI entry point for BioETL.

This module provides the main Click group and registers command groups lazily.
It keeps import-time overhead low for targeted CLI tests and single-command use.
"""

from __future__ import annotations

from importlib import import_module

import click

from bioetl import __version__ as BIOETL_VERSION
from bioetl.interfaces.cli.registry_helpers import (
    _build_registered_registry,
    create_registry,
    register_all_pipelines,
)

__all__ = [
    "build_cli_registry",
    "cli",
    "main",
]

_LAZY_COMMAND_SPECS: dict[str, tuple[str, str, str]] = {
    "adr": ("bioetl.interfaces.cli.commands.adr", "adr", "ADR tooling"),
    "checkpoint": (
        "bioetl.interfaces.cli.commands.checkpoint",
        "checkpoint",
        "Manage pipeline checkpoints",
    ),
    "config": (
        "bioetl.interfaces.cli.commands.config",
        "config",
        "Inspect and validate configuration",
    ),
    "dq": (
        "bioetl.interfaces.cli.commands.config_dq",
        "dq",
        "Data quality configuration commands",
    ),
    "diagnostics": (
        "bioetl.interfaces.cli.commands.diagnostics",
        "diagnostics",
        "Unified operator diagnostics across metrics, health, checkpoints, manifests, and quarantine",
    ),
    "debug": (
        "bioetl.interfaces.cli.commands.debug",
        "debug",
        "Run a pipeline with breakpoints",
    ),
    "export": (
        "bioetl.interfaces.cli.commands.export",
        "export_command",
        "Export pipeline artifacts",
    ),
    "health": (
        "bioetl.interfaces.cli.commands.health",
        "health",
        "Health checks and diagnostics",
    ),
    "lineage": (
        "bioetl.interfaces.cli.commands.lineage",
        "lineage",
        "Inspect pipeline lineage",
    ),
    "lock": (
        "bioetl.interfaces.cli.commands.lock",
        "lock",
        "Inspect and manage local runtime locks",
    ),
    "maintenance": (
        "bioetl.interfaces.cli.commands.maintenance",
        "maintenance",
        "Maintenance operations",
    ),
    "quarantine": (
        "bioetl.interfaces.cli.commands.quarantine",
        "quarantine",
        "Manage quarantine records",
    ),
    "run": (
        "bioetl.interfaces.cli.commands.run",
        "run",
        "Run a configured pipeline",
    ),
    "run-all": (
        "bioetl.interfaces.cli.commands.run_all",
        "run_all",
        "Run all configured pipelines",
    ),
    "run-composite": (
        "bioetl.interfaces.cli.commands.run_composite",
        "run_composite",
        "Run a composite pipeline",
    ),
    "run-manifest": (
        "bioetl.interfaces.cli.commands.run_manifest",
        "run_manifest",
        "Inspect run manifests and ledgers",
    ),
}


def _load_cli_command(command_name: str) -> click.Command | click.Group | None:
    """Import a CLI command module only when the command is requested."""
    spec = _LAZY_COMMAND_SPECS.get(command_name)
    if spec is None:
        return None

    module_name, attribute_name, _help_text = spec
    command = getattr(import_module(module_name), attribute_name)
    if getattr(command, "name", command_name) != command_name:
        command.name = command_name
    return command


class _LazyCliGroup(click.Group):
    """Click group that resolves BioETL subcommands on demand."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        del ctx
        return list(_LAZY_COMMAND_SPECS)

    def get_command(
        self,
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | click.Group | None:
        del ctx
        if cmd_name in self.commands:
            return self.commands[cmd_name]

        command = _load_cli_command(cmd_name)
        if command is not None:
            self.commands[cmd_name] = command
        return command

    def format_commands(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
    ) -> None:
        del ctx
        rows = [
            (name, help_text)
            for name, (_module_name, _attribute_name, help_text) in (
                _LAZY_COMMAND_SPECS.items()
            )
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


def _build_main_registry() -> object:
    """Build an explicit registry for the canonical process entrypoint.

    Uses interface-layer registry helpers so the CLI entry module does not
    import composition modules directly while preserving historical patch
    points used by tests.
    """
    return _build_registered_registry(
        create_registry_fn=create_registry,
        register_all_pipelines_fn=register_all_pipelines,
    )


def build_cli_registry() -> object:
    """Compatibility seam retaining the historical main-level registry builder."""
    return _build_main_registry()


@click.group(cls=_LazyCliGroup)  # type: ignore[untyped-decorator]
@click.version_option(version=BIOETL_VERSION)  # type: ignore[untyped-decorator]
@click.pass_context  # type: ignore[untyped-decorator]
def cli(ctx: click.Context) -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    del ctx


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

================================================================================
File: registry_helpers.py
Path: cli\registry_helpers.py
================================================================================
"""Registry helpers for CLI entrypoints.

These helpers provide the canonical explicit-registry path for CLI code paths
without ambient global registry state. Each call returns a fresh, explicitly
populated ``PipelineRegistry`` instance.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "build_cli_registry",
    "create_registry",
    "register_all_pipelines",
]


def create_registry() -> PipelineRegistry:
    """Create a fresh registry via the public composition facade."""
    from bioetl.composition.registry_api import create_registry as _impl

    return _impl()


def register_all_pipelines(*, registry: PipelineRegistry | None = None) -> None:
    """Register pipelines via the public composition facade."""
    from bioetl.composition.registry_api import register_all_pipelines as _impl

    _impl(registry=registry)


def _build_registered_registry(
    *,
    create_registry_fn: Callable[[], PipelineRegistry],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Build and populate a fresh registry using explicit collaborators."""
    registry = create_registry_fn()
    register_all_pipelines_fn(registry=registry)
    return registry


def build_cli_registry() -> PipelineRegistry:
    """Build a fresh explicit registry for one CLI invocation."""
    return _build_registered_registry(
        create_registry_fn=create_registry,
        register_all_pipelines_fn=register_all_pipelines,
    )

================================================================================
File: __init__.py
Path: http\__init__.py
================================================================================
"""HTTP interface module for BioETL.

Provides HTTP endpoints for health checks and monitoring.
"""

from __future__ import annotations

from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.types import HealthResponse

__all__ = ["HealthResponse", "HealthServer"]

================================================================================
File: health_server.py
Path: http\health_server.py
================================================================================
"""HTTP Health Server for BioETL.

Provides standard liveness and readiness probes.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin
from bioetl.interfaces.http.health_server_routing_mixin import (
    HealthServerRoutingMixin,
)
from bioetl.interfaces.http.health_server_state_mixin import HealthServerStateMixin
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.domain.ports import HealthMonitorPort, LoggerPort


class HealthServer(
    HealthServerHTTPMixin,
    HealthServerRoutingMixin,
    HealthServerStateMixin,
):
    """Async HTTP server for health check endpoints."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8081,
        health_monitor: HealthMonitorPort | None = None,
        quarantine_service: QuarantineService | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize health server.

        Args:
            host: IP address to bind the server to. Defaults to localhost.
            port: TCP port to listen on. Defaults to 8081.
            health_monitor: Optional monitor providing provider health states for
                /health/ready and /health/providers endpoints. Endpoints report
                healthy with no provider data when None.
            quarantine_service: Optional read-only service for
                /ops/quarantine/* explorer endpoints.
            logger: Optional LoggerPort for structured server event logging.
                Server events are silently dropped when None.
        """
        self.host = host
        self.port = port
        self._health_monitor = health_monitor
        self._quarantine_service = quarantine_service
        self._logger = logger
        self._server: asyncio.Server | None = None
        self._start_time: float | None = None
        self._request_error_allowlist = (
            UnicodeDecodeError,
            ValueError,
            RuntimeError,
            OSError,
            ConnectionError,
            asyncio.IncompleteReadError,
        )
        self._writer_close_allowlist = (
            OSError,
            RuntimeError,
            ConnectionError,
            BrokenPipeError,
        )

    async def start(self) -> None:
        """Start the health server."""
        self._start_time = time.monotonic()
        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self.host,
                self.port,
                reuse_address=True,
            )
        except OSError as exc:
            if self._logger:
                self._logger.warning(
                    "health_server_bind_failed",
                    host=self.host,
                    port=self.port,
                    error=str(exc),
                    reason_code="HEALTH_SERVER_BIND_FAILED",
                )
            raise
        if self._logger:
            self._logger.info("health_server_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        """Stop the health server gracefully."""
        if not self._server:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        if self._logger:
            self._logger.info("health_server_stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server is not None and self._server.is_serving()

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time


async def run_health_server(
    host: str = "0.0.0.0",
    port: int = 8081,
    health_monitor: HealthMonitorPort | None = None,
    quarantine_service: QuarantineService | None = None,
    logger: LoggerPort | None = None,
) -> None:
    """Run the health server until interrupted.

    Starts the HealthServer and keeps it alive until the coroutine is cancelled
    (e.g., via asyncio.CancelledError from a task group or signal handler).

    Args:
        host: IP address to bind to. Defaults to all interfaces (0.0.0.0).
        port: TCP port to listen on. Defaults to 8081.
        health_monitor: Optional monitor providing provider health states.
            Health endpoints report no provider data when None.
        quarantine_service: Optional read-only quarantine explorer service.
        logger: Optional LoggerPort for structured server event logging.
    """
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=health_monitor,
        quarantine_service=quarantine_service,
        logger=logger,
    )
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    finally:
        await server.stop()


__all__ = ["HealthResponse", "HealthServer", "run_health_server"]

================================================================================
File: health_server_http_mixin.py
Path: http\health_server_http_mixin.py
================================================================================
"""HTTP protocol and request-processing helpers for HealthServer."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.interfaces.http.types import HealthResponse


class _RouteRequestSupport(Protocol):
    """Typed support contract for request routing implementation."""

    async def _route_request(
        self,
        writer: asyncio.StreamWriter,
        path: str,
    ) -> None: ...


class HealthServerHTTPMixin:
    """Mixin for low-level HTTP request/response lifecycle."""

    _logger: LoggerPort | None
    _request_error_allowlist: tuple[type[BaseException], ...]
    _writer_close_allowlist: tuple[type[BaseException], ...]

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming HTTP connection.

        Args:
            reader: Async stream reader for the incoming TCP connection.
            writer: Async stream writer for sending the HTTP response.
        """
        try:
            await self._process_request(reader, writer)
        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except self._request_error_allowlist as error:
            await self._handle_request_error(writer, error)
        finally:
            await self._close_writer(writer)

    async def _process_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process incoming HTTP request.

        Reads request line and headers, validates method, and dispatches to the
        appropriate route handler. Sends error responses for bad requests (400)
        and unsupported methods (405).

        Args:
            reader: Async stream reader providing the raw HTTP request bytes.
            writer: Async stream writer for sending the HTTP response.
        """
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return

        method, path = self._parse_request_line(request_line)
        if method is None or path is None:
            await self._send_response(writer, 400, "Bad Request")
            return

        await self._consume_headers(reader)

        if method != "GET":
            await self._send_response(writer, 405, "Method Not Allowed")
            return

        route_support = cast(_RouteRequestSupport, self)
        await route_support._route_request(writer, path)

    def _parse_request_line(self, request_line: bytes) -> tuple[str | None, str | None]:
        """Parse HTTP request line into method and path.

        Args:
            request_line: Raw bytes of the HTTP request line (e.g., b'GET /health HTTP/1.1\r\n').

        Returns:
            Tuple of (method, path), or (None, None) if the line is malformed.
        """
        request = request_line.decode("utf-8").strip()
        parts = request.split(" ")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    async def _consume_headers(self, reader: asyncio.StreamReader) -> None:
        """Read and discard HTTP headers.

        Args:
            reader: Async stream reader positioned after the request line.
        """
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

    async def _handle_request_error(
        self,
        writer: asyncio.StreamWriter,
        error: BaseException,
    ) -> None:
        """Handle request processing error.

        Logs the error with structured context and sends a 500 Internal Server Error
        response to the client.

        Args:
            writer: Async stream writer for sending the error response.
            error: Exception caught during request processing.
        """
        if self._logger:
            self._logger.error(
                "health_server_error",
                error=str(error),
                error_type=type(error).__name__,
                reason="request_processing_failed",
                reason_code="HEALTH_REQUEST_PROCESSING_FAILED",
            )
        await self._send_response(writer, 500, "Internal Server Error")

    async def _close_writer(self, writer: asyncio.StreamWriter) -> None:
        """Close the stream writer safely.

        Attempts to close the writer and drain pending data. Connection-level
        errors during close are logged at DEBUG level and suppressed to avoid
        masking the original response.

        Args:
            writer: Async stream writer to close.
        """
        try:
            writer.close()
            await writer.wait_closed()
        except self._writer_close_allowlist as close_error:
            if self._logger:
                self._logger.debug(
                    "health_server_writer_close_failed",
                    error=str(close_error),
                    error_type=type(close_error).__name__,
                    reason="writer_close_failed",
                    reason_code="HEALTH_WRITER_CLOSE_FAILED",
                )

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        response: HealthResponse,
    ) -> None:
        """Send JSON response.

        Serializes the HealthResponse to JSON and writes a complete HTTP/1.1
        response with Content-Type: application/json.

        Args:
            writer: Async stream writer for the outgoing response.
            response: HealthResponse to serialize and send.
        """
        body = response.to_json()
        status_code = response.http_status
        status_text = "OK" if status_code == 200 else "Service Unavailable"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None:
        """Send a generic JSON payload response."""
        body = json.dumps(payload, default=str)
        try:
            status_text = HTTPStatus(status_code).phrase
        except ValueError:
            status_text = "OK"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None:
        """Send plain-text JSON error response.

        Writes an HTTP/1.1 response with a JSON body containing the error message.

        Args:
            writer: Async stream writer for the outgoing response.
            status_code: HTTP status code (e.g., 400, 404, 500).
            message: Human-readable error message included in the JSON body.
        """
        body = json.dumps({"error": message})
        http_response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()


__all__ = ["HealthServerHTTPMixin"]

================================================================================
File: health_server_routing_mixin.py
Path: http\health_server_routing_mixin.py
================================================================================
"""Routing and endpoint handlers for HealthServer."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import parse_qs, unquote, urlsplit

from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.domain.ports import HealthMonitorPort

_NOT_FOUND_MESSAGE = "Not Found"


class _HealthResponseSupport(Protocol):
    """Typed support contract for HTTP response helpers."""

    async def _send_json_response(
        self,
        writer: asyncio.StreamWriter,
        response: HealthResponse,
    ) -> None: ...

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None: ...

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None: ...


class _HealthStateSupport(Protocol):
    """Typed support contract for state aggregation helpers."""

    def _get_overall_status(self) -> HealthStatus: ...

    def _get_provider_statuses(
        self,
    ) -> dict[str, JsonDict]: ...  # Any: provider-specific status fields


class HealthServerRoutingMixin:
    """Mixin for health endpoint routing and payload generation."""

    _health_monitor: HealthMonitorPort | None
    _quarantine_service: QuarantineService | None

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        raise NotImplementedError

    async def _route_request(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Route request to appropriate handler."""
        parsed_path = urlsplit(path)
        route_path = parsed_path.path
        query = self._parse_query_params(parsed_path.query)
        handlers = {
            "/health": self._handle_health,
            "/healthz": self._handle_health,
            "/health/live": self._handle_liveness,
            "/health/ready": self._handle_readiness,
            "/health/providers": self._handle_providers,
        }
        handler = handlers.get(route_path)
        if handler:
            response = await handler()
            response_support = cast(_HealthResponseSupport, self)
            await response_support._send_json_response(writer, response)
            return
        if route_path.startswith("/ops/quarantine/"):
            await self._route_quarantine_request(
                writer=writer,
                path=route_path,
                query=query,
            )
            return
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)

    def _parse_query_params(self, raw_query: str) -> dict[str, str]:
        """Parse query string into a single-value key/value mapping."""
        parsed = parse_qs(raw_query, keep_blank_values=False)
        return {key: values[-1] for key, values in parsed.items() if values}

    def _read_required_param(
        self,
        query: dict[str, str],
        name: str,
    ) -> str:
        """Return required query parameter or raise ValueError."""
        value = query.get(name)
        if value is None or not value.strip():
            raise ValueError(f"Missing required query parameter: {name}")
        return value.strip()

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None:
        """Return an optional query parameter as stripped value."""
        value = query.get(name)
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int:
        """Parse one integer query parameter with bounds validation."""
        raw = self._read_optional_param(query, name)
        if raw is None:
            return default
        parsed = int(raw)
        if parsed < minimum:
            raise ValueError(f"Invalid query parameter: {name} must be >= {minimum}")
        return parsed

    async def _route_quarantine_request(
        self,
        *,
        writer: asyncio.StreamWriter,
        path: str,
        query: dict[str, str],
    ) -> None:
        """Route record-level quarantine explorer requests."""
        response_support = cast(_HealthResponseSupport, self)
        if self._quarantine_service is None:
            await response_support._send_response(
                writer,
                503,
                "Quarantine explorer unavailable",
            )
            return

        try:
            if path == "/ops/quarantine/filtered-records":
                await self._handle_filtered_records(writer, query)
                return
            if path == "/ops/quarantine/filtered-stats":
                await self._handle_filtered_stats(writer, query)
                return
            if path == "/ops/quarantine/filter-options":
                await self._handle_filter_options(writer, query)
                return
            if path.startswith("/ops/quarantine/filtered-record/"):
                payload_hash = unquote(path.rsplit("/", maxsplit=1)[-1]).strip()
                if not payload_hash:
                    raise ValueError("Missing payload_hash in path")
                await self._handle_filtered_record_detail(writer, query, payload_hash)
                return
            await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
        except ValueError as exc:
            await response_support._send_response(writer, 400, str(exc))

    async def _handle_filtered_records(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle paginated list endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        limit = self._read_int_param(query, "limit", default=50, minimum=1)
        offset = self._read_int_param(query, "offset", default=0, minimum=0)
        payload = await self._quarantine_service.list_filtered_records(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            payload_hash=self._read_optional_param(query, "payload_hash"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
            limit=limit,
            offset=offset,
            sort=self._read_optional_param(query, "sort") or "ingestion_ts_desc",
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filtered_stats(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle aggregate stats endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        payload = await self._quarantine_service.get_filtered_stats(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            payload_hash=self._read_optional_param(query, "payload_hash"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filter_options(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
    ) -> None:
        """Handle variable-options endpoint for filtered Silver records."""
        assert self._quarantine_service is not None
        pipeline = self._read_required_param(query, "pipeline")
        payload = await self._quarantine_service.get_filtered_filter_options(
            pipeline=pipeline,
            run_type=self._read_optional_param(query, "run_type"),
            reason_code=self._read_optional_param(query, "reason_code"),
            field=self._read_optional_param(query, "field"),
            run_id=self._read_optional_param(query, "run_id"),
            from_ts=self._read_optional_param(query, "from"),
            to_ts=self._read_optional_param(query, "to"),
        )
        response_support = cast(_HealthResponseSupport, self)
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_filtered_record_detail(
        self,
        writer: asyncio.StreamWriter,
        query: dict[str, str],
        payload_hash: str,
    ) -> None:
        """Handle detail endpoint for one filtered Silver record."""
        assert self._quarantine_service is not None
        payload = await self._quarantine_service.get_filtered_record(
            payload_hash=payload_hash,
            pipeline=self._read_required_param(query, "pipeline"),
        )
        response_support = cast(_HealthResponseSupport, self)
        if payload is None:
            await response_support._send_response(writer, 404, _NOT_FOUND_MESSAGE)
            return
        await response_support._send_payload_response(writer, 200, payload)

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        await asyncio.sleep(0)
        state_support = cast(_HealthStateSupport, self)
        status = state_support._get_overall_status()
        checks: JsonDict = {  # Any: response payload values are heterogeneous
            "server": {
                "status": "healthy",
                "uptime_seconds": round(self.uptime_seconds, 2),
            }
        }
        if self._health_monitor:
            checks["providers"] = state_support._get_provider_statuses()
        return HealthResponse(
            status=status.value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live endpoint."""
        await asyncio.sleep(0)
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={
                "server": {
                    "status": "healthy",
                    "uptime_seconds": round(self.uptime_seconds, 2),
                }
            },
        )

    async def _handle_readiness(self) -> HealthResponse:
        """Handle /health/ready endpoint."""
        await asyncio.sleep(0)
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        state_support = cast(_HealthStateSupport, self)
        provider_statuses = state_support._get_provider_statuses()
        has_unhealthy = any(
            status.get("status") == "unhealthy" for status in provider_statuses.values()
        )
        status = "unhealthy" if has_unhealthy else "healthy"
        return HealthResponse(
            status=status,
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": provider_statuses},
        )

    async def _handle_providers(self) -> HealthResponse:
        """Handle /health/providers endpoint."""
        await asyncio.sleep(0)
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        state_support = cast(_HealthStateSupport, self)
        return HealthResponse(
            status=state_support._get_overall_status().value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": state_support._get_provider_statuses()},
        )


__all__ = ["HealthServerRoutingMixin"]

================================================================================
File: health_server_state_mixin.py
Path: http\health_server_state_mixin.py
================================================================================
"""Provider-state helpers for HealthServer."""

from __future__ import annotations

from bioetl.domain.ports import HealthMonitorPort
from bioetl.domain.types import HealthStatus, JsonDict


class HealthServerStateMixin:
    """Mixin with provider state aggregation helpers."""

    _health_monitor: HealthMonitorPort | None

    def _get_overall_status(self) -> HealthStatus:
        """Get overall health status from all providers."""
        if not self._health_monitor:
            return HealthStatus.HEALTHY
        states = self._health_monitor.get_all_states()
        if not states:
            return HealthStatus.HEALTHY
        statuses = [state.status for state in states.values()]
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        if any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _get_provider_statuses(
        self,
    ) -> dict[str, JsonDict]:  # Any: response payload values are heterogeneous
        """Get detailed status for all providers."""
        if not self._health_monitor:
            return {}
        states = self._health_monitor.get_all_states()
        return {
            name: {
                "status": state.status.value.lower(),
                "consecutive_errors": state.consecutive_errors,
            }
            for name, state in states.items()
        }


__all__ = ["HealthServerStateMixin"]

================================================================================
File: types.py
Path: http\types.py
================================================================================
"""HTTP interface types for BioETL."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from bioetl.domain.types import JsonDict


@dataclass
class HealthResponse:
    """Health check response data."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: JsonDict = field(  # Any: CLI/HTTP response values are heterogeneous
        default_factory=dict
    )  # Any: CLI/HTTP response values are heterogeneous

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(
            {
                "status": self.status,
                "timestamp": self.timestamp,
                "version": self.version,
                "checks": self.checks,
            },
            indent=2,
        )

    @property
    def http_status(self) -> int:
        """Return HTTP status code based on health status."""
        if self.status == "healthy":
            return 200
        elif self.status == "degraded":
            return 200  # Still operational
        return 503  # Service Unavailable


__all__ = ["HealthResponse"]

================================================================================
File: observability.py
Path: observability.py
================================================================================
"""Observability interface compatibility facade for BioETL.

This module remains import-safe for interface-layer consumers, but the
canonical public observability API now lives in
``bioetl.composition.observability_api``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability_api import ObservabilityDiagnosticsBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.observability_api import MetricsOperatorProfile

__all__ = [
    "MetricsServerError",
    "get_audit_service",
    "get_checkpoint_service",
    "get_health_service",
    "get_lineage_service",
    "get_metrics_operator_profile",
    "get_metrics_service",
    "get_observability_diagnostics_bundle",
    "get_observability_workflow_service",
    "get_quarantine_service",
    "get_run_manifest_service",
    "push_metrics_to_gateway",
    "start_metrics_server",
]


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through the canonical composition API."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Push metrics through the canonical composition API."""
    from bioetl.composition.observability_api import push_metrics_to_gateway as _impl

    return _impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
        logger=logger,
    )


def get_checkpoint_service() -> CheckpointService:
    """Load the checkpoint diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_checkpoint_service as _impl

    return _impl()


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_audit_service as _impl

    return _impl()


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_metrics_service as _impl

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Load the operator-facing metrics/admin diagnostics profile."""
    from bioetl.composition.observability_api import (
        get_metrics_operator_profile as _impl,
    )

    return _impl()


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load the observability workflow service through the canonical composition API."""
    from bioetl.composition.observability_api import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


def get_health_service() -> HealthService:
    """Load the health diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_health_service as _impl

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load the quarantine diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_quarantine_service as _impl

    return _impl()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_run_manifest_service as _impl

    return _impl()


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_lineage_service as _impl

    return _impl()


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Return the unified diagnostics bundle through the composition API."""
    from bioetl.composition.observability_api import (
        get_observability_diagnostics_bundle as _impl,
    )

    return _impl()

================================================================================
File: __init__.py
Path: orchestration\__init__.py
================================================================================
"""Orchestration utilities for pipeline execution.

This module is the designated location for orchestration utilities that
coordinate pipeline execution from interfaces layer (CLI, REST API, etc.).

REQ-ARCH-APP-001 states that external orchestration frameworks (Celery, Airflow)
must NOT be imported in application layer. This module serves as the integration
point for any such frameworks when needed.

Current status:
- Signal handlers were removed in 2025-12-31 (CLI handles KeyboardInterrupt directly)
- The module is reserved for future orchestration needs

For pipeline execution, use composition public APIs:
    from bioetl.composition.execution_api import run_pipeline
    from bioetl.composition.execution_api import get_pipeline_runner_service
"""

from __future__ import annotations

__all__: list[str] = []

