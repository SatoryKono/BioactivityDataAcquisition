"""Lock AUD-008 for memory sidecar: sync_pkg has no star imports."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
INIT = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "__init__.py"


def test_sync_pkg_init_has_no_star_imports() -> None:
    offenders = [
        f"{lineno}:{line.strip()}"
        for lineno, line in enumerate(
            INIT.read_text(encoding="utf-8").splitlines(), start=1
        )
        if re.search(r"^\s*from\s+\S+\s+import\s+\*", line) or "noqa: F403" in line
    ]
    assert offenders == []


def test_sync_pkg_all_composes_core_and_cli() -> None:
    import memory.graph.sync_pkg as pkg
    from memory.graph.sync_pkg import _core as core_mod
    from memory.graph.sync_pkg import cli as cli_mod

    expected = [*core_mod.__all__]
    for name in cli_mod.__all__:
        if name not in expected:
            expected.append(name)
    assert list(pkg.__all__) == expected


def test_sync_pkg_lazy_exports_resolve_and_reject_unknown() -> None:
    import memory.graph.sync_pkg as pkg
    from memory.graph.sync_pkg import _core as core_mod

    assert getattr(pkg, core_mod.__all__[0]) is getattr(core_mod, core_mod.__all__[0])
    assert pkg.CLI_FLAG_DEFINITIONS is not None
    with pytest.raises(AttributeError):
        pkg.definitely_not_an_export_zzz
