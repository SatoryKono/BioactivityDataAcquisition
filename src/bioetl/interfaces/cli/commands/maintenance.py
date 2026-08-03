"""Public maintenance command seam for BioETL CLI.

Canonical implementation lives in
``bioetl.interfaces.cli.commands.domains.maintenance.command_group``.
This module is a sanctioned external/public re-export surface only.
First-party runtime code should import the domain package owner instead.
"""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.maintenance.command_group import (
    maintenance,
)

__all__ = ["maintenance"]
