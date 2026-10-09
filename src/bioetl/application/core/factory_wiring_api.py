"""Legacy flat facade for composition-owned pipeline factory wiring."""

from __future__ import annotations

from bioetl.application.core.wiring import factory as _factory
from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade,
)

_LEGACY_FACTORY_EXPORTS = {name: (_factory.__name__, name) for name in _factory.__all__}
install_lazy_export_facade(globals(), __name__, _LEGACY_FACTORY_EXPORTS)
