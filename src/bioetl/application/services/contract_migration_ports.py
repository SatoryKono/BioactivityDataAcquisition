"""Compatibility re-export — implementation lives in `bioetl.application.services.contract.contract_migration_ports`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.contract.contract_migration_ports import *  # noqa: F403
from bioetl.application.services.contract.contract_migration_ports import __all__ as __all__
