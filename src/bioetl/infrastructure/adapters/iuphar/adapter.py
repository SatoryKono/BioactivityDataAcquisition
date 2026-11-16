"""Pure BioETL projection onto the existing offline classification kernel."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import replace

from bioetl.domain.target_classification import (
    TargetClassificationArtifact,
    TargetClassificationBatch,
    TargetClassificationInput,
    TargetClassificationResult,
)
from iuphar_target_class.models import RawTargetRow, RunProvenance
from iuphar_target_class.pipeline import BatchResult, classify_batch
from iuphar_target_class.pipeline_io import render_batch
from iuphar_target_class.stage0.io import canonical_json_bytes

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
_SOURCE_TAXA = {
    "Homo sapiens": "9606",
    "Mus musculus": "10090",
    "Rattus norvegicus": "10116",
}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return None if not text or text == "unknown" else text


def _tokens(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(part for item in value for part in _tokens(item))
    text = _text(value)
    if text is None:
        return ()
    if text.startswith("["):
        loaded = json.loads(text)
        if not isinstance(loaded, list):
            raise ValueError("expected a JSON identifier array")
        return _tokens(loaded)
    return tuple(part for raw in re.split(r"[|;]", text) if (part := _text(raw)))


def _taxon(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("taxonomy_id must be a positive integer")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("taxonomy_id must be a positive integer")
        value = int(value)
    text = str(value).strip()
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        raise ValueError("taxonomy_id must be a positive integer")
    return text


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _raw_fields(data: Mapping[str, object], taxon: str | None) -> dict[str, str | None]:
    accessions = tuple(
        dict.fromkeys(
            (
                *_tokens(data.get("component_accessions")),
                *_tokens(data.get("target_xref_uniprot_ids")),
            )
        )
    )
    synonyms = tuple(
        dict.fromkeys(
            (
                *_tokens(data.get("target_protein_synonyms")),
                *_tokens(data.get("target_gene_synonyms")),
            )
        )
    )
    return {
        "target_chembl_id": _text(data.get("target_id")),
        # ChEMBL identity is never passed as the kernel's explicit IUPHAR ID.
        "target_id": _text(data.get("iuphar_target_id")),
        "uniprot": "|".join(accessions) or None,
        "organism": taxon,
        "source_organism": _text(data.get("organism")),
        "name": _text(data.get("pref_name")),
        "synonyms": "|".join(synonyms) or None,
        "ec": "|".join(_tokens(data.get("target_ec_numbers"))) or None,
        "gene_symbol": _text(data.get("gene_symbol")),
        "gene_id": _text(data.get("gene_id")),
        "source_business_data": canonical_json_bytes(_plain(data)).decode("utf-8"),
    }


def _eligibility(
    data: Mapping[str, object], species: frozenset[str]
) -> tuple[str | None, str | None]:
    if data.get("target_type") != "SINGLE PROTEIN":
        return None, "unsupported_target_type"
    try:
        taxon = _taxon(data.get("taxonomy_id"))
    except ValueError:
        return None, "invalid_taxonomy_id"
    if taxon is not None and taxon not in species:
        return taxon, "unsupported_taxon"
    source_taxon = _SOURCE_TAXA.get(_text(data.get("organism")) or "")
    if taxon is not None and source_taxon is not None and taxon != source_taxon:
        return taxon, "taxonomy_name_conflict"
    return taxon, None


def _unclassified(
    row: TargetClassificationInput, profile_hash: str, reason: str
) -> TargetClassificationResult:
    projection = dict.fromkeys(_FIELD_MAP)
    projection["target_class_profile_sha256"] = profile_hash
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


def _row_result(batch: BatchResult, profile_hash: str) -> TargetClassificationResult:
    output = batch.rows[0]
    projection = {
        key: getattr(output.result, source) for key, source in _FIELD_MAP.items()
    }
    projection["target_class_profile_sha256"] = profile_hash
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
    inputs: tuple[TargetClassificationInput, ...], profile: LoadedIupharProfile
) -> tuple[list[RawTargetRow], dict[str, TargetClassificationResult]]:
    results: dict[str, TargetClassificationResult] = {}
    eligible: list[RawTargetRow] = []
    for row in inputs:
        taxon, reason = _eligibility(
            row.business_data, profile.snapshot.species_taxon_ids
        )
        if reason is not None:
            results[row.input_row_id] = _unclassified(
                row, profile.profile_sha256, reason
            )
        else:
            eligible.append(
                RawTargetRow(
                    row.input_row_id, _raw_fields(row.business_data, taxon), "protein"
                )
            )
    return eligible, results


def _project_rows(
    classified: BatchResult, profile_sha256: str
) -> dict[str, TargetClassificationResult]:
    results: dict[str, TargetClassificationResult] = {}
    for row in classified.rows:
        invalid = row.result.input_validation_status == "invalid_input"
        one = replace(
            classified,
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
        results[row.result.input_row_id] = _row_result(one, profile_sha256)
    return results


class IupharTargetClassificationAdapter:
    """Classify without HTTP or file writes after verified profile loading."""

    def __init__(self, profile: LoadedIupharProfile) -> None:
        self._profile = profile
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
        eligible, results = _adapt_inputs(inputs, profile)
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
            ),
            run_id=run_id,
        )
        results.update(_project_rows(classified, self.profile_sha256))
        metrics = dict(classified.metrics)
        metrics.update(rows=len(inputs), not_applicable=len(inputs) - len(eligible))
        return TargetClassificationBatch(
            tuple(results[key] for key in identities), metrics, self.profile_sha256
        )


__all__ = ["IupharTargetClassificationAdapter"]
