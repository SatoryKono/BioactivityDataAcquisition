"""Offline replay of a digest-bound composite parent envelope."""

from __future__ import annotations

import asyncio
from copy import copy
from pathlib import Path

import click

from bioetl.composition.composite_catalog import replay_assay


@click.command("replay-assay")
@click.option(
    "--envelope",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--sha256",
    "envelope_hash",
    required=True,
    help="Digest from the parent run report.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="New isolated output directory.",
)
def replay_assay_command(envelope: Path, envelope_hash: str, output: Path) -> None:
    """Reproduce composite Silver/Gold without invoking provider APIs."""
    if envelope.name != "parent.json":
        raise click.ClickException("Expected a parent.json replay envelope")
    try:
        receipt = asyncio.run(replay_assay(envelope.parent, envelope_hash, output))
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(
        f"Offline composite replay verified: {receipt['records']} rows; Silver/Gold equal"
    )


# Keep independent names in the lazy command cache while sharing the callback.
replay_composite_command = copy(replay_assay_command)
replay_composite_command.name = "replay-composite"
