"""
Core pipeline orchestration and models.
Deprecated: Use bioetl.application.pipelines, bioetl.domain.models, etc.
"""
from bioetl.domain.enums import ErrorAction
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.models import RunContext, RunResult
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.stages import StageABC, StageResult
from bioetl.core.container import PipelineContainer, build_pipeline_dependencies
from bioetl.core.custom_types import (
    CUSTOM_FIELD_NORMALIZERS,
    normalize_array,
    normalize_chembl_id,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)

__all__ = [
    "ErrorAction",
    "ErrorPolicyABC",
    "PipelineHookABC",
    "PipelineBase",
    "RunContext",
    "RunResult",
    "StageABC",
    "StageResult",
    "PipelineContainer",
    "build_pipeline_dependencies",
    "CUSTOM_FIELD_NORMALIZERS",
    "normalize_array",
    "normalize_chembl_id",
    "normalize_doi",
    "normalize_pcid",
    "normalize_pmid",
    "normalize_record",
    "normalize_uniprot",
]
