"""Lock AUD-008: application facades use explicit re-exports, no star imports."""

from __future__ import annotations

import importlib
from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src" / "bioetl"

STAR_RE = re.compile(r"^\s*from\s+\S+\s+import\s+\*")

FACADE_FILES = (
    SRC / "application" / "core" / "factory_wiring_api.py",
    SRC / "application" / "core" / "field_transforms" / "__init__.py",
    SRC / "application" / "core" / "preflight" / "__init__.py",
    SRC / "application" / "core" / "transformer_runtime" / "__init__.py",
    SRC / "application" / "core" / "transformer_runtime" / "finalization.py",
    SRC / "application" / "core" / "transformer_runtime" / "state.py",
    SRC / "application" / "pipelines" / "openalex" / "extractors.py",
)

# Facade module -> source modules whose __all__ it must re-export exactly.
FACADE_SOURCES = {
    "bioetl.application.core.factory_wiring_api": (
        "bioetl.application.core.wiring.factory",
    ),
    "bioetl.application.core.field_transforms": (
        "bioetl.application.core.dict_transformers",
        "bioetl.application.core.entity_id",
        "bioetl.application.core.field_specs",
    ),
    "bioetl.application.core.preflight": ("bioetl.application.core.preflight.service",),
    "bioetl.application.core.transformer_runtime": (
        "bioetl.application.core.transformer_runtime.finalization",
        "bioetl.application.core.transformer_runtime.orchestration",
        "bioetl.application.core.transformer_runtime.state",
    ),
    "bioetl.application.core.transformer_runtime.finalization": (
        "bioetl.application.core.batch_transformer_dq_thresholds",
        "bioetl.application.core.batch_transformer_finalization",
    ),
    "bioetl.application.core.transformer_runtime.state": (
        "bioetl.application.core.batch_transformer_state",
    ),
    "bioetl.application.pipelines.openalex.extractors": (
        "bioetl.application.pipelines.openalex._extractors_authors",
        "bioetl.application.pipelines.openalex._extractors_publication_fields",
        "bioetl.application.pipelines.openalex._extractors_topics_grants",
    ),
}


def test_facade_files_have_no_star_imports() -> None:
    offenders = []
    for path in FACADE_FILES:
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if STAR_RE.search(line) or "noqa: F403" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert offenders == []


# Facades that additionally re-export an explicit subset of owner modules
# without a full __all__ (locked literally so drift fails loudly).
FACADE_EXTRAS = {
    "bioetl.application.core.transformer_runtime": frozenset(
        {
            "TRANSFORM_PROCESSING_ERRORS",
            "bind_record_context",
            "transform_record_attempt",
            "QUARANTINE_WRITE_WARN_ONLY_ERRORS",
            "flush_dq_records",
            "flush_filtered_records",
            "route_single_transform_attempt",
            "StreamingBatchProcessor",
        }
    ),
}


@pytest.mark.parametrize("facade", sorted(FACADE_SOURCES))
def test_facade_reexports_source_all_exactly(facade: str) -> None:
    module = importlib.import_module(facade)
    expected: set[str] = set()
    for source in FACADE_SOURCES[facade]:
        expected.update(importlib.import_module(source).__all__)
    expected.update(FACADE_EXTRAS.get(facade, frozenset()))
    assert set(module.__all__) == expected


def test_factory_wiring_facade_resolves_lazily() -> None:
    from bioetl.application.core import factory_wiring_api
    from bioetl.application.core.wiring import factory

    assert factory_wiring_api.PipelineRunner is factory.PipelineRunner
    assert set(factory_wiring_api.__all__) == set(factory.__all__)
