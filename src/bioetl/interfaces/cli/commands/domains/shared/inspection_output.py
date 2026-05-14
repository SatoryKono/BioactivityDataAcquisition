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
