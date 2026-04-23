"""Support helpers for health rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        all_health_results_healthy as all_health_results_healthy,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        build_health_result_lines as build_health_result_lines,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        build_health_server_info_lines as build_health_server_info_lines,
    )
    from bioetl.interfaces.cli.commands.domains.health.rendering import (
        render_health_results_json as render_health_results_json,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.health.rendering")
