"""Bronze layer DQ analyzer.

Implements minimal validation for raw Bronze data:
- Record count
- File integrity (checksum, size)
- Schema snapshot (field detection)
- Field presence rates
- Encoding validation

Follows RULES.md §3.1 DQ strategy for Bronze layer.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import orjson

from bioetl.application.services.dq.dq_report_builders import (
    build_summary,
    update_counts,
)
from bioetl.domain.ports import BronzeDQConfigPort
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    BronzeDQCheckType,
    BronzeDQReport,
    DQCheckStatus,
    EncodingValidationResult,
    FileIntegrityResult,
    MedallionLayer,
    RecordCountResult,
    SchemaSnapshotResult,
)


class BronzeDQAnalyzer:
    """Analyzer for Bronze layer DQ checks.

    Performs minimal validation on raw data to capture lineage
    without blocking ingestion. Implements BronzeDQAnalyzerPort.
    """

    def analyze(
        self,
        records: Iterator[bytes],
        *,
        run_id: str,
        pipeline: str,
        batch_id: str,
        source_file: str,
        config: BronzeDQConfigPort,
        timestamp: datetime,
    ) -> BronzeDQReport:
        """Analyze Bronze data and generate DQ report.

        Args:
            records: Iterator of raw JSON bytes records.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            batch_id: Batch identifier.
            source_file: Path to the Bronze file.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).

        Returns:
            BronzeDQReport: Complete DQ report for Bronze layer.
        """
        # Materialize records for analysis (Bronze batches are typically small)
        record_list = list(records)
        enabled_checks = set(config.get_checks_enums())

        checks: JsonDict = {}  # Any: DQ check values vary by check type
        passed = 0
        failed = 0
        warnings = 0

        # Record count check
        if BronzeDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(record_list)
            checks["record_count"] = to_dict(record_count_result)
            passed, failed, warnings = update_counts(
                record_count_result.status, passed, failed, warnings
            )

        # File integrity check
        if BronzeDQCheckType.FILE_INTEGRITY in enabled_checks:
            file_integrity_result = self._check_file_integrity(record_list)
            checks["file_integrity"] = to_dict(file_integrity_result)
            passed, failed, warnings = update_counts(
                file_integrity_result.status, passed, failed, warnings
            )

        # Schema snapshot
        if BronzeDQCheckType.SCHEMA_SNAPSHOT in enabled_checks:
            schema_snapshot_result = self._check_schema_snapshot(record_list)
            checks["schema_snapshot"] = to_dict(schema_snapshot_result)
            passed, failed, warnings = update_counts(
                schema_snapshot_result.status, passed, failed, warnings
            )

        # Raw field presence
        if BronzeDQCheckType.RAW_FIELD_PRESENCE in enabled_checks:
            field_presence_result = self._check_field_presence(record_list)
            checks["raw_field_presence"] = field_presence_result  # Already a dict
            # Count as pass (info only)
            passed += 1

        # Encoding validation
        if BronzeDQCheckType.ENCODING_VALIDATION in enabled_checks:
            encoding_result = self._check_encoding(record_list)
            checks["encoding_validation"] = to_dict(encoding_result)
            passed, failed, warnings = update_counts(
                encoding_result.status, passed, failed, warnings
            )

        summary = build_summary(passed, failed, warnings)

        return BronzeDQReport(
            layer=MedallionLayer.BRONZE,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            batch_id=batch_id,
            source_file=source_file,
            checks=checks,
            summary=summary,
        )

    def _check_record_count(self, records: list[bytes]) -> RecordCountResult:
        """Check record count."""
        count = len(records)
        return RecordCountResult(
            value=count,
            status=DQCheckStatus.PASS if count > 0 else DQCheckStatus.WARN,
        )

    def _check_file_integrity(self, records: list[bytes]) -> FileIntegrityResult:
        """Check file integrity via BLAKE2 checksum."""
        # Calculate combined checksum of all records
        hasher = hashlib.blake2b()
        total_size = 0

        for record in records:
            hasher.update(record)
            total_size += len(record)

        checksum = hasher.hexdigest()

        return FileIntegrityResult(
            checksum_blake2=checksum,
            size_bytes=total_size,
            compression_ratio=None,  # Will be calculated after compression
            status=DQCheckStatus.PASS,
        )

    def _check_schema_snapshot(self, records: list[bytes]) -> SchemaSnapshotResult:
        """Detect schema from records."""
        field_types: dict[str, set[str]] = {}

        for record in records:
            try:
                data = orjson.loads(record)
                self._update_field_types(field_types, data)
            except orjson.JSONDecodeError:
                continue

        schema = self._render_schema_snapshot(field_types)

        return SchemaSnapshotResult(
            fields_detected=len(schema),
            schema=schema,
            new_fields_since_last_run=(),  # Would need previous schema
            missing_fields_since_last_run=(),
            status=DQCheckStatus.PASS,
        )

    def _update_field_types(
        self,
        field_types: dict[str, set[str]],
        data: object,
    ) -> None:
        """Merge inferred JSON field types from one decoded record."""
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            field_types.setdefault(key, set()).add(self._infer_type(value))

    def _render_schema_snapshot(
        self,
        field_types: dict[str, set[str]],
    ) -> dict[str, str]:
        """Convert field type sets into stable string representations."""
        return {
            field: next(iter(types)) if len(types) == 1 else "|".join(sorted(types))
            for field, types in field_types.items()
        }

    def _check_field_presence(self, records: list[bytes]) -> dict[str, float]:
        """Calculate field presence rates."""
        field_counts: Counter[str] = Counter()
        total_records = len(records)

        if total_records == 0:
            return {}

        for record in records:
            try:
                data = orjson.loads(record)
                if isinstance(data, dict):
                    for key in data:
                        field_counts[key] += 1
            except orjson.JSONDecodeError:
                continue

        return {
            field: round(count / total_records, 4)
            for field, count in field_counts.items()
        }

    def _check_encoding(self, records: list[bytes]) -> EncodingValidationResult:
        """Validate UTF-8 encoding."""
        encoding_errors = 0
        invalid_records: list[int] = []

        for idx, record in enumerate(records):
            try:
                record.decode("utf-8")
            except UnicodeDecodeError:
                encoding_errors += 1
                invalid_records.append(idx)

        status = DQCheckStatus.PASS if encoding_errors == 0 else DQCheckStatus.FAIL

        return EncodingValidationResult(
            encoding_errors=encoding_errors,
            invalid_utf8_records=tuple(invalid_records),
            status=status,
        )

    def _infer_type(self, value: Any) -> str:  # Any: infers JSON type from ...
        """Infer JSON type from Python value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"


__all__ = ["BronzeDQAnalyzer"]
