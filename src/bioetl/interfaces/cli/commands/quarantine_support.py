"""Support helpers for quarantine helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _inspect_quarantine as _inspect_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _purge_quarantine as _purge_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _replay_quarantine as _replay_quarantine,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _resolve_quarantine_record as _resolve_quarantine_record,
    )
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _show_quarantine_stats as _show_quarantine_stats,
    )

alias_module(__name__, "bioetl.interfaces.cli.commands.domains.quarantine.support")
