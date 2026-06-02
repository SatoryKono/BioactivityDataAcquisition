"""Application-level debug export collection for per-run audit packs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, GoldRecord, RunID

__all__ = [
    "DEBUG_REASON_DICTIONARY",
    "DebugExportConfig",
    "DebugExportPack",
    "DebugExportResult",
    "DebugExportService",
    "DebugExportWriterPort",
]


_SOURCE_ID_FIELDS = (
    "activity_id",
    "document_chembl_id",
    "publication_id",
    "molecule_chembl_id",
    "target_chembl_id",
    "assay_chembl_id",
    "chembl_id",
    "id",
    "entity_id",
)


DEBUG_REASON_DICTIONARY: tuple[dict[str, str], ...] = (
    {
        "reason_code": "SCHEMA_REQUIRED_FIELD_MISSING",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Required field is missing from the record payload.",
    },
    {
        "reason_code": "SCHEMA_TYPE_MISMATCH",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Record payload failed schema/type validation.",
    },
    {
        "reason_code": "DQ_SOFT_RULE_FAILED",
        "rule_layer": "silver",
        "action": "skip",
        "reason_message": "A non-fatal runtime DQ rule rejected the record.",
    },
    {
        "reason_code": "DQ_HARD_RULE_FAILED",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "A blocking runtime DQ rule rejected the record.",
    },
    {
        "reason_code": "DUPLICATE_PRIMARY_KEY",
        "rule_layer": "silver",
        "action": "skip",
        "reason_message": "A duplicate business key was skipped during merge.",
    },
    {
        "reason_code": "SEMANTIC_FILTER_EXCLUDED",
        "rule_layer": "gold",
        "action": "filter",
        "reason_message": "Gold semantic filter excluded the record.",
    },
    {
        "reason_code": "CROSS_VALIDATION_NULLIFIED",
        "rule_layer": "cross_validation",
        "action": "nullify",
        "reason_message": "Cross-validation nullified one or more fields.",
    },
    {
        "reason_code": "GOLD_CONTRACT_VIOLATION",
        "rule_layer": "gold",
        "action": "fail",
        "reason_message": "Gold strict contract validation rejected the record.",
    },
    {
        "reason_code": "QUARANTINE_POLICY",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Runtime invalid-record policy routed the record to quarantine.",
    },
)


@dataclass(frozen=True, slots=True)
class DebugExportConfig:
    """Runtime configuration for debug audit-pack export."""

    enabled: bool = False
    formats: tuple[str, ...] = ("csv", "xlsx")
    output_dir: str = "artifacts/debug_exports"
    include_bom: bool = False
    max_rows_per_sheet: int = 1_048_576
    workflow_id: str = "standalone"


@dataclass(frozen=True, slots=True)
class DebugExportPack:
    """Deterministic in-memory representation of one debug export run pack."""

    run_id: str
    pipeline_id: str
    provider_id: str
    workflow_id: str
    manifest_id: str | None
    status: str
    output_root: str
    formats: tuple[str, ...]
    include_bom: bool
    max_rows_per_sheet: int
    created_at: datetime
    tables: dict[str, tuple[dict[str, object], ...]]
    reason_dictionary: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class DebugExportResult:
    """Persisted debug export artifact metadata."""

    root_path: str
    manifest_path: str
    debug_export_hash: str
    file_paths: tuple[str, ...] = ()


class DebugExportWriterPort(Protocol):
    """Infrastructure writer contract for persisted debug export packs."""

    def write_pack(
        self,
        *,
        pack: DebugExportPack,
    ) -> DebugExportResult:
        """Persist the provided audit pack and return artifact metadata."""
        ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_optional_text(value: object | None) -> str | None:
    text = _normalize_text(value).strip()
    return text or None


def _safe_payload(record: Mapping[str, object] | None) -> dict[str, object]:
    return {} if record is None else dict(record)


def _primary_key(record: Mapping[str, object] | None) -> str:
    payload = _safe_payload(record)
    entity_id = _normalize_optional_text(payload.get("entity_id"))
    if entity_id is not None:
        return entity_id
    source_id = _source_record_id(payload)
    return source_id or ""


def _source_record_id(record: Mapping[str, object] | None) -> str:
    payload = _safe_payload(record)
    for field_name in _SOURCE_ID_FIELDS:
        value = _normalize_optional_text(payload.get(field_name))
        if value is not None:
            return value
    return ""


def _infer_failed_field(record: Mapping[str, object], details: str) -> str:
    lowered = details.lower()
    for field_name in sorted(record):
        if field_name.lower() in lowered:
            return field_name
    return ""


def _extract_rule_id(details: str) -> str:
    if "rules=[" not in details:
        return ""
    _, _, tail = details.partition("rules=[")
    value, _, _ = tail.partition("]")
    return value.strip()


def _infer_reason_code(
    *,
    error_type: ErrorType | None = None,
    details: str = "",
    policy: str | None = None,
) -> str:
    normalized = details.lower()
    if "missing" in normalized and (
        "field" in normalized or "_" in normalized or ":" in normalized
    ):
        return "SCHEMA_REQUIRED_FIELD_MISSING"
    if "schema" in normalized or (
        error_type is not None and error_type.value == "schema_violation"
    ):
        return "SCHEMA_TYPE_MISMATCH"
    if "runtime dq validation failed" in normalized:
        return "DQ_HARD_RULE_FAILED"
    if policy == "quarantine":
        return "QUARANTINE_POLICY"
    return "DQ_SOFT_RULE_FAILED"


def _payload_hash(
    *,
    provider_id: str,
    record: Mapping[str, object] | None,
) -> str:
    payload = _safe_payload(record)
    if not payload:
        return ""
    existing = _normalize_optional_text(payload.get("content_hash"))
    if existing is not None:
        return existing
    generator = EntityIdentityGenerator()
    return str(generator.compute_content_hash(provider_id, payload))


def _jsonable_payload(payload: Mapping[str, object] | None) -> str:
    import json

    return json.dumps(_safe_payload(payload), ensure_ascii=False, sort_keys=True)


def _base_row(
    *,
    run_id: str,
    workflow_id: str,
    pipeline_id: str,
    provider_id: str,
    stage: str,
    record_index: int,
    raw_record: Mapping[str, object] | None,
    normalized_record: Mapping[str, object] | None,
    status: str,
    created_at: datetime,
    action: str = "",
    reason_code: str = "",
    reason_message: str = "",
    rule_id: str = "",
    rule_layer: str = "",
    failed_field: str = "",
    failed_value: str = "",
    expected_constraint: str = "",
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "pipeline_id": pipeline_id,
        "provider_id": provider_id,
        "stage": stage,
        "record_index": record_index,
        "source_record_id": _source_record_id(raw_record or normalized_record),
        "primary_key": _primary_key(normalized_record or raw_record),
        "payload_hash": _payload_hash(
            provider_id=provider_id,
            record=normalized_record or raw_record,
        ),
        "input_payload_hash": _payload_hash(provider_id=provider_id, record=raw_record),
        "output_payload_hash": _payload_hash(
            provider_id=provider_id,
            record=normalized_record,
        ),
        "status": status,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "rule_id": rule_id,
        "rule_layer": rule_layer,
        "failed_field": failed_field,
        "failed_value": failed_value,
        "expected_constraint": expected_constraint,
        "action": action,
        "created_at": created_at.isoformat(),
        "raw_payload": _jsonable_payload(raw_record),
        "normalized_payload": _jsonable_payload(normalized_record),
    }


class DebugExportService:
    """Collect per-run audit rows before persistence through an adapter."""

    def __init__(
        self,
        *,
        config: DebugExportConfig,
        run_id: RunID | UUID,
        pipeline_id: str,
        provider_id: str,
        manifest_id: str | None = None,
        writer: DebugExportWriterPort | None = None,
        created_at_factory: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._config = config
        self._run_id = str(run_id)
        self._pipeline_id = pipeline_id
        self._provider_id = provider_id
        self._manifest_id = manifest_id
        self._writer = writer
        self._created_at_factory = created_at_factory
        self._bronze_rows: list[dict[str, object]] = []
        self._silver_full_rows: list[dict[str, object]] = []
        self._silver_rejected_rows: list[dict[str, object]] = []
        self._silver_quarantine_rows: list[dict[str, object]] = []
        self._gold_full_rows: list[dict[str, object]] = []
        self._gold_rejected_rows: list[dict[str, object]] = []
        self._lineage_rows: list[dict[str, object]] = []
        self._debug_root: str | None = None
        self._gold_record_index_by_hash: dict[str, int] = {}

    @property
    def enabled(self) -> bool:
        return bool(self._config.enabled)

    @property
    def workflow_id(self) -> str:
        return self._config.workflow_id

    @property
    def output_dir(self) -> str:
        return self._config.output_dir

    def attach_manifest_id(self, manifest_id: str | None) -> None:
        self._manifest_id = manifest_id

    def set_debug_root(self, path: str | Path) -> None:
        self._debug_root = str(path)

    def record_bronze_batch(
        self,
        *,
        records: Sequence[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
        source_metadata: object | None = None,
    ) -> None:
        if not self.enabled:
            return
        source_attrs = (
            source_metadata.model_dump()
            if hasattr(source_metadata, "model_dump")
            else (
                dict(source_metadata)
                if isinstance(source_metadata, Mapping)
                else {"source_metadata": _normalize_text(source_metadata)}
                if source_metadata is not None
                else {}
            )
        )
        for offset, raw_record in enumerate(records):
            row = _base_row(
                run_id=self._run_id,
                workflow_id=self.workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="bronze",
                record_index=start_index + offset,
                raw_record=raw_record,
                normalized_record=raw_record,
                status="included",
                action="extract",
                created_at=self._created_at_factory(),
            )
            row["batch_id"] = str(batch_id)
            row["source_metadata"] = _jsonable_payload(source_attrs)
            self._bronze_rows.append(row)

    def record_transform_success(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        silver_record: BronzeRecord,
        gold_record: GoldRecord | None,
        gold_excluded_by_contract: bool,
    ) -> None:
        if not self.enabled:
            return
        created_at = self._created_at_factory()
        self._silver_full_rows.append(
            _base_row(
                run_id=self._run_id,
                workflow_id=self.workflow_id,
                pipeline_id=self._pipeline_id,
                provider_id=self._provider_id,
                stage="silver",
                record_index=record_index,
                raw_record=raw_record,
                normalized_record=silver_record,
                status="included",
                action="include",
                created_at=created_at,
            )
        )
        if gold_record is not None:
            self._gold_record_index_by_hash[
                _payload_hash(provider_id=self._provider_id, record=gold_record)
            ] = record_index
            self._gold_full_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self.workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=raw_record,
                    normalized_record=gold_record,
                    status="included",
                    action="include",
                    created_at=created_at,
                )
            )
            return
        if gold_excluded_by_contract:
            self._gold_rejected_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self.workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=raw_record,
                    normalized_record=silver_record,
                    status="skipped",
                    action="filter",
                    reason_code="SEMANTIC_FILTER_EXCLUDED",
                    reason_message="Gold semantic filter excluded the record.",
                    rule_layer="gold",
                    created_at=created_at,
                )
            )

    def record_filtered_out(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        reason: str,
        details: Mapping[str, object] | None,
        policy: str,
    ) -> None:
        if not self.enabled:
            return
        row = _base_row(
            run_id=self._run_id,
            workflow_id=self.workflow_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            stage="silver",
            record_index=record_index,
            raw_record=raw_record,
            normalized_record=None,
            status="quarantined" if policy == "quarantine" else "skipped",
            action="quarantine" if policy == "quarantine" else "skip",
            reason_code="DQ_SOFT_RULE_FAILED",
            reason_message=reason,
            rule_layer="silver",
            rule_id=_extract_rule_id(reason),
            failed_field=_infer_failed_field(raw_record, reason),
            failed_value=_normalize_text(
                (details or {}).get(_infer_failed_field(raw_record, reason), "")
            ),
            created_at=self._created_at_factory(),
        )
        target = (
            self._silver_quarantine_rows
            if policy == "quarantine"
            else self._silver_rejected_rows
        )
        target.append(row)

    def record_data_quality_failure(
        self,
        *,
        raw_record: BronzeRecord,
        record_index: int,
        error_type: ErrorType,
        error_details: str,
        policy: str,
    ) -> None:
        if not self.enabled:
            return
        reason_code = _infer_reason_code(
            error_type=error_type,
            details=error_details,
            policy=policy,
        )
        row = _base_row(
            run_id=self._run_id,
            workflow_id=self.workflow_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            stage="silver",
            record_index=record_index,
            raw_record=raw_record,
            normalized_record=None,
            status="quarantined" if policy == "quarantine" else "skipped",
            action="quarantine" if policy == "quarantine" else "skip",
            reason_code=reason_code,
            reason_message=error_details,
            rule_id=_extract_rule_id(error_details),
            rule_layer="silver",
            failed_field=_infer_failed_field(raw_record, error_details),
            failed_value=_normalize_text(
                raw_record.get(_infer_failed_field(raw_record, error_details), "")
            ),
            expected_constraint=error_type.value,
            created_at=self._created_at_factory(),
        )
        target = (
            self._silver_quarantine_rows
            if policy == "quarantine"
            else self._silver_rejected_rows
        )
        target.append(row)

    def record_gold_validation_failure(
        self,
        *,
        records: Sequence[GoldRecord],
        errors: Sequence[str],
    ) -> None:
        if not self.enabled:
            return
        error_message = "; ".join(errors)
        for record in records:
            record_index = self._gold_record_index_by_hash.get(
                _payload_hash(provider_id=self._provider_id, record=record),
                -1,
            )
            self._gold_rejected_rows.append(
                _base_row(
                    run_id=self._run_id,
                    workflow_id=self.workflow_id,
                    pipeline_id=self._pipeline_id,
                    provider_id=self._provider_id,
                    stage="gold",
                    record_index=record_index,
                    raw_record=None,
                    normalized_record=record,
                    status="rejected",
                    action="fail",
                    reason_code="GOLD_CONTRACT_VIOLATION",
                    reason_message=error_message,
                    rule_layer="gold",
                    rule_id="gold.strict_contract",
                    failed_field=_infer_failed_field(record, error_message),
                    failed_value=_normalize_text(
                        record.get(_infer_failed_field(record, error_message), "")
                    ),
                    expected_constraint="strict_gold_validation",
                    created_at=self._created_at_factory(),
                )
            )

    def record_lineage_rows(
        self,
        rows: Sequence[Mapping[str, object]],
    ) -> None:
        if not self.enabled:
            return
        self._lineage_rows.extend(dict(row) for row in rows)

    def build_pack(
        self,
        *,
        status: str,
        manifest_id: str | None = None,
    ) -> DebugExportPack:
        manifest_value = manifest_id if manifest_id is not None else self._manifest_id
        tables = {
            "bronze_index": tuple(sorted(self._bronze_rows, key=_row_sort_key)),
            "silver_full": tuple(sorted(self._silver_full_rows, key=_row_sort_key)),
            "silver_rejected": tuple(
                sorted(self._silver_rejected_rows, key=_row_sort_key)
            ),
            "silver_quarantine": tuple(
                sorted(self._silver_quarantine_rows, key=_row_sort_key)
            ),
            "gold_full": tuple(sorted(self._gold_full_rows, key=_row_sort_key)),
            "gold_rejected": tuple(sorted(self._gold_rejected_rows, key=_row_sort_key)),
            "dq_summary": tuple(self._build_dq_summary_rows()),
            "lineage": tuple(sorted(self._lineage_rows, key=_lineage_sort_key)),
            "reason_dictionary": DEBUG_REASON_DICTIONARY,
        }
        return DebugExportPack(
            run_id=self._run_id,
            pipeline_id=self._pipeline_id,
            provider_id=self._provider_id,
            workflow_id=self.workflow_id,
            manifest_id=manifest_value,
            status=status,
            output_root=self._debug_root or self.output_dir,
            formats=self._config.formats,
            include_bom=self._config.include_bom,
            max_rows_per_sheet=self._config.max_rows_per_sheet,
            created_at=self._created_at_factory(),
            tables=tables,
            reason_dictionary=DEBUG_REASON_DICTIONARY,
        )

    def finalize(
        self,
        *,
        status: str,
        manifest_id: str | None = None,
    ) -> DebugExportResult | None:
        if not self.enabled or self._writer is None:
            return None
        return self._writer.write_pack(
            pack=self.build_pack(status=status, manifest_id=manifest_id)
        )

    def _build_dq_summary_rows(self) -> tuple[dict[str, object], ...]:
        counter: Counter[tuple[str, str, str, str]] = Counter()
        for table_name in ("silver_rejected", "silver_quarantine", "gold_rejected"):
            for row in getattr(self, f"_{table_name}_rows"):
                counter[
                    (
                        _normalize_text(row.get("stage")),
                        _normalize_text(row.get("status")),
                        _normalize_text(row.get("reason_code")),
                        _normalize_text(row.get("action")),
                    )
                ] += 1
        return tuple(
            {
                "run_id": self._run_id,
                "workflow_id": self.workflow_id,
                "pipeline_id": self._pipeline_id,
                "stage": stage,
                "status": status,
                "reason_code": reason_code,
                "action": action,
                "record_count": count,
            }
            for (stage, status, reason_code, action), count in sorted(counter.items())
        )


def _row_sort_key(row: Mapping[str, object]) -> tuple[int | None, str, str]:
    index_value = row.get("record_index")
    try:
        record_index = int(index_value) if index_value is not None else None
    except (TypeError, ValueError):
        record_index = None
    return (
        record_index,
        _normalize_text(row.get("primary_key")),
        _normalize_text(row.get("payload_hash")),
    )


def _lineage_sort_key(row: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        _normalize_text(row.get("fragment_id")),
        _normalize_text(row.get("edge_type")),
        _normalize_text(row.get("node_id")),
    )
