"""ADR management commands for BioETL CLI.

Provides commands to list, show, and validate ADR documents.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

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


@click.group()
def adr() -> None:
    """ADR (Architecture Decision Records) utilities."""


def get_adr_service() -> AdrServicePort:
    """Load the ADR service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_adr_service as _impl,
    )

    impl = cast("Callable[[], AdrServicePort]", _impl)
    return impl()


@adr.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
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


@adr.command("show")
@click.argument("number", type=int)
@click.option("--raw", is_flag=True, help="Print raw markdown content")
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


@adr.command("validate")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
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
