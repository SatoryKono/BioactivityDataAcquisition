"""Thin wrapper re-exporting the canonical run-all command."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.run_all.command import run_all

__all__ = ["run_all"]
