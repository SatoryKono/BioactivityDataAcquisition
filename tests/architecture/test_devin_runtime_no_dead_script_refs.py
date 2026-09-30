"""Devin runtime must not reference the retired config-bot script (#11784).

The archived `scripts/agents/py-config-bot-1.py` no longer exists; the
canonical config gate is `python -m scripts.schema validate-configs`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEVIN_ROOT = ROOT / ".devin"
RETIRED_REF = "scripts/agents/py-config-bot-1.py"

pytestmark = pytest.mark.architecture


def test_devin_runtime_has_no_dead_config_bot_refs() -> None:
    offenders = sorted(
        str(path.relative_to(ROOT).as_posix())
        for path in DEVIN_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".toml", ".yaml", ".yml", ".json"}
        and RETIRED_REF in path.read_text(encoding="utf-8", errors="replace")
    )
    assert not offenders, (
        "Retired script reference in Devin runtime; use "
        "`python -m scripts.schema validate-configs`:\n" + "\n".join(offenders)
    )
