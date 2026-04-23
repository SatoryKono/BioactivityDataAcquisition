"""Public cleanup command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        bronze_cleanup_command as bronze_cleanup_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        cleanup_preview_command as cleanup_preview_command,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        get_bronze_cleanup_service as get_bronze_cleanup_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
        preview_pipeline_cleanup as preview_pipeline_cleanup,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.cleanup")
