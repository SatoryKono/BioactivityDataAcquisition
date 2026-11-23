"""The typed public facade must expose its runtime exports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]


def test_public_facade_strict_consumer(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "from bioetl.domain.ports import (\n"
        "    EntityTypeExtractor, GoldFilterCallback, GoldTransformCallback,\n"
        "    TransformCallback, PaginationConfigLike, SourceConfigLike,\n"
        "    ForeignKeyReconciliationAction,\n"
        ")\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--no-incremental",
            "--follow-imports=silent",
            "--cache-dir",
            str(tmp_path / "cache"),
            str(consumer),
        ],
        cwd=ROOT,
        env={**os.environ, "MYPYPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
