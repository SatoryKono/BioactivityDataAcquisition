"""Tests for pipeline registration modules (import + class verification).

Covers 17 pipeline modules that are simple BasePipeline subclasses
with transformer injection via DI.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from bioetl.application.core.base import BasePipeline

# (module_path, class_name)
# ChEMBL pipelines consolidated in _pipelines.py per audit-package-structure-2026-02-07
_PIPELINE_MODULES: list[tuple[str, str]] = [
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLActivityPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLAssayPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLAssayParametersPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLCellLinePipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLCompoundRecordPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLMoleculePipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLProteinClassPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLPublicationPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLPublicationSimilarityPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLPublicationTermPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLSubcellularFractionPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLTargetPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLTargetComponentPipeline"),
    ("bioetl.application.pipelines.chembl._pipelines", "ChEMBLTissuePipeline"),
    ("bioetl.application.pipelines.pubchem.compound", "PubChemCompoundPipeline"),
    ("bioetl.application.pipelines.pubmed.publication", "PubMedPublicationPipeline"),
    ("bioetl.application.pipelines.uniprot.protein", "UniProtProteinPipeline"),
]


@pytest.mark.unit
class TestPipelineRegistrations:
    """Verify all pipeline registration modules can be imported and are valid subclasses."""

    @pytest.mark.parametrize(
        ("module_path", "class_name"),
        _PIPELINE_MODULES,
        ids=[cls for _, cls in _PIPELINE_MODULES],
    )
    def test_pipeline_module_importable(
        self, module_path: str, class_name: str
    ) -> None:
        """Each pipeline module must be importable."""
        mod = importlib.import_module(module_path)
        cls: Any = getattr(mod, class_name)
        assert issubclass(cls, BasePipeline)

    @pytest.mark.parametrize(
        ("module_path", "class_name"),
        _PIPELINE_MODULES,
        ids=[cls for _, cls in _PIPELINE_MODULES],
    )
    def test_pipeline_class_is_concrete(
        self, module_path: str, class_name: str
    ) -> None:
        """Each pipeline class must not define its own __init__ (relies on BasePipeline.create)."""
        mod = importlib.import_module(module_path)
        cls: Any = getattr(mod, class_name)
        assert "__init__" not in cls.__dict__, (
            f"{class_name} should not define __init__; it inherits from BasePipeline"
        )
