"""Apply remaining S1 C3–C6 correctness residuals (one-shot patcher)."""

# NOSONAR - S1192 duplicated literals are intentional for replace(old, new) pattern in patcher script

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label}: target block missing in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"fixed {label}")


def main() -> None:
    # --- #7771 gold support: capability check + rebind_schema API ---
    gold_support = ROOT / "src/bioetl/application/core/_batch_writer_gold_support.py"
    gold_support.write_text(
        '''# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Gold-layer prepare/validate helpers for BatchWriter IO paths."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.exceptions import SchemaViolationError

if TYPE_CHECKING:
    from bioetl.domain.types import GoldRecord


@runtime_checkable
class _GoldValidatorRebindProtocol(Protocol):
    """Validators that can rebind to a projected Gold schema."""

    def rebind_schema(self, schema: object) -> object: ...


def prepare_gold_records(
    writer: object,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
) -> tuple[list[GoldRecord], list[str]]:
    """Project records to schema and compute available columns."""
    target_schema = schema if schema is not None else writer._gold_schema
    schema_columns = writer._get_schema_columns(target_schema)
    if not schema_columns:
        return records, writer._collect_record_columns(records)

    dq_defaults = {"_dq_warn": False, "_dq_error": False}
    projected = [
        {
            key: record.get(key, dq_defaults.get(key))
            for key in schema_columns
            if key in record or key in dq_defaults
        }
        for record in records
    ]
    return projected, list(schema_columns)


def validate_gold_records(
    writer: object,
    records: list[GoldRecord],
    *,
    schema: object | None = None,
) -> None:
    """Validate Gold records against schema contract."""
    validator = writer._gold_validator
    target_schema = schema if schema is not None else writer._gold_schema
    if schema is not None:
        validator = rebind_gold_validator_schema(validator, target_schema)

    result = validator.validate(records)
    if not result.valid:
        debug_export_service = getattr(writer, "_debug_export_service", None)
        if debug_export_service is not None:
            debug_export_service.record_gold_validation_failure(
                records=records,
                errors=result.errors,
            )
        raise SchemaViolationError("gold", result.errors)


def rebind_gold_validator_schema(
    validator: object,
    schema: object,
) -> object:
    """Rebind schema-aware validators via their owned rebind/clone API."""
    rebind = getattr(validator, "rebind_schema", None)
    if callable(rebind):
        return rebind(schema)
    # Validators without a rebind surface keep their original schema binding.
    return validator


def should_defer_gold_validation_to_storage(writer: object) -> bool:
    """Whether Gold validation/projection must happen per-version in storage."""
    policy = getattr(writer, "_gold_schema_policy_by_version", None)
    return bool(policy is not None and policy.is_multi_version)
''',
        encoding="utf-8",
    )
    print("fixed gold_support")

    # Add rebind_schema to PanderaGoldValidator / BasePanderaValidator
    pandera = ROOT / "src/bioetl/infrastructure/validation/pandera_validator.py"
    text = pandera.read_text(encoding="utf-8")
    if "def rebind_schema(" not in text:
        marker = "    def validate(\n        self,\n        records: list[\n            JsonDict  # Any: validated records have heterogeneous field types\n        ],  # Any: validated records have heterogeneous field types\n    ) -> ValidationResult:  # Any: validated records have heterogeneous field types\n"
        insert = (
            "    def rebind_schema(self, schema: pa.DataFrameSchema | None) -> BasePanderaValidator:\n"
            '        """Return a same-class validator bound to ``schema`` without private attrs."""\n'
            "        return type(self)(schema=schema, strict=self._strict)\n"
            "\n" + marker
        )
        if marker not in text:
            raise SystemExit("pandera validate marker missing")
        pandera.write_text(text.replace(marker, insert, 1), encoding="utf-8")
        print("fixed pandera rebind_schema")
    else:
        print("pandera rebind_schema already present")

    # ContractAwareGoldValidator should preserve dq_config on rebind
    contract = ROOT / "src/bioetl/infrastructure/validation/contract_validator.py"
    ctext = contract.read_text(encoding="utf-8")
    if "def rebind_schema(" not in ctext:
        insert_at = "    @property\n    def policy_ref(self) -> DQPolicyRef | None:\n"
        method = (
            "    def rebind_schema(self, schema: pa.DataFrameSchema | None) -> ContractAwareGoldValidator:\n"
            '        """Return a clone bound to ``schema`` preserving DQ config."""\n'
            "        return type(self)(\n"
            "            schema=schema,\n"
            "            strict=self._strict,\n"
            "            dq_config=self._dq_config,\n"
            "        )\n"
            "\n"
        )
        if insert_at not in ctext:
            raise SystemExit("contract validator marker missing")
        contract.write_text(
            ctext.replace(insert_at, method + insert_at, 1), encoding="utf-8"
        )
        print("fixed contract rebind_schema")
    else:
        print("contract rebind_schema already present")

    # GoldValidatorPort optional rebind (documented via Protocol extension not required)

    # --- #7780 columns: return None on projection failures ---
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_columns_mixin.py",
        (
            "        try:\n"
            "            converted = to_schema()\n"
            '            select_columns = getattr(converted, "select_columns", None)\n'
            "            if callable(select_columns):\n"
            "                return cast(object, select_columns(list(column_order)))\n"
            "        except _SCHEMA_EXTRACTION_ERRORS:\n"
            "            return schema\n"
            "        return None\n"
        ),
        (
            "        try:\n"
            "            converted = to_schema()\n"
            '            select_columns = getattr(converted, "select_columns", None)\n'
            "            if callable(select_columns):\n"
            "                return cast(object, select_columns(list(column_order)))\n"
            "        except _SCHEMA_EXTRACTION_ERRORS:\n"
            "            return None\n"
            "        return None\n"
        ),
        "columns_to_schema",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_columns_mixin.py",
        (
            "        try:\n"
            "            return cast(object, select_columns(list(column_order)))\n"
            "        except _SCHEMA_EXTRACTION_ERRORS:\n"
            "            return schema\n"
        ),
        (
            "        try:\n"
            "            return cast(object, select_columns(list(column_order)))\n"
            "        except _SCHEMA_EXTRACTION_ERRORS:\n"
            "            return None\n"
        ),
        "columns_select",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_columns_mixin.py",
        (
            "        except (ImportError, AttributeError, TypeError, ValueError):\n"
            "            return schema\n"
        ),
        (
            "        except (ImportError, AttributeError, TypeError, ValueError):\n"
            "            return None\n"
        ),
        "columns_pyarrow",
    )

    # --- #7781 gold IO path: single column resolve + prepare/validate order ---
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_io_mixin.py",
        (
            "        try:\n"
            "            schema_payload: object = self._gold_schema\n"
            "            if should_defer_gold_validation_to_storage(self):\n"
            "                available_cols = self._collect_record_columns(records)\n"
            "                schema_payload = self._gold_schema_policy_by_version\n"
            "            else:\n"
            "                available_cols = list(\n"
            "                    self._get_schema_columns(self._gold_schema) or ()\n"
            "                ) or self._collect_record_columns(records)\n"
            "                column_order, rename_map = self._resolve_layer_columns(\n"
            '                    "gold", available_cols\n'
            "                )\n"
            "                schema_payload = self._project_schema_for_layer(\n"
            '                    "gold",\n'
            "                    self._gold_schema,\n"
            "                    column_order,\n"
            "                )\n"
            "                records, available_cols = prepare_gold_records(\n"
            "                    self,\n"
            "                    records,\n"
            "                    schema=schema_payload,\n"
            "                )\n"
            "                validate_gold_records(self, records, schema=schema_payload)\n"
            "\n"
            "            column_order, rename_map = self._resolve_layer_columns(\n"
            '                "gold", available_cols\n'
            "            )\n"
            "            if rename_map:\n"
            "                records = self._apply_renames_to_records(records, rename_map)\n"
        ),
        (
            "        try:\n"
            "            if should_defer_gold_validation_to_storage(self):\n"
            "                available_cols = self._collect_record_columns(records)\n"
            "                schema_payload: object = self._gold_schema_policy_by_version\n"
            "            else:\n"
            "                records, available_cols = prepare_gold_records(self, records)\n"
            "                validate_gold_records(self, records)\n"
            "                column_order_preview, _rename_preview = self._resolve_layer_columns(\n"
            '                    "gold", available_cols\n'
            "                )\n"
            "                schema_payload = self._project_schema_for_layer(\n"
            '                    "gold",\n'
            "                    self._gold_schema,\n"
            "                    column_order_preview,\n"
            "                )\n"
            "                # Re-project/validate against the layer-projected schema when available.\n"
            "                if schema_payload is not None and schema_payload is not self._gold_schema:\n"
            "                    records, available_cols = prepare_gold_records(\n"
            "                        self,\n"
            "                        records,\n"
            "                        schema=schema_payload,\n"
            "                    )\n"
            "                    validate_gold_records(self, records, schema=schema_payload)\n"
            "\n"
            "            column_order, rename_map = self._resolve_layer_columns(\n"
            '                "gold", available_cols\n'
            "            )\n"
            "            if rename_map:\n"
            "                records = self._apply_renames_to_records(records, rename_map)\n"
        ),
        "gold_io_path",
    )

    # --- #7782 tracing: close spans on CancelledError ---
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_io_mixin.py",
        (
            "            self._end_span(span)\n"
            "            persisted_bronze_result: BronzeWriteResult = bronze_result\n"
            "            return persisted_bronze_result\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
        ),
        (
            "            self._end_span(span)\n"
            "            persisted_bronze_result: BronzeWriteResult = bronze_result\n"
            "            return persisted_bronze_result\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
            "        except BaseException:\n"
            "            # asyncio.CancelledError (BaseException) must still close the span.\n"
            "            self._end_span(span)\n"
            "            raise\n"
        ),
        "bronze_cancel_span",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_io_mixin.py",
        (
            "            self._end_span(span)\n"
            "            persisted_silver_result: SilverWriteResult | None = silver_result\n"
            "            return persisted_silver_result\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
        ),
        (
            "            self._end_span(span)\n"
            "            persisted_silver_result: SilverWriteResult | None = silver_result\n"
            "            return persisted_silver_result\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
            "        except BaseException:\n"
            "            self._end_span(span)\n"
            "            raise\n"
        ),
        "silver_cancel_span",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/batch_writer_io_mixin.py",
        (
            "            self._end_span(span)\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
            "\n"
            "    def _prepare_gold_records(\n"
        ),
        (
            "            self._end_span(span)\n"
            "        except _WRITE_SPAN_ERRORS as error:\n"
            "            self._end_span(span, error)\n"
            "            raise\n"
            "        except BaseException:\n"
            "            self._end_span(span)\n"
            "            raise\n"
            "\n"
            "    def _prepare_gold_records(\n"
        ),
        "gold_cancel_span",
    )

    # --- #7774 dq helpers ---
    replace_once(
        ROOT / "src/bioetl/application/core/batch_executor_dq_helpers.py",
        (
            "def extract_dq_entity(config: RecordProcessorConfig) -> str:\n"
            '    """Derive entity name for report naming from silver table naming."""\n'
            "    table_config = config.table_config\n"
            "    silver_table = table_config.silver_table\n"
            "    entity_type = config.entity_type\n"
            '    if silver_table and "_" in silver_table:\n'
            '        underscore_entity: str = silver_table.split("_", 1)[1]\n'
            "        return underscore_entity\n"
            '    if silver_table and "." in silver_table:\n'
            '        dotted_entity: str = silver_table.split(".")[-1]\n'
            "        return dotted_entity\n"
            "    resolved_entity: str = silver_table or entity_type\n"
            "    return resolved_entity\n"
        ),
        (
            "def extract_dq_entity(config: RecordProcessorConfig) -> str:\n"
            '    """Derive entity name for report naming from silver table naming.\n'
            "\n"
            "    Strip schema qualifiers first, then optional ``silver_`` layer prefixes,\n"
            "    so entity names that contain underscores remain intact.\n"
            '    """\n'
            "    table_config = config.table_config\n"
            "    silver_table = table_config.silver_table\n"
            "    entity_type = config.entity_type\n"
            "    if not silver_table:\n"
            "        return entity_type\n"
            "    # schema.entity -> entity (preserve underscores in entity segment)\n"
            '    name = silver_table.rsplit(".", 1)[-1]\n'
            '    if name.startswith("silver_"):\n'
            '        return name.removeprefix("silver_")\n'
            "    return name\n"
        ),
        "extract_dq_entity",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/batch_executor_dq_helpers.py",
        (
            '    replay_timestamp_anchor = getattr(context, "replay_timestamp_anchor", None)\n'
            '    started_at = getattr(context, "started_at", None)\n'
            "    if started_at is None:\n"
            "        started_at = current_utc_time()\n"
            "    dq_timestamp = replay_timestamp_anchor or started_at\n"
        ),
        (
            '    replay_timestamp_anchor = getattr(context, "replay_timestamp_anchor", None)\n'
            "    started_at = context.started_at\n"
            "    if started_at is None:\n"
            '        raise ValueError("PipelineContext.started_at is required for DQ report context")\n'
            "    dq_timestamp = replay_timestamp_anchor or started_at\n"
        ),
        "dq_started_at",
    )
    # Drop unused current_utc_time import if present
    dq_helpers = ROOT / "src/bioetl/application/core/batch_executor_dq_helpers.py"
    dtext = dq_helpers.read_text(encoding="utf-8")
    if "current_utc_time" in dtext and "started_at = current_utc_time" not in dtext:
        # remove import line if now unused
        lines = dtext.splitlines(keepends=True)
        new_lines = [ln for ln in lines if "current_utc_time" not in ln]
        dq_helpers.write_text("".join(new_lines), encoding="utf-8")
        print("removed unused current_utc_time import")

    # --- #7775 reservoir: drop hasattr guards (runtime state already inits) ---
    replace_once(
        ROOT / "src/bioetl/application/core/batch_executor_dq_mixin.py",
        (
            '        """Add item to a bounded deterministic sample ranked by stable content."""\n'
            '        if not hasattr(self, "_dq_total_seen"):\n'
            "            self._dq_total_seen = 0\n"
            '        if not hasattr(self, "_dq_reservoir_ranks"):\n'
            "            self._dq_reservoir_ranks = {}\n"
            "        self._dq_total_seen += 1\n"
            "        reservoir_ranks = self._dq_reservoir_ranks.setdefault(id(reservoir), [])\n"
        ),
        (
            '        """Add item to a bounded deterministic sample ranked by stable content."""\n'
            "        self._dq_total_seen += 1\n"
            "        # Stage-keyed rank map (initialized on BatchExecutorRuntimeState).\n"
            "        stage_key = id(reservoir)\n"
            "        reservoir_ranks = self._dq_reservoir_ranks.setdefault(stage_key, [])\n"
        ),
        "reservoir_hasattr",
    )

    # --- #7772 quarantine metrics ---
    replace_once(
        ROOT / "src/bioetl/application/core/_quarantine_metrics_support.py",
        (
            "    if batch_metrics is not None:\n"
            "        batch_metrics.track_quarantined_records(error_type, count)\n"
            "        return\n"
            "    if metrics is None:\n"
            "        return\n"
            '    track_quarantined_records = getattr(metrics, "track_quarantined_records", None)\n'
            "    if callable(track_quarantined_records):\n"
            "        track_quarantined_records(error_type, count)\n"
            "    metrics.increment_counter(\n"
        ),
        (
            "    if batch_metrics is not None:\n"
            "        batch_metrics.track_quarantined_records(error_type, count)\n"
            "        return\n"
            "    if metrics is None:\n"
            "        return\n"
            "    metrics.increment_counter(\n"
        ),
        "track_quarantine_metrics",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/_quarantine_metrics_support.py",
        (
            "    if batch_metrics is not None:\n"
            '        batch_metrics.track_processed_records("quarantined", count)\n'
            "        return\n"
            "    if metrics is None:\n"
            "        return\n"
            '    track_processed_records = getattr(metrics, "track_processed_records", None)\n'
            "    if callable(track_processed_records):\n"
            '        track_processed_records("quarantined", count)\n'
            "    metrics.increment_counter(\n"
        ),
        (
            "    if batch_metrics is not None:\n"
            '        batch_metrics.track_processed_records("quarantined", count)\n'
            "        return\n"
            "    if metrics is None:\n"
            "        return\n"
            "    metrics.increment_counter(\n"
        ),
        "track_processed_quarantined",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/_quarantine_metrics_support.py",
        (
            '    """Emit metrics for filter-rejected records."""\n'
            "    if metrics is None:\n"
            "        return\n"
            "    pipeline_metrics.record_quarantine_records(\n"
            "        reason=FILTERED_OUT_SILVER,\n"
            "        count=count,\n"
            "    )\n"
            "    _record_silver_removal_accounting(\n"
            '        outcome="filtered_out",\n'
            "        reason_code=FILTERED_OUT_SILVER,\n"
            "        count=count,\n"
            "    )\n"
        ),
        (
            '    """Emit metrics for filter-rejected records.\n'
            "\n"
            "    Pipeline accounting always runs; optional MetricsPort is not required.\n"
            '    """\n'
            "    _ = metrics\n"
            "    pipeline_metrics.record_quarantine_records(\n"
            "        reason=FILTERED_OUT_SILVER,\n"
            "        count=count,\n"
            "    )\n"
            "    _record_silver_removal_accounting(\n"
            '        outcome="filtered_out",\n'
            "        reason_code=FILTERED_OUT_SILVER,\n"
            "        count=count,\n"
            "    )\n"
        ),
        "record_filtered_quarantine_metrics",
    )

    # --- #7773 mapping: module-scope import for predicate ---
    replace_once(
        ROOT / "src/bioetl/application/core/_record_normalization_mapping.py",
        ("from bioetl.domain.normalization.json import serialize_json_canonical\n"),
        (
            "from bioetl.domain.normalization.json import serialize_json_canonical\n"
            "from bioetl.domain.normalization.profiles.base import (\n"
            "    _normalizer_accepts_record_context as _profile_rule_accepts_record_context,\n"
            ")\n"
        ),
        "mapping_import",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/_record_normalization_mapping.py",
        (
            "        normalized = dict(record)\n"
            "        for field_name in tuple(normalized.keys()):\n"
            "            rule = self._profile_rule(field_name)\n"
            "            from bioetl.domain.normalization.profiles.base import (\n"
            "                _normalizer_accepts_record_context as _profile_rule_accepts_record_context,\n"
            "            )\n"
            "\n"
            "            if rule is None or not _profile_rule_accepts_record_context(\n"
            "                rule.normalizer\n"
            "            ):\n"
        ),
        (
            "        normalized = dict(record)\n"
            "        for field_name in tuple(normalized.keys()):\n"
            "            rule = self._profile_rule(field_name)\n"
            "            if rule is None or not _profile_rule_accepts_record_context(\n"
            "                rule.normalizer\n"
            "            ):\n"
        ),
        "mapping_loop_import",
    )

    # --- #7777 entity_id: always uppercase term type component ---
    replace_once(
        ROOT / "src/bioetl/application/core/entity_id.py",
        (
            "def _normalize_publication_term_identity_component(value: str) -> str:\n"
            '    """Canonicalize publication-term identity components before hashing."""\n'
            "    normalized = value.strip()\n"
            "    upper_value = normalized.upper()\n"
            "    if upper_value in PUBLICATION_TERM_TYPES:\n"
            "        return upper_value\n"
            "    return normalized\n"
        ),
        (
            "def _normalize_publication_term_identity_component(value: str) -> str:\n"
            '    """Canonicalize publication-term identity components before hashing.\n'
            "\n"
            "    Always return the trimmed uppercased value so identity hashing is case-stable\n"
            "    for known and unknown term types alike. Vocabulary membership remains a\n"
            "    validation concern outside entity-id construction.\n"
            '    """\n'
            "    return value.strip().upper()\n"
        ),
        "entity_id_term_type",
    )

    print("C3-C6 partial DONE")


if __name__ == "__main__":
    main()
