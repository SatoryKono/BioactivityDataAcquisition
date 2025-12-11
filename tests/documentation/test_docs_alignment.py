from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_docs_alignment import run_checks


def test_docs_alignment_ok() -> None:
    result = run_checks()
    assert result.is_ok(), result.format_errors()
