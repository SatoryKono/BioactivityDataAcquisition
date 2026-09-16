"""Writable control-plane path helpers shared outside runtime-builder fan-in."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, cast

__all__ = ["control_plane_root", "resolve_data_root"]

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


def resolve_data_root(settings: Settings) -> Path:
    """Resolve the writable data root used by run-manifest builders."""
    impl = cast(
        "Callable[..., Path]",
        import_module(
            "bioetl.composition.runtime_builders._run_manifest_data_roots"
        ).resolve_data_root,
    )
    return impl(settings)


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return resolve_data_root(settings) / "output" / "control" / leaf
