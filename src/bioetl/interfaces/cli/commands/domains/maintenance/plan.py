"""Internal wrapper for the public plan command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.plan import (
    get_contract_migration_service,
    plan_command,
)

__all__ = ["get_contract_migration_service", "plan_command"]
