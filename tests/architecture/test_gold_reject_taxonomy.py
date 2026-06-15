"""Architecture guardrails for Gold reject taxonomy ownership."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SILVER_SURFACES = (
    ROOT / "src/bioetl/application/services/dq/silver_analyzer.py",
    ROOT / "src/bioetl/application/services/dq/silver_check_executor.py",
    ROOT / "src/bioetl/application/services/dq/silver_statistics.py",
    ROOT / "src/bioetl/application/services/dq/silver_statistics_helpers.py",
    ROOT / "src/bioetl/infrastructure/storage/silver",
    ROOT / "src/bioetl/infrastructure/storage/silver_writer.py",
)
FORBIDDEN_SILVER_MARKERS = (
    "gold_candidate_",
    "analysis_readiness",
    "analysis-readiness",
)


def _iter_python_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(sorted(path.rglob("*.py")))


def test_silver_surfaces_do_not_emit_gold_candidate_or_readiness_flags() -> None:
    offenders: list[str] = []
    for surface in SILVER_SURFACES:
        for path in _iter_python_files(surface):
            text = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_SILVER_MARKERS:
                if marker in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{marker}")

    assert offenders == []
