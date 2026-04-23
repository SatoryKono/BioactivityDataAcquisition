"""Support helpers for quarantine rendering helpers."""

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
