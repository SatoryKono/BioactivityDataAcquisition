"""Composition-facing seams for application-core assembly.

This package groups the stable wiring APIs used by ``composition/`` so the
top-level ``application.core`` family keeps fewer mixed-purpose modules.
Legacy flat facades (``*_wiring_api.py``) remain for compatibility.
"""

from __future__ import annotations

from bioetl.application.core.wiring.factory import *  # noqa: F403
from bioetl.application.core.wiring.registry import *  # noqa: F403
from bioetl.application.core.wiring.runtime import *  # noqa: F403
from bioetl.application.core.wiring.transformer import *  # noqa: F403
from bioetl.application.core.wiring.factory import __all__ as _FACTORY_ALL
from bioetl.application.core.wiring.registry import __all__ as _REGISTRY_ALL
from bioetl.application.core.wiring.runtime import __all__ as _RUNTIME_ALL
from bioetl.application.core.wiring.transformer import __all__ as _TRANSFORMER_ALL

__all__ = [*_FACTORY_ALL, *_RUNTIME_ALL, *_TRANSFORMER_ALL, *_REGISTRY_ALL]
