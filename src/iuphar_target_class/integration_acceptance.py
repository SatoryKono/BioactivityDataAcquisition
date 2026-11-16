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

from .models import RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, classify_batch
from .pipeline_acceptance import SourceImport, VolumePlan, load_admitted_cohort
from .pipeline_io import render_batch
from .policy import VOLUME_TEST_SECONDS
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


def _verified_labels(request: IntegrationAcceptanceRequest) -> _ReferenceSpecification:
    raw = request.expected_labels.read_bytes()
    if sha256_bytes(raw) != request.expected_labels_sha256:
        raise ValueError("expected-label digest mismatch")
    spec = cast("_ReferenceSpecification", json.loads(raw))
    if (
        spec.get("artifact") != "bioetl_iuphar_reference_cases"
        or spec.get("schema_version") != 1
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
        references = case.get("source_references", [])
        expected = case.get("expected", {})
        if (
            not references
            or not expected
            or not set(expected).issubset(_EXPECTED_FIELDS)
        ):
            raise ValueError(
                "each reference case needs reviewed source proof and outcomes"
            )
        for reference in references:
            path = (root / reference["path"]).resolve()
            if not path.is_relative_to(root.resolve()) or path.is_symlink():
                raise ValueError("reference source escapes its specification root")
            if sha256_file(path) != reference["sha256"]:
                raise ValueError("reference source digest mismatch")
        actual = results.get(case["input_row_id"])
        if actual is None:
            raise ValueError("reference case is outside the admitted cohort")
        for field, value in expected.items():
            if getattr(actual, field) != value:
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
) -> str:
    """Verify an actual Application evidence manifest and successful run report."""
    proof = json.loads(path.read_bytes())
    if (
        proof.get("artifact") != "bioetl_iuphar_pipeline_evidence"
        or proof.get("pipeline_name") != "chembl_target"
        or proof.get("mode") not in {"shadow", "enrich"}
        or proof.get("status") != "complete"
        or proof.get("snapshot_manifest_sha256") != snapshot_sha256
        or not proof.get("run_id")
        or not isinstance(proof.get("row_count"), int)
        or proof["row_count"] <= 0
    ):
        raise ValueError("missing complete, matching target integration occurrence")
    artifacts = proof.get("artifacts", {})
    digests = proof.get("artifact_sha256", {})
    report = proof.get("pipeline_report")
    if not artifacts and isinstance(digests, dict):
        artifacts = {
            name: {"path": name, "sha256": digest} for name, digest in digests.items()
        }
    if not artifacts or (not isinstance(report, dict) and pipeline_report is None):
        raise ValueError("integration proof lacks output bytes or pipeline report")
    references = list(artifacts.values())
    if isinstance(report, dict):
        references.append(report)
    for item in references:
        artifact = (path.parent / item["path"]).resolve()
        if not artifact.is_relative_to(path.parent.resolve()):
            raise ValueError("integration artifact escapes proof root")
        if sha256_file(artifact) != item["sha256"]:
            raise ValueError("integration artifact digest mismatch")
    report_path = pipeline_report or path.parent / report["path"]
    run = json.loads(report_path.read_bytes())["identity"]
    if run.get("run_id") != proof["run_id"] or run.get("status") != "success":
        raise ValueError("integration run was not a successful matching occurrence")
    if (run.get("pipeline") or run.get("pipeline_name")) != "chembl_target":
        raise ValueError("integration proof belongs to another pipeline")
    return sha256_file(path)


def run_integration_acceptance(
    request: IntegrationAcceptanceRequest,
    *,
    snapshot: IndexedSnapshot,
    output_dir: Path,
    clock: Callable[[], float] = perf_counter,
) -> Mapping[str, object]:
    """Run full frozen cohort, compare reviewed cases and preserve a new receipt."""
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
    imports = spec.get("source_imports", [])
    if (
        {item["source_path"] for item in imports} != set(spec["selected_source_paths"])
        or any(item["format_version"] != "bioetl_target_kernel_csv_v1" for item in imports)
    ):
        raise ValueError("integration acceptance requires explicit canonical TaxID input profiles")
    if request.provenance.snapshot_id != snapshot.snapshot_id:
        raise ValueError("execution provenance belongs to another snapshot")
    if not snapshot.complete:
        raise ValueError("complete admitted snapshot required")
    cohort = load_admitted_cohort(request.stage0_manifest, _volume_plan(spec))
    if not cohort.rows or len(cohort.rows) != spec["expected_rows"]:
        raise ValueError("full admitted cohort count differs from the frozen plan")
    checks["stage0_admission"] = "PASS"
    receipt.update(
        stage0_manifest_sha256=cohort.manifest_sha256,
        reviewer_reference=spec["reviewer_reference"],
    )
    config = {
        "snapshot_manifest_sha256": request.snapshot_manifest_sha256,
        "expected_labels_sha256": request.expected_labels_sha256,
        "stage0_manifest_sha256": cohort.manifest_sha256,
        "run_id": request.run_id,
        "expected_rows": len(cohort.rows),
    }
    (output_dir / "execution-config.json").write_bytes(canonical_json_bytes(config))
    start = clock()
    batch = classify_batch(
        cohort.rows,
        snapshot=snapshot,
        provenance=request.provenance,
        run_id=request.run_id,
    )
    elapsed = clock() - start
    if batch.status != "processed" or not 0 <= elapsed <= VOLUME_TEST_SECONDS:
        raise AssertionError("full-cohort execution or approved volume limit failed")
    _check_cases(batch, spec, request.expected_labels.parent)
    checks["reference_cases"] = "PASS"
    _check_evidence(batch)
    checks["evidence_integrity"] = "PASS"
    rendered = render_batch(batch)
    repeated = classify_batch(
        tuple(reversed(cohort.rows)),
        snapshot=snapshot,
        provenance=request.provenance,
        run_id=request.run_id,
    )
    if rendered != render_batch(repeated):
        raise AssertionError("frozen-provenance permutation determinism failed")
    checks["semantic_determinism"] = "PASS"
    receipt.update(
        output_sha256={name: sha256_bytes(raw) for name, raw in rendered.items()},
        elapsed_seconds=elapsed,
        rows=len(cohort.rows),
        reference_cases_accepted=True,
    )
    for name, raw in rendered.items():
        (output_dir / name).write_bytes(raw)
    if request.pipeline_proof is None:
        raise ValueError("actual target pipeline integration proof is missing")
    receipt["pipeline_proof_sha256"] = verify_pipeline_proof(
        request.pipeline_proof,
        request.snapshot_manifest_sha256,
        request.pipeline_report,
    )
    if request.pipeline_report is not None:
        receipt["pipeline_report_sha256"] = sha256_file(request.pipeline_report)
    checks["pipeline_integration"] = "PASS"
    receipt["status"] = "PASS"
