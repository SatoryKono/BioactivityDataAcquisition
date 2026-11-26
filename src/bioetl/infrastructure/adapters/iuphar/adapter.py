"""Pure BioETL projection onto the existing offline classification kernel."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifact,
    TargetClassificationBatch,
    TargetClassificationInput,
    TargetClassificationResult,
)
from iuphar_target_class.bioetl_input import (
    plain_target_value as _plain,
)
from iuphar_target_class.bioetl_input import (
    project_target_fields as _raw_fields,
)
from iuphar_target_class.bioetl_input import (
    target_input_eligibility as _eligibility,
)
from iuphar_target_class.models import RawTargetRow, RunProvenance
from iuphar_target_class.pipeline import BatchResult, classify_batch
from iuphar_target_class.pipeline_io import render_batch
from iuphar_target_class.stage0.io import canonical_json_bytes

from .detail_projection import detail_projection
from .snapshot_loader import LoadedIupharProfile

_FIELD_MAP = {
    "iuphar_target_id": "matched_target_id",
    "iuphar_class": "iuphar_class",
    "iuphar_match_status": "match_status",
    "iuphar_annotation_status": "iuphar_annotation_status",
    "local_class": "local_class",
    "effective_class": "effective_class",
    "effective_source": "effective_source",
    "decision_status": "decision_status",
}


def _unclassified(
    row: TargetClassificationInput,
    profile_hash: str,
    reason: str,
    *,
    include_detail: bool,
) -> TargetClassificationResult:
    projection = dict.fromkeys(_FIELD_MAP)
    projection["target_class_profile_sha256"] = profile_hash
    if include_detail:
        projection.update(detail_projection(None, computed=False))
    payloads: dict[str, object] = {
        "classification.json": [
            {
                "input_row_id": row.input_row_id,
                "status": "not_applicable",
                "reason": reason,
                "raw_fields": _plain(row.business_data),
            }
        ],
        "evidence.json": [],
        "candidates.json": [],
        "components.json": [],
        "diagnostics.json": [
            {"input_row_id": row.input_row_id, "code": reason, "level": "warning"}
        ],
        "metrics.json": {"rows": 1, "not_applicable": 1},
    }
    return TargetClassificationResult(
        row.input_row_id,
        projection,
        tuple(
            TargetClassificationArtifact(name, canonical_json_bytes(value))
            for name, value in payloads.items()
        ),
        (reason,),
    )


def _row_result(
    batch: BatchResult, profile_hash: str, *, include_detail: bool
) -> TargetClassificationResult:
    output = batch.rows[0]
    projection = {
        key: getattr(output.result, source) for key, source in _FIELD_MAP.items()
    }
    projection["target_class_profile_sha256"] = profile_hash
    if include_detail:
        projection.update(detail_projection(output, computed=True))
    return TargetClassificationResult(
        output.result.input_row_id,
        projection,
        tuple(
            TargetClassificationArtifact(name, value)
            for name, value in render_batch(batch).items()
        ),
        tuple(
            dict.fromkeys(diagnostic.code for diagnostic in output.result.diagnostics)
        ),
    )


def _request_identities(
    inputs: tuple[TargetClassificationInput, ...], run_id: str, run_started_at: str
) -> tuple[str, ...]:
    if not run_id.strip() or not run_started_at.strip():
        raise ValueError("classification requires fixed run identity and start time")
    identities = tuple(row.input_row_id for row in inputs)
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate classification input row identities")
    for identity in identities:
        if not identity or any(mark in identity for mark in ("/", "\n", "\r")):
            raise ValueError("invalid classification input row identity")
    return identities


def _adapt_inputs(
    inputs: tuple[TargetClassificationInput, ...],
    profile: LoadedIupharProfile,
    *,
    include_detail: bool,
) -> tuple[list[RawTargetRow], dict[str, TargetClassificationResult]]:
    results: dict[str, TargetClassificationResult] = {}
    eligible: list[RawTargetRow] = []
    for row in inputs:
        taxon, reason = _eligibility(
            row.business_data,
            profile.snapshot.species_taxon_ids,
            policy=profile.matching_policy_version,
        )
        if reason is not None:
            results[row.input_row_id] = _unclassified(
                row, profile.profile_sha256, reason, include_detail=include_detail
            )
        else:
            fields = _raw_fields(row.business_data, taxon)
            eligible.append(RawTargetRow(row.input_row_id, fields, "protein"))
    return eligible, results


def _project_rows(
    classified: BatchResult, profile_sha256: str, *, include_detail: bool
) -> dict[str, TargetClassificationResult]:
    results: dict[str, TargetClassificationResult] = {}
    for row in classified.rows:
        invalid = row.result.input_validation_status == "invalid_input"
        one = BatchResult(
            rows=(row,),
            diagnostics=tuple(
                (key, value)
                for key, value in classified.diagnostics
                if key == row.result.input_row_id
            ),
            components=(),
            metrics={
                "rows": 1,
                "invalid_rows": int(invalid),
                "classified_rows": int(bool(row.result.effective_class)),
                "class_null": int(row.result.effective_class is None),
            },
            status="rejected" if invalid else "processed",
        )
        results[row.result.input_row_id] = _row_result(
            one, profile_sha256, include_detail=include_detail
        )
    return results


class IupharTargetClassificationAdapter:
    """Classify without HTTP or file writes after verified profile loading."""

    def __init__(
        self, profile: LoadedIupharProfile, *, table_contract: str = "3.1.0"
    ) -> None:
        if table_contract not in {"3.0.0", "3.1.0", "3.2.0"}:
            raise ValueError("unknown target table contract")
        self._profile = profile
        self._include_detail = table_contract == "3.2.0"
        self.profile_sha256 = profile.profile_sha256
        self.snapshot_id = profile.snapshot.snapshot.snapshot_id
        self.snapshot_manifest_sha256 = profile.snapshot.snapshot_manifest_sha256
        self.immutable_uri = profile.snapshot.immutable_uri

    def classify_record(
        self,
        business_data: Mapping[str, object],
        *,
        input_row_id: str,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationResult:
        batch = self.classify_batch(
            (TargetClassificationInput(input_row_id, business_data),),
            run_id=run_id,
            run_started_at=run_started_at,
        )
        return batch.results[0]

    def classify_batch(
        self,
        inputs: tuple[TargetClassificationInput, ...],
        *,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationBatch:
        identities = _request_identities(inputs, run_id, run_started_at)
        profile = self._profile
        eligible, results = _adapt_inputs(
            inputs, profile, include_detail=self._include_detail
        )
        classified = classify_batch(
            tuple(eligible),
            snapshot=profile.snapshot.snapshot,
            provenance=RunProvenance(
                self.snapshot_id,
                profile.normalization_version,
                profile.rules_version,
                profile.classification_schema_version,
                profile.snapshot.retrieved_at,
                run_started_at,
                matching_policy_version=profile.matching_policy_version,
            ),
            run_id=run_id,
        )
        results.update(
            _project_rows(
                classified,
                self.profile_sha256,
                include_detail=self._include_detail,
            )
        )
        metrics = dict(classified.metrics)
        metrics.update(rows=len(inputs), not_applicable=len(inputs) - len(eligible))
        return TargetClassificationBatch(
            tuple(results[key] for key in identities), metrics, self.profile_sha256
        )


__all__ = ["IupharTargetClassificationAdapter"]
