"""Shared thin callback dispatch for Click command entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import click

_InputT = TypeVar("_InputT")


def dispatch_cli_callback[InputT](
    click_context: click.Context,
    *,
    build_cli_input: Callable[[], _InputT],
    run_with_cli_policy: Callable[[click.Context, _InputT], None],
) -> None:
    """Build normalized CLI input and hand it off to the policy layer."""
    cli_input = build_cli_input()
    run_with_cli_policy(click_context, cli_input)
