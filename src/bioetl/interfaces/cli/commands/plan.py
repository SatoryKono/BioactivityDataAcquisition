"""Retained public plan command seam over the canonical maintenance module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.maintenance.plan import (
        get_contract_migration_service as get_contract_migration_service,
    )
    from bioetl.interfaces.cli.commands.domains.maintenance.plan import (
        plan_command as plan_command,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.maintenance.plan")
