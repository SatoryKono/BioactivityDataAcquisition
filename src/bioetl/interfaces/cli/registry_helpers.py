"""Registry helpers for CLI entrypoints.

These helpers provide the canonical explicit-registry path for CLI code paths
without ambient global registry state. Each call returns a fresh, explicitly
populated ``PipelineRegistry`` instance.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "build_cli_registry",
    "create_registry",
    "format_command_help_rows",
    "register_all_pipelines",
]

LazyCommandSpec = tuple[str, str, str]


class CommandHelpFormatter(Protocol):
    """Minimal Click help-formatter surface used by lazy CLI groups."""

    def section(self, name: str) -> AbstractContextManager[None]: ...

    def write_dl(self, rows: Sequence[tuple[str, str]]) -> None: ...


def create_registry() -> PipelineRegistry:
    """Create a fresh registry via the public composition facade."""
    from bioetl.composition.registry_api import create_registry as _impl

    return _impl()


def register_all_pipelines(*, registry: PipelineRegistry | None = None) -> None:
    """Register pipelines via the public composition facade."""
    from bioetl.composition.registry_api import register_all_pipelines as _impl

    _impl(registry=registry)


def format_command_help_rows(
    *,
    formatter: CommandHelpFormatter,
    eager_commands: Mapping[str, tuple[object, str]],
    lazy_commands: Mapping[str, LazyCommandSpec],
    section_title: str = "Commands",
) -> None:
    """Render deterministic help rows for eager plus lazy CLI commands."""
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, (_command, help_text) in eager_commands.items():
        seen.add(name)
        rows.append((name, help_text))
    for name, (_module_name, _attribute_name, help_text) in lazy_commands.items():
        if name in seen:
            continue
        seen.add(name)
        rows.append((name, help_text))
    if rows:
        with formatter.section(section_title):
            formatter.write_dl(rows)


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
