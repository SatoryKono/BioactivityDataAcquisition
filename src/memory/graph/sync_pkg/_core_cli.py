"""Command-line entry points extracted from the graph sync kernel (AUD-001 slice 1)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_normalization_operation_count",
    "_parser",
    "_run_apply_normalization_evidence_only",
    "_run_snapshot_cli",
    "_snapshot_operation_count",
    "_validate_cli_args",
    "_write_json",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli.main(argv)


def _parser() -> argparse.ArgumentParser:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._parser()


def _validate_cli_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    from memory.graph.sync_pkg import cli as _cli

    _cli._validate_cli_args(parser, args)


def _run_snapshot_cli(args: argparse.Namespace) -> int:
    """Execute the standard snapshot/sync CLI flow and return the exit code."""
    from memory.graph.sync_pkg import cli as _cli

    return _cli._run_snapshot_cli(args)


def _snapshot_operation_count(args: argparse.Namespace) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._snapshot_operation_count(args)


def _normalization_operation_count(summary: dict[str, JsonValue]) -> int:
    from memory.graph.sync_pkg import cli as _cli

    return _cli._normalization_operation_count(summary)


def _run_apply_normalization_evidence_only(args: argparse.Namespace) -> int:
    """Execute normalization-evidence-only mode and return the CLI exit code."""
    from memory.graph.sync_pkg import cli as _cli

    return _cli._run_apply_normalization_evidence_only(args)


def _write_json(path: Path, payload: JsonValue) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
