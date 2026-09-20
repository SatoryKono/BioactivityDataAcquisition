"""Lock AUD-010: compat shims carry sunset dates and stay unreferenced."""

from __future__ import annotations

from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "bioetl"

# Shim file -> acceptable first-party src files referencing its legacy alias.
SHIM_MARKERS = (
    "src/bioetl/application/ports/metrics.py",
    "src/bioetl/infrastructure/validation/pandera_validator.py",
    "src/bioetl/domain/_observability_contract_primitives.py",
    "src/bioetl/domain/value_objects/_run_context_create_support.py",
    "src/bioetl/infrastructure/system/memory_monitor.py",
)
PORTS_INIT = "src/bioetl/application/ports/__init__.py"
LEGACY_ALIASES = ("MetricsStartResult", "MetricsGatewayResult")
LEGACY_ALIAS_HOME = {
    "src/bioetl/application/ports/metrics.py",
    "src/bioetl/application/ports/__init__.py",
}


def _src_hits(pattern: str) -> dict[str, list[str]]:
    rx = re.compile(pattern)
    hits: dict[str, list[str]] = {}
    for path in sorted((ROOT / "src").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if rx.search(line)
        ]
        if lines:
            hits[rel] = lines
    return hits


@pytest.mark.architecture
def test_shims_declare_sunset_and_codemod() -> None:
    missing = []
    for rel in SHIM_MARKERS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        lowered = text.lower()
        if not ("sunset" in lowered and "2026-12-31" in text and "codemod" in lowered):
            missing.append(rel)
    assert missing == [], (
        "Every compat shim needs a sunset date and a codemod (AUD-010):\n"
        + "\n".join(missing)
    )


@pytest.mark.architecture
def test_ports_reexport_marks_deprecated_aliases() -> None:
    lines = (ROOT / PORTS_INIT).read_text(encoding="utf-8").splitlines()
    for alias in LEGACY_ALIASES:
        alias_lines = [line for line in lines if alias in line]
        assert alias_lines, f"{alias} missing from {PORTS_INIT}"
        unmarked = [
            line.strip() for line in alias_lines if "sunset 2026-12-31" not in line
        ]
        assert unmarked == [], (
            f"{alias} re-export lines need sunset markers (AUD-010):\n"
            + "\n".join(unmarked)
        )


@pytest.mark.architecture
def test_legacy_metric_aliases_stay_in_compat_surface() -> None:
    offenders: list[str] = []
    for alias in LEGACY_ALIASES:
        for rel in _src_hits(rf"\b{alias}\b"):
            if rel not in LEGACY_ALIAS_HOME:
                offenders.append(f"{rel}: {alias}")
    assert offenders == [], (
        "Legacy aliases must not leak outside the compat surface (AUD-010):\n"
        + "\n".join(sorted(offenders))
    )


@pytest.mark.architecture
def test_memory_stats_compat_reexport_has_no_src_importers() -> None:
    hits = _src_hits(
        r"from bioetl\.infrastructure\.system\.memory_monitor import "
        r".*MemoryStats"
    )
    assert hits == {}, (
        "First-party src must import MemoryStats from bioetl.domain.ports "
        f"(AUD-010): {sorted(hits)}"
    )


@pytest.mark.architecture
def test_top_level_pandera_schema_has_no_code_usage() -> None:
    hits = _src_hits(r"pandera\.DataFrameSchema")
    offenders = {
        rel: [line for line in lines if not line.startswith("#")]
        for rel, lines in hits.items()
    }
    offenders = {rel: lines for rel, lines in offenders.items() if lines}
    assert offenders == {}, (
        "Top-level pandera.DataFrameSchema must stay comment-only "
        f"(AUD-010): {sorted(offenders)}"
    )
