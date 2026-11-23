"""Execute source-bound offline reference acceptance without rewriting history.

PASS qualifies only the supplied reviewed cases and integration occurrence. It
never asserts broad biological accuracy or upgrades the historical TC reports.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import NotRequired, TypedDict, cast

from .bioetl_input import target_input_eligibility
from .models import ClassificationResult, RawTargetRow, RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, classify_batch
from .pipeline_acceptance import (
    AdmittedCohort,
    SourceImport,
    VolumePlan,
    load_admitted_cohort,
)
from .pipeline_io import render_batch
from .pipeline_proof import (
    PipelineExecutionBinding,
    execution_semantics,
    verify_stored_pipeline_proof,
)
from .policy import VOLUME_TEST_SECONDS
from .reference_coverage import (
    SUPPORTED_REFERENCE_FIELDS,
    validate_executed_reference_coverage,
    validate_reference_coverage_receipt,
    validate_reference_specification,
)
from .stage0.io import canonical_json_bytes, sha256_bytes, sha256_file

CHECKS = (
    "stage0_admission",
    "reference_cases",
    "evidence_integrity",
    "semantic_determinism",
    "pipeline_integration",
)
_EXPECTED_FIELDS = frozenset(
    {
        "match_status",
        "matched_target_id",
        "iuphar_class",
        "local_class",
        "effective_class",
        "effective_source",
        "decision_status",
        "iuphar_annotation_status",
    }
)


class _SourceReference(TypedDict):
    path: str
    sha256: str


class _ReferenceCase(TypedDict):
    input_row_id: str
    source_references: list[_SourceReference]
    expected: dict[str, object]


class _SourceImportSpec(TypedDict):
    source_path: str
    format_version: str
    target_kind: str


class _ReferenceSpecification(TypedDict):
    """Shape of the pinned reference document at the JSON boundary."""

    artifact: str
    schema_version: int
    reviewer_reference: str
    approval_reference: str
    environment: str
    snapshot_manifest_sha256: str
    stage0_manifest_sha256: str
    selected_source_paths: list[str]
    expected_rows: int
    source_imports: NotRequired[list[_SourceImportSpec]]
    cases: list[_ReferenceCase]
    cohort_manifest_sha256: NotRequired[str]
    conversion_ledger_sha256: NotRequired[str]
    scope_declaration: NotRequired[dict[str, object]]
    reference_matrix: NotRequired[dict[str, object]]
    normalization_version: NotRequired[str]
    rules_version: NotRequired[str]
    classification_schema_version: NotRequired[str]
    taxonomy_scope: NotRequired[list[str]]


@dataclass(frozen=True, slots=True)
class IntegrationAcceptanceRequest:
    """Explicit pinned inputs; no current/latest fallback is permitted."""

    stage0_manifest: Path
    expected_labels: Path
    expected_labels_sha256: str
    snapshot_manifest_sha256: str
    provenance: RunProvenance
    run_id: str
    pipeline_proof: Path | None = None
    pipeline_report: Path | None = None
    species_taxon_ids: frozenset[str] | None = None


def _verified_labels(request: IntegrationAcceptanceRequest) -> _ReferenceSpecification:
    raw = request.expected_labels.read_bytes()
    if sha256_bytes(raw) != request.expected_labels_sha256:
        raise ValueError("expected-label digest mismatch")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("reference specification must be a JSON object")
    spec = cast("_ReferenceSpecification", loaded)
    if (
        spec.get("artifact") != "bioetl_iuphar_reference_cases"
        or spec.get("schema_version") not in {1, 2}
        or not spec.get("reviewer_reference")
        or not spec.get("approval_reference")
        or not spec.get("environment")
    ):
        raise ValueError("missing reviewed, versioned reference-case specification")
    if spec.get("snapshot_manifest_sha256") != request.snapshot_manifest_sha256:
        raise ValueError("reference cases belong to another snapshot")
    return spec


def _volume_plan(spec: _ReferenceSpecification) -> VolumePlan:
    return VolumePlan(
        manifest_sha256=spec["stage0_manifest_sha256"],
        selected_source_paths=tuple(spec["selected_source_paths"]),
        expected_rows=spec["expected_rows"],
        approval_reference=spec["approval_reference"],
        environment=spec["environment"],
        source_imports=tuple(
            SourceImport(**item) for item in spec.get("source_imports", [])
        ),
    )


def _check_cases(batch: BatchResult, spec: _ReferenceSpecification, root: Path) -> None:
    results = {row.result.input_row_id: row.result for row in batch.rows}
    cases = spec.get("cases", [])
    identities = [case["input_row_id"] for case in cases]
    if not cases or len(set(identities)) != len(identities):
        raise ValueError("reference cases must have distinct row identities")
    for case in cases:
        allowed = (
            SUPPORTED_REFERENCE_FIELDS
            if spec["schema_version"] == 2
            else _EXPECTED_FIELDS
        )
        _check_reference_case(case, results.get(case["input_row_id"]), root, allowed)


def _check_reference_sources(references: list[_SourceReference], root: Path) -> None:
    """Bind reviewed source files to the reference specification directory."""
    for reference in references:
        path = (root / reference["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("reference source escapes its specification root")
        if sha256_file(path) != reference["sha256"]:
            raise ValueError("reference source digest mismatch")


def _check_reference_case(
    case: _ReferenceCase,
    actual: ClassificationResult | None,
    root: Path,
    allowed_fields: frozenset[str] = _EXPECTED_FIELDS,
) -> None:
    """Compare one source-backed expectation with the executed row result."""
    references = case.get("source_references", [])
    expected = case.get("expected", {})
    if not references or not expected or not set(expected).issubset(allowed_fields):
        raise ValueError("each reference case needs reviewed source proof and outcomes")
    _check_reference_sources(references, root)
    if actual is None:
        raise ValueError("reference case is outside the admitted cohort")
    for field, value in expected.items():
        if canonical_json_bytes(getattr(actual, field)) != canonical_json_bytes(value):
            raise AssertionError(
                f"reference mismatch: {case['input_row_id']} / {field}"
            )


def _check_evidence(batch: BatchResult) -> None:
    for row in batch.rows:
        ids = {item.evidence_id for item in row.evidence.records}
        wanted = {*row.result.match_evidence_ids, *row.result.local_evidence_ids}
        if not wanted.issubset(ids):
            raise AssertionError("classification has dangling evidence references")
        if row.result.iuphar_class and not row.annotation:
            raise AssertionError("direct class has no frozen provider annotation")
        if any(
            item.input_row_id != row.result.input_row_id
            for item in row.evidence.records
        ):
            raise AssertionError("evidence belongs to another input row")


def verify_pipeline_proof(
    path: Path,
    snapshot_sha256: str,
    pipeline_report: Path | None = None,
    *,
    provenance: RunProvenance | None = None,
    expected_row_ids: tuple[str, ...] | None = None,
    expected_execution: tuple[PipelineExecutionBinding, ...] | None = None,
) -> str:
    """Require a verified row-store occurrence and its source-bound run report."""
    if provenance is None:
        raise ValueError("pipeline proof requires expected executed version identities")
    return verify_stored_pipeline_proof(
        path,
        snapshot_sha256,
        pipeline_report,
        provenance,
        expected_row_ids=expected_row_ids,
        expected_execution=expected_execution,
    )


def run_integration_acceptance(
    request: IntegrationAcceptanceRequest,
    *,
    snapshot: IndexedSnapshot,
    output_dir: Path,
    clock: Callable[[], float] = perf_counter,
) -> Mapping[str, object]:
    """Run full frozen cohort, compare reviewed cases and preserve a new receipt."""
    resolved_output = output_dir.expanduser().resolve(strict=False)
    output_root = resolved_output.parent
    relative_output = resolved_output.relative_to(output_root)
    if output_root == resolved_output or any(
        part in {"..", "."} for part in relative_output.parts
    ):
        raise ValueError("acceptance output escapes its parent directory")
    output_dir = output_root.joinpath(*relative_output.parts)
    output_dir.mkdir(parents=True, exist_ok=False)
    checks = dict.fromkeys(CHECKS, "NOT_RUN")
    receipt: dict[str, object] = {
        "artifact": "bioetl_iuphar_acceptance",
        "schema_version": 1,
        "scope": "offline_target_integration",
        "status": "BLOCKED_INPUT",
        "run_id": request.run_id,
        "checks": checks,
        "snapshot_manifest_sha256": request.snapshot_manifest_sha256,
        "expected_labels_sha256": request.expected_labels_sha256,
        "reference_cases_accepted": False,
        "biological_accuracy_accepted": False,
        "normalization_version": request.provenance.normalization_version,
        "rules_version": request.provenance.rules_version,
        "classification_schema_version": request.provenance.schema_version,
    }
    try:
        _execute_acceptance(request, snapshot, output_dir, clock, receipt, checks)
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt["reason"] = str(error)
    except AssertionError as error:
        receipt.update(status="FAIL", reason=str(error))
    (output_dir / "acceptance.json").write_bytes(canonical_json_bytes(receipt))
    return receipt


def _execute_acceptance(
    request: IntegrationAcceptanceRequest,
    snapshot: IndexedSnapshot,
    output_dir: Path,
    clock: Callable[[], float],
    receipt: dict[str, object],
    checks: dict[str, str],
) -> None:
    spec = _verified_labels(request)
    cohort = _admit_acceptance_cohort(request, snapshot, spec)
    if spec["schema_version"] == 2:
        _prepare_reference_scope(request, cohort, spec, receipt)
    checks["stage0_admission"] = "PASS"
    receipt.update(
        stage0_manifest_sha256=cohort.manifest_sha256,
        reviewer_reference=spec["reviewer_reference"],
    )
    _write_execution_config(request, cohort, output_dir)
    batch, elapsed = _execute_cohort(request, snapshot, cohort.rows, clock)
    rendered = _verify_batch_outputs(
        request, snapshot, cohort.rows, batch, spec, checks
    )
    receipt.update(
        output_sha256={name: sha256_bytes(raw) for name, raw in rendered.items()},
        elapsed_seconds=elapsed,
        rows=len(cohort.rows),
        reference_cases_accepted=True,
    )
    for name, raw in rendered.items():
        (output_dir / name).write_bytes(raw)
    _record_pipeline_acceptance(request, receipt, cohort, batch)
    if spec["schema_version"] == 2:
        receipt["artifact_references"] = _publication_references(
            request, cohort, output_dir, rendered
        )
        validate_reference_coverage_receipt(receipt)
    checks["pipeline_integration"] = "PASS"
    receipt["status"] = "PASS"


def _require_canonical_imports(spec: _ReferenceSpecification) -> None:
    """Allow only the explicit TaxID-preserving integration input profile."""
    imports = spec.get("source_imports", [])
    if {item["source_path"] for item in imports} != set(
        spec["selected_source_paths"]
    ) or any(
        item["format_version"] != "bioetl_target_kernel_csv_v1"
        or item["target_kind"] != "protein"
        for item in imports
    ):
        raise ValueError(
            "integration acceptance requires explicit canonical TaxID input profiles"
        )


def _admit_acceptance_cohort(
    request: IntegrationAcceptanceRequest,
    snapshot: IndexedSnapshot,
    spec: _ReferenceSpecification,
) -> AdmittedCohort:
    """Bind complete Stage-0 rows and execution provenance to this snapshot."""
    _require_canonical_imports(spec)
    if request.provenance.snapshot_id != snapshot.snapshot_id:
        raise ValueError("execution provenance belongs to another snapshot")
    admitted = (
        snapshot.admission_complete
        if snapshot.admission_complete is not None
        else snapshot.complete
    )
    if not admitted:
        raise ValueError("complete admitted snapshot required")
    cohort = load_admitted_cohort(request.stage0_manifest, _volume_plan(spec))
    if not cohort.rows or len(cohort.rows) != spec["expected_rows"]:
        raise ValueError("full admitted cohort count differs from the frozen plan")
    return cohort


def _prepare_reference_scope(
    request: IntegrationAcceptanceRequest,
    cohort: AdmittedCohort,
    spec: _ReferenceSpecification,
    receipt: dict[str, object],
) -> None:
    if request.pipeline_report is None or request.pipeline_proof is None:
        raise ValueError(
            "V2 reference acceptance requires explicit pipeline proof and report paths"
        )
    receipt.update(
        validate_reference_specification(
            spec,
            cohort=cohort,
            provenance=request.provenance,
            root=request.expected_labels.parent,
        )
    )


def _write_execution_config(
    request: IntegrationAcceptanceRequest, cohort: AdmittedCohort, output_dir: Path
) -> None:
    """Preserve the exact run inputs before executing classification."""
    config = {
        "snapshot_manifest_sha256": request.snapshot_manifest_sha256,
        "expected_labels_sha256": request.expected_labels_sha256,
        "stage0_manifest_sha256": cohort.manifest_sha256,
        "run_id": request.run_id,
        "expected_rows": len(cohort.rows),
        "species_taxon_ids": (
            sorted(request.species_taxon_ids)
            if request.species_taxon_ids is not None
            else None
        ),
    }
    (output_dir / "execution-config.json").write_bytes(canonical_json_bytes(config))


def _execute_cohort(
    request: IntegrationAcceptanceRequest,
    snapshot: IndexedSnapshot,
    rows: tuple[RawTargetRow, ...],
    clock: Callable[[], float],
) -> tuple[BatchResult, float]:
    """Run the complete cohort within the existing approved volume bound."""
    start = clock()
    batch = classify_batch(
        rows,
        snapshot=snapshot,
        provenance=request.provenance,
        run_id=request.run_id,
    )
    elapsed = clock() - start
    if batch.status != "processed" or not 0 <= elapsed <= VOLUME_TEST_SECONDS:
        raise AssertionError("full-cohort execution or approved volume limit failed")
    return batch, elapsed


def _verify_batch_outputs(
    request: IntegrationAcceptanceRequest,
    snapshot: IndexedSnapshot,
    rows: tuple[RawTargetRow, ...],
    batch: BatchResult,
    spec: _ReferenceSpecification,
    checks: dict[str, str],
) -> Mapping[str, bytes]:
    """Verify reviewed outcomes, evidence and frozen permutation determinism."""
    try:
        _check_cases(batch, spec, request.expected_labels.parent)
        if spec["schema_version"] == 2:
            validate_executed_reference_coverage(batch, spec)
    except AssertionError:
        checks["reference_cases"] = "FAIL"
        raise
    checks["reference_cases"] = "PASS"
    try:
        _check_evidence(batch)
    except AssertionError:
        checks["evidence_integrity"] = "FAIL"
        raise
    checks["evidence_integrity"] = "PASS"
    rendered = render_batch(batch)
    repeated = classify_batch(
        tuple(reversed(rows)),
        snapshot=snapshot,
        provenance=request.provenance,
        run_id=request.run_id,
    )
    if rendered != render_batch(repeated):
        checks["semantic_determinism"] = "FAIL"
        raise AssertionError("frozen-provenance permutation determinism failed")
    checks["semantic_determinism"] = "PASS"
    return rendered


def _execution_bindings(
    cohort: AdmittedCohort,
    batch: BatchResult,
    species_taxon_ids: frozenset[str] | None = None,
) -> tuple[PipelineExecutionBinding, ...]:
    """Bind each admitted input to the semantic result of this execution."""
    by_row = {row.result.input_row_id: row.result for row in batch.rows}
    bindings: list[PipelineExecutionBinding] = []
    for row in cohort.rows:
        result = by_row.get(row.input_row_id)
        if result is None:
            raise ValueError("pipeline proof belongs to another admitted cohort")
        raw_fields: Mapping[str, object] = dict(row.fields)
        semantic = execution_semantics(result)
        business_json = row.fields.get("source_business_data")
        if business_json:
            if species_taxon_ids is None:
                raise ValueError(
                    "canonical pipeline proof requires the profile species scope"
                )
            business = json.loads(business_json)
            if not isinstance(business, dict):
                raise ValueError("canonical source business data must be an object")
            _, reason = target_input_eligibility(business, species_taxon_ids)
            if reason is not None:
                raw_fields = business
                semantic = dict.fromkeys(semantic)
                semantic.update(status="not_applicable", reason=reason)
        bindings.append(
            PipelineExecutionBinding(
                row.input_row_id,
                raw_fields,
                semantic,
            )
        )
    return tuple(bindings)


def _record_pipeline_acceptance(
    request: IntegrationAcceptanceRequest,
    receipt: dict[str, object],
    cohort: AdmittedCohort,
    batch: BatchResult,
) -> None:
    """Attach only a verified real pipeline occurrence to the receipt."""
    if request.pipeline_proof is None:
        raise ValueError("actual target pipeline integration proof is missing")
    receipt["pipeline_proof_sha256"] = verify_pipeline_proof(
        request.pipeline_proof,
        request.snapshot_manifest_sha256,
        request.pipeline_report,
        provenance=request.provenance,
        expected_row_ids=tuple(row.input_row_id for row in cohort.rows),
        expected_execution=_execution_bindings(
            cohort, batch, request.species_taxon_ids
        ),
    )
    if request.pipeline_report is not None:
        receipt["pipeline_report_sha256"] = sha256_file(request.pipeline_report)


def _publication_references(
    request: IntegrationAcceptanceRequest,
    cohort: AdmittedCohort,
    output_dir: Path,
    rendered: Mapping[str, bytes],
) -> list[dict[str, str]]:
    references = [
        _artifact_reference(
            "stage0_manifest", request.stage0_manifest, cohort.manifest_sha256
        ),
        _artifact_reference(
            "expected_labels", request.expected_labels, request.expected_labels_sha256
        ),
    ]
    for kind, path in (
        ("pipeline_proof", request.pipeline_proof),
        ("pipeline_report", request.pipeline_report),
    ):
        if path is not None:
            references.append(_artifact_reference(kind, path, sha256_file(path)))
    references.extend(_stage0_dependency_references(request.stage0_manifest))
    references.extend(
        _artifact_reference(name, output_dir / name, sha256_bytes(raw))
        for name, raw in rendered.items()
    )
    return references


def _artifact_reference(kind: str, path: Path, digest: str) -> dict[str, str]:
    if sha256_file(path) != digest:
        raise ValueError(
            "acceptance dependency bytes changed before receipt publication"
        )
    return {
        "kind": kind,
        "immutable_uri": path.resolve(strict=True).as_uri(),
        "sha256": digest,
    }


def _stage0_dependency_references(path: Path) -> list[dict[str, str]]:
    document = json.loads(path.read_bytes())
    references = []
    names = {
        "cohort_manifest.json": "cohort_manifest",
        "conversion_ledgers.json": "conversion_ledger",
    }
    for name, digest in document["artifact_sha256"].items():
        references.append(
            _artifact_reference(
                names.get(name, "stage0_proof:" + name), path.parent / name, digest
            )
        )
    for material in document["copies"]:
        references.append(
            _artifact_reference(
                "stage0_" + material["role"],
                path.parent / material["copy_path"],
                material["sha256"],
            )
        )
    return references
