"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.pipeline_test_ownership_path import (
    _pipeline_test_ownership,
    _pipeline_test_ownership_path,
)

__all__ = [
    "_pipeline_test_payload",
]


def _pipeline_test_payload(
    root: Path,
    ownership_config: str,
) -> tuple[dict[str, object] | None, dict[object, object] | None]:
    ownership_path = _pipeline_test_ownership_path(root, ownership_config)
    if not ownership_path.is_file():
        return None, None
    payload = _read_yaml(ownership_path)
    return payload, _pipeline_test_ownership(payload)
