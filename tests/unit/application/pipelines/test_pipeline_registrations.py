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
_PIPELINE_MODULES: list[tuple[str, str]] = [
    ("bioetl.application.pipelines.chembl.activity", "ChEMBLActivityPipeline"),
    ("bioetl.application.pipelines.chembl.assay", "ChEMBLAssayPipeline"),
    (
        "bioetl.application.pipelines.chembl.assay_parameters",
        "ChEMBLAssayParametersPipeline",
    ),
    ("bioetl.application.pipelines.chembl.cell_line", "ChEMBLCellLinePipeline"),
    (
        "bioetl.application.pipelines.chembl.compound_record",
        "ChEMBLCompoundRecordPipeline",
    ),
    ("bioetl.application.pipelines.chembl.molecule", "ChEMBLMoleculePipeline"),
    ("bioetl.application.pipelines.chembl.protein_class", "ChEMBLProteinClassPipeline"),
    ("bioetl.application.pipelines.chembl.publication", "ChEMBLPublicationPipeline"),
    (
        "bioetl.application.pipelines.chembl.publication_similarity",
        "ChEMBLPublicationSimilarityPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.publication_term",
        "ChEMBLPublicationTermPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.subcellular_fraction",
        "ChEMBLSubcellularFractionPipeline",
    ),
    ("bioetl.application.pipelines.chembl.target", "ChEMBLTargetPipeline"),
    (
        "bioetl.application.pipelines.chembl.target_component",
        "ChEMBLTargetComponentPipeline",
    ),
    ("bioetl.application.pipelines.chembl.tissue", "ChEMBLTissuePipeline"),
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
