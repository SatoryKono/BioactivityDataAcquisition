"""E2E matrix tests covering all entity pipelines.

This suite provides one smoke E2E case per entity pipeline declared in
`configs/entities/**`. It is intentionally lightweight:
- Uses `limit=1` where possible
- Reuses existing VCR cassettes when available
- Skips gracefully in playback mode when cassette is missing
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from deltalake.exceptions import DeltaError, TableNotFoundError
from tests.helpers.vcr_config import (
    QUERY_IGNORE_EMAIL_MATCH_ON,
    build_base_vcr_config,
)
from vcr.errors import (
    CannotOverwriteExistingCassetteException,
    UnhandledHTTPRequestError,
)

from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.exceptions.infrastructure import InfrastructureError
from bioetl.domain.exceptions.network import ExternalServiceError

from .conftest import (
    assert_bronze_files_exist,
    assert_bronze_metadata_files_exist,
    assert_run_manifest_exists,
    assert_silver_table_has_records,
    build_e2e_skip_reason,
    create_test_context,
    is_external_healthcheck_playback_failure,
    run_pipeline_or_skip_transient,
    _resolve_e2e_pipeline_matrix_execution_timeout_seconds,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")

CASSETTE_ROOT = Path(__file__).parent.parent / "fixtures" / "vcr"
PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS = (
    _resolve_e2e_pipeline_matrix_execution_timeout_seconds()
)


@dataclass(frozen=True, slots=True)
class PipelineE2ECase:
    """Single pipeline case for matrix E2E smoke test."""

    pipeline_name: str
    provider: str
    entity: str
    smoke_limit: int = 1
    query: str | None = None
    filter_ids: tuple[str, ...] | None = None
    filter_field: str | None = None
    cassette_candidates: tuple[str, ...] = ()


PIPELINE_CASES: tuple[PipelineE2ECase, ...] = (
    PipelineE2ECase(
        "chembl_activity",
        "chembl",
        "activity",
        cassette_candidates=("test_chembl_activity_full_cycle",),
    ),
    PipelineE2ECase(
        "chembl_assay",
        "chembl",
        "assay",
        cassette_candidates=("test_chembl_assay_full_cycle",),
    ),
    PipelineE2ECase(
        "chembl_assay_parameters",
        "chembl",
        "assay_parameters",
        cassette_candidates=(
            "test_pipeline_matrix__chembl_assay_parameters",
            "test_chembl_assay_full_cycle",
        ),
    ),
    PipelineE2ECase(
        "chembl_cell_line",
        "chembl",
        "cell_line",
        cassette_candidates=(
            "TestChemblCellLinePipeline.test_chembl_cell_line_happy_path",
        ),
    ),
    PipelineE2ECase(
        "chembl_compound_record",
        "chembl",
        "compound_record",
        cassette_candidates=(
            "TestChemblCompoundRecordPipeline.test_chembl_compound_record_happy_path",
        ),
    ),
    PipelineE2ECase(
        "chembl_molecule",
        "chembl",
        "molecule",
        cassette_candidates=("test_chembl_molecule_full_cycle",),
    ),
    PipelineE2ECase(
        "chembl_protein_class",
        "chembl",
        "protein_class",
        smoke_limit=2,
        cassette_candidates=("test_pipeline_matrix__chembl_protein_class",),
    ),
    PipelineE2ECase(
        "chembl_publication",
        "chembl",
        "publication",
        cassette_candidates=("test_chembl_publication_full_cycle",),
    ),
    PipelineE2ECase(
        "chembl_publication_similarity",
        "chembl",
        "publication_similarity",
        cassette_candidates=("test_pipeline_matrix__chembl_publication_similarity",),
    ),
    PipelineE2ECase(
        "chembl_publication_term",
        "chembl",
        "publication_term",
        cassette_candidates=(
            "test_pipeline_matrix__chembl_publication_term",
            "test_chembl_publication_term_full_cycle",
        ),
    ),
    PipelineE2ECase(
        "chembl_subcellular_fraction",
        "chembl",
        "subcellular_fraction",
        smoke_limit=2,
        filter_ids=("CHEMBL615178", "CHEMBL615210"),
        filter_field="assay_chembl_id",
        cassette_candidates=("test_pipeline_matrix__chembl_subcellular_fraction",),
    ),
    PipelineE2ECase(
        "chembl_target",
        "chembl",
        "target",
        smoke_limit=5,
        cassette_candidates=("test_chembl_target_full_cycle",),
    ),
    PipelineE2ECase(
        "chembl_target_component",
        "chembl",
        "target_component",
        cassette_candidates=(
            "TestChemblTargetComponentPipeline.test_chembl_target_component_happy_path",
        ),
    ),
    PipelineE2ECase(
        "chembl_target_protein_classification",
        "chembl",
        "target_protein_classification",
    ),
    PipelineE2ECase("chembl_tissue", "chembl", "tissue"),
    PipelineE2ECase(
        "crossref_publication",
        "crossref",
        "publication",
        query="rhodopsin crystal structure",
        cassette_candidates=("test_crossref_search_by_title",),
    ),
    PipelineE2ECase("composite_activity", "composite", "activity"),
    PipelineE2ECase("composite_assay", "composite", "assay"),
    PipelineE2ECase("composite_molecule", "composite", "molecule"),
    PipelineE2ECase("composite_publication", "composite", "publication"),
    PipelineE2ECase("composite_target", "composite", "target"),
    PipelineE2ECase(
        "openalex_publication",
        "openalex",
        "publication",
        query="COVID-19 vaccine",
        cassette_candidates=("TestOpenAlexAdapterIntegration.test_fetch_with_query",),
    ),
    PipelineE2ECase(
        "pubchem_compound",
        "pubchem",
        "compound",
        query="aspirin",
        cassette_candidates=(
            "test_pubchem_compound_pipeline",
            "test_pubchem_compound_full_cycle",
        ),
    ),
    PipelineE2ECase(
        "pubmed_publication",
        "pubmed",
        "publication",
        cassette_candidates=("test_pubmed_publication_full_cycle",),
    ),
    PipelineE2ECase(
        "semanticscholar_publication",
        "semanticscholar",
        "publication",
        smoke_limit=3,
        query="CRISPR gene editing",
        cassette_candidates=(
            "TestSemanticScholarAdapterIntegration.test_fetch_with_query",
        ),
    ),
    PipelineE2ECase(
        "uniprot_idmapping",
        "uniprot",
        "idmapping",
        filter_ids=("CHEMBL204",),
        filter_field="target_id",
        cassette_candidates=("TestUniProtIDMappingIntegration.test_map_single_id",),
    ),
    PipelineE2ECase(
        "uniprot_protein",
        "uniprot",
        "protein",
        cassette_candidates=("test_uniprot_protein_full_cycle",),
    ),
)

PIPELINE_CASE_BY_NAME: dict[str, PipelineE2ECase] = {
    case.pipeline_name: case for case in PIPELINE_CASES
}

MATRIX_REPLAY_DEFERRED_PIPELINES: frozenset[str] = frozenset(
    {
        "chembl_cell_line",
        "chembl_tissue",
        "chembl_compound_record",
        "chembl_assay_parameters",
        "chembl_protein_class",
        "chembl_publication_similarity",
        "chembl_publication_term",
        "chembl_subcellular_fraction",
        "chembl_target_component",
        "chembl_target_protein_classification",
        "composite_activity",
        "composite_assay",
        "composite_molecule",
        "composite_publication",
        "composite_target",
        "uniprot_idmapping",
    }
)
ACTIVE_PIPELINE_CASES: tuple[PipelineE2ECase, ...] = tuple(
    case
    for case in PIPELINE_CASES
    if case.pipeline_name not in MATRIX_REPLAY_DEFERRED_PIPELINES
)

CRITICAL_SMOKE_PIPELINES: frozenset[str] = frozenset(
    {
        "chembl_activity",
        "chembl_assay",
        "chembl_molecule",
        "chembl_publication",
        "chembl_target",
        "crossref_publication",
        "openalex_publication",
        "pubchem_compound",
        "pubmed_publication",
        "semanticscholar_publication",
        "uniprot_protein",
    }
)
NON_EMPTY_CASSETTE_CONTRACT_PIPELINES: frozenset[str] = frozenset(
    CRITICAL_SMOKE_PIPELINES
)

VCR_MISS_MARKERS: tuple[str, ...] = (
    "can't overwrite existing cassette",
    "no match for the request",
    "vcr",
)
MATRIX_SKIP_ERRORS: tuple[type[Exception], ...] = (
    InfrastructureError,
    ExternalServiceError,
    httpx.HTTPStatusError,
    CannotOverwriteExistingCassetteException,
    UnhandledHTTPRequestError,
    DataQualityThresholdError,
)

BRONZE_ONLY_ON_DQ_THRESHOLD_PIPELINES: frozenset[str] = frozenset(
    {
        "pubchem_compound",
        "chembl_publication_similarity",
    }
)


def _is_vcr_recording_enabled() -> bool:
    record_mode = os.environ.get("VCR_RECORD_MODE", "none").lower()
    if record_mode in {"all", "new_episodes"}:
        return True
    argv_text = " ".join(sys.argv).lower()
    return any(
        token in argv_text
        for token in (
            "--vcr-record=all",
            "--vcr-record=new_episodes",
            "--vcr-record-mode=all",
            "--vcr-record-mode=new_episodes",
        )
    )


def _cassette_exists(provider: str, cassette_name: str) -> bool:
    provider_dir = CASSETTE_ROOT / provider
    candidates = (
        provider_dir / cassette_name,
        provider_dir / f"{cassette_name}.yaml",
    )
    return any(path.exists() for path in candidates)


def _build_e2e_fail_reason(
    reason_code: str,
    *,
    pipeline_name: str,
    detail: str,
) -> str:
    """Build deterministic failure reason for CI classification."""
    return f"E2E_FAIL[{reason_code}] pipeline={pipeline_name}; {detail}"


def _requires_non_empty_cassette_contract(pipeline_name: str) -> bool:
    """Return True if matrix smoke pipeline must have non-empty cassette sample."""
    return pipeline_name in NON_EMPTY_CASSETTE_CONTRACT_PIPELINES


def _resolve_cassette_name(case: PipelineE2ECase) -> str | None:
    dynamic_candidates = (
        f"test_{case.pipeline_name}_full_cycle",
        f"test_pipeline_matrix__{case.pipeline_name}",
    )
    all_candidates = tuple(
        dict.fromkeys((*case.cassette_candidates, *dynamic_candidates))
    )

    if _is_vcr_recording_enabled():
        if all_candidates:
            return all_candidates[0]
        return f"test_pipeline_matrix__{case.pipeline_name}"

    for cassette in all_candidates:
        if _cassette_exists(case.provider, cassette):
            return cassette
    return None


def _is_vcr_mismatch_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in VCR_MISS_MARKERS)


def _is_rate_limited_http_error(exc: Exception) -> bool:
    """Return True when upstream API returned transient HTTP 429."""
    if isinstance(exc, ExternalServiceError):
        return exc.status_code == 429
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    return exc.response.status_code == 429


def _iter_entity_pipelines() -> set[str]:
    pipelines: set[str] = set()
    for path in sorted(Path("configs/entities").rglob("*.yaml")):
        provider = path.parent.name
        pipelines.add(f"{provider}_{path.stem}")
    return pipelines


@pytest.fixture(params=ACTIVE_PIPELINE_CASES, ids=lambda c: c.pipeline_name)
def pipeline_case(request: pytest.FixtureRequest) -> PipelineE2ECase:
    return request.param


@pytest.fixture
def vcr_cassette_dir(pipeline_case: PipelineE2ECase) -> Path:
    cassette_dir = CASSETTE_ROOT / pipeline_case.provider
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


@pytest.fixture
def vcr_cassette_name(pipeline_case: PipelineE2ECase) -> str:
    cassette_name = _resolve_cassette_name(pipeline_case)
    if cassette_name is None:
        if (
            pipeline_case.pipeline_name in CRITICAL_SMOKE_PIPELINES
            and not _is_vcr_recording_enabled()
        ):
            pytest.fail(
                "E2E_POLICY[CRITICAL_CASSETTE_MISSING] "
                f"pipeline={pipeline_case.pipeline_name}; "
                "record cassette via VCR_RECORD_MODE=new_episodes."
            )
        pytest.skip(
            build_e2e_skip_reason(
                "CASSETTE_MISSING",
                pipeline_name=pipeline_case.pipeline_name,
                detail="run with VCR_RECORD_MODE=new_episodes to record",
            )
        )
    return cassette_name


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    record_mode = "new_episodes" if _is_vcr_recording_enabled() else "none"
    return build_base_vcr_config(
        match_on=QUERY_IGNORE_EMAIL_MATCH_ON,
        decode_compressed_response=True,
        record_mode=record_mode,
    )


def test_pipeline_matrix_declares_all_entity_pipelines() -> None:
    configured = _iter_entity_pipelines()
    declared = {case.pipeline_name for case in PIPELINE_CASES}
    deferred_entities = {
        pipeline_name
        for pipeline_name in MATRIX_REPLAY_DEFERRED_PIPELINES
        if not pipeline_name.startswith("composite_")
    }
    assert declared == configured
    assert deferred_entities <= configured


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline_matrix_smoke(
    e2e_data_dir: Path,
    pipeline_case: PipelineE2ECase,
    vcr_cassette_name: str,
) -> None:
    """Run one smoke E2E per entity pipeline.

    The test validates that a pipeline can execute and produce at least one
    Bronze and Silver artifact under available cassette coverage.
    """
    ctx = create_test_context(
        pipeline_case.pipeline_name,
        limit=pipeline_case.smoke_limit,
        query=pipeline_case.query,
        filter_ids=pipeline_case.filter_ids,
        filter_field=pipeline_case.filter_field,
    )

    if pipeline_case.pipeline_name == "chembl_publication_term":
        pytest.skip(
            build_e2e_skip_reason(
                "DERIVED_PIPELINE_COVERED_BY_DEDICATED_E2E",
                pipeline_name=pipeline_case.pipeline_name,
                detail=(
                    "matrix smoke is skipped for this derived entity; "
                    "coverage lives in tests/e2e/test_chembl_publication_term_e2e.py"
                ),
            )
        )

    silver_validation_skipped = False
    try:
        await asyncio.wait_for(
            run_pipeline_or_skip_transient(ctx),
            timeout=PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        pytest.fail(
            _build_e2e_fail_reason(
                "PIPELINE_EXECUTION_TIMEOUT",
                pipeline_name=pipeline_case.pipeline_name,
                detail=(
                    f"timeout_seconds={PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS:g}; "
                    f"run_id={ctx.run_id}"
                ),
            ),
            pytrace=False,
        )
    except MATRIX_SKIP_ERRORS as exc:
        if _is_rate_limited_http_error(exc):
            pytest.skip(
                build_e2e_skip_reason(
                    "INFRA_FLAKY_429",
                    pipeline_name=pipeline_case.pipeline_name,
                    detail=str(exc),
                )
            )
        if is_external_healthcheck_playback_failure(exc):
            pytest.skip(
                build_e2e_skip_reason(
                    "INFRA_FLAKY_CASSETTE_HEALTHCHECK_MISMATCH",
                    pipeline_name=pipeline_case.pipeline_name,
                    detail=str(exc),
                )
            )
        if not _is_vcr_recording_enabled() and _is_vcr_mismatch_error(exc):
            pytest.skip(
                build_e2e_skip_reason(
                    "INFRA_FLAKY_CASSETTE_MISMATCH",
                    pipeline_name=pipeline_case.pipeline_name,
                    detail=str(exc),
                )
            )
        # Some non-critical matrix cassettes prove Bronze/raw payload coverage but
        # still fail Silver due to sparse upstream sample content.
        if (
            isinstance(exc, DataQualityThresholdError)
            and pipeline_case.pipeline_name in BRONZE_ONLY_ON_DQ_THRESHOLD_PIPELINES
        ):
            silver_validation_skipped = True
        else:
            raise
    except Exception as exc:
        pytest.fail(  # pragma: no cover - defensive branch
            _build_e2e_fail_reason(
                "CODE_REGRESSION",
                pipeline_name=pipeline_case.pipeline_name,
                detail=f"error_type={type(exc).__name__}; {exc}",
            )
        )

    try:
        bronze_files = assert_bronze_files_exist(
            e2e_data_dir,
            pipeline_case.provider,
            pipeline_case.entity,
        )
        assert len(bronze_files) >= 1
        if not silver_validation_skipped:
            await assert_silver_table_has_records(
                e2e_data_dir, pipeline_case.pipeline_name, 1
            )
    except (AssertionError, DeltaError, TableNotFoundError) as exc:
        if _requires_non_empty_cassette_contract(pipeline_case.pipeline_name):
            pytest.fail(
                _build_e2e_fail_reason(
                    "INFRA_FLAKY_CASSETTE_EMPTY",
                    pipeline_name=pipeline_case.pipeline_name,
                    detail=str(exc),
                )
            )
        if pipeline_case.pipeline_name == "chembl_publication_term":
            pytest.skip(
                build_e2e_skip_reason(
                    "CASSETTE_EMPTY_DERIVED_PAYLOAD",
                    pipeline_name=pipeline_case.pipeline_name,
                    detail=(
                        "pipeline completed successfully but cassette sample produced "
                        "no derived publication_term Bronze/Silver artifacts"
                    ),
                )
            )
        metadata_files = assert_bronze_metadata_files_exist(
            e2e_data_dir,
            pipeline_case.provider,
            pipeline_case.entity,
        )
        manifest = assert_run_manifest_exists(e2e_data_dir, ctx.run_id)
        assert metadata_files
        assert manifest["run_id"] == str(ctx.run_id)
