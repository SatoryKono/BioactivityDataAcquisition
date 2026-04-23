"""Support helpers for quarantine execution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        QuarantineExecutionPolicy as QuarantineExecutionPolicy,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        run_quarantine_async as run_quarantine_async,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
        run_quarantine_sync as run_quarantine_sync,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.execution")
