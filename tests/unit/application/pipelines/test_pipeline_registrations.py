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
# ChEMBL marker classes are canonically owned by pipeline_types.py.
_PIPELINE_MODULES: list[tuple[str, str]] = [
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLActivityPipeline"),
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLAssayPipeline"),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLAssayParametersPipeline",
    ),
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLCellLinePipeline"),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLCompoundRecordPipeline",
    ),
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLMoleculePipeline"),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLProteinClassPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLPublicationPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLPublicationSimilarityPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLPublicationTermPipeline",
    ),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLSubcellularFractionPipeline",
    ),
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLTargetPipeline"),
    (
        "bioetl.application.pipelines.chembl.pipeline_types",
        "ChEMBLTargetComponentPipeline",
    ),
    ("bioetl.application.pipelines.chembl.pipeline_types", "ChEMBLTissuePipeline"),
    ("bioetl.application.pipelines.pubchem", "PubChemCompoundPipeline"),
    ("bioetl.application.pipelines.pubmed", "PubMedPublicationPipeline"),
    ("bioetl.application.pipelines.uniprot", "UniProtProteinPipeline"),
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

    @pytest.mark.parametrize(
        "class_name",
        [
            "ChEMBLActivityPipeline",
            "ChEMBLAssayPipeline",
            "ChEMBLAssayParametersPipeline",
            "ChEMBLCellLinePipeline",
            "ChEMBLCompoundRecordPipeline",
            "ChEMBLMoleculePipeline",
            "ChEMBLProteinClassPipeline",
            "ChEMBLPublicationPipeline",
            "ChEMBLPublicationSimilarityPipeline",
            "ChEMBLPublicationTermPipeline",
            "ChEMBLSubcellularFractionPipeline",
            "ChEMBLTargetPipeline",
            "ChEMBLTargetComponentPipeline",
            "ChEMBLTissuePipeline",
        ],
    )
    def test_chembl_pipeline_types_module_exports_marker_classes(
        self, class_name: str
    ) -> None:
        """Canonical pipeline_types exports should expose ChEMBL marker classes."""
        canonical_module = importlib.import_module(
            "bioetl.application.pipelines.chembl.pipeline_types"
        )

        assert getattr(canonical_module, class_name)
