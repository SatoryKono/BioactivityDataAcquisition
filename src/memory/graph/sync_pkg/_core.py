#!/usr/bin/env python3
"""Build and optionally sync the canonical deterministic BioETL graph into Neo4j."""

from __future__ import annotations

import shutil as shutil  # re-exported via __all__
import sys

from memory.graph.sync_pkg import _core_reexport_a as _core_reexport_a
from memory.graph.sync_pkg import _core_reexport_b as _core_reexport_b
from memory.graph.sync_pkg import _core_reexport_c as _core_reexport_c
from memory.graph.sync_pkg import _core_reexport_d as _core_reexport_d


def _install_reexport_shards() -> None:
    g = globals()
    for mod in (
        _core_reexport_a,
        _core_reexport_b,
        _core_reexport_c,
        _core_reexport_d,
    ):
        for name in mod.__all__:
            g[name] = getattr(mod, name)


_install_reexport_shards()

__all__ = [
    name
    for name in globals()
    if not name.startswith("__")
    and name != "_install_reexport_shards"
    and not name.startswith("_core_reexport_")
]

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
