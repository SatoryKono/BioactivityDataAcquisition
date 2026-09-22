# cast(Any) typing census

Linked issue: #10596 (AUD-006). Schema: `cast-any-typing-census-v1`.

Justified markers: `PD3`, `PD6`, `TYPE-002`, `Any: mixin host`, `Any: host attr`, `Any: JSON`, `as_mixin_host(`.

- total_cast_any_count: 382
- justified_count: 240
- unjustified_count: 142
- file_count: 117

## By category

| Category | Count |
| --- | ---: |
| `pd3_host_attr_default` | 131 |
| `pd6_host_attr_default` | 90 |
| `type_002_policy` | 0 |
| `any_mixin_host` | 3 |
| `any_host_attr` | 16 |
| `any_json` | 0 |
| `as_mixin_host_call` | 0 |
| `unjustified` | 142 |

## By layer

| Layer | Total | Unjustified |
| --- | ---: | ---: |
| `application` | 189 | 67 |
| `composition` | 22 | 8 |
| `domain` | 12 | 2 |
| `infrastructure` | 156 | 64 |
| `interfaces` | 3 | 1 |

## Unjustified by sub-bucket (triage only)

| Sub-bucket | Count |
| --- | ---: |
| `pd4_host_default_pending_protocol` | 71 |
| `free_form_reason` | 70 |
| `no_reason_tag` | 1 |

## Top files

| Path | Total | Justified | Unjustified |
| --- | ---: | ---: | ---: |
| `src/bioetl/application/services/quality/data_quality_anomalies.py` | 11 | 0 | 11 |
| `src/bioetl/infrastructure/storage/gold/metadata_mixin.py` | 11 | 0 | 11 |
| `src/bioetl/infrastructure/storage/bronze/side_effects_mixin.py` | 8 | 0 | 8 |
| `src/bioetl/infrastructure/storage/silver/operations/metadata_context_facade.py` | 8 | 0 | 8 |
| `src/bioetl/application/composite/merger_io_mixin.py` | 6 | 0 | 6 |
| `src/bioetl/application/services/quality/dq_report_generation_mixin.py` | 6 | 0 | 6 |
| `src/bioetl/application/composite/merger_output_mixin.py` | 5 | 0 | 5 |
| `src/bioetl/application/core/batch_writer_tracing_mixin.py` | 5 | 0 | 5 |
| `src/bioetl/infrastructure/storage/gold/read_cleanup_mixin.py` | 5 | 0 | 5 |
| `src/bioetl/application/services/medallion/medallion_lifecycle.py` | 4 | 0 | 4 |
| `src/bioetl/infrastructure/quality/exemptions_registry.py` | 4 | 0 | 4 |
| `src/bioetl/application/composite/join_planner_delegation_mixin.py` | 3 | 0 | 3 |
| `src/bioetl/application/core/postrun/_failure_policy.py` | 3 | 0 | 3 |
| `src/bioetl/application/services/export_lineage/export_execution.py` | 3 | 0 | 3 |
| `src/bioetl/infrastructure/observability/observability_backend_process.py` | 3 | 0 | 3 |
| `src/bioetl/application/composite/helpers/dependency_chained_key_resolver.py` | 2 | 0 | 2 |
| `src/bioetl/application/composite/merger_metrics_mixin.py` | 2 | 0 | 2 |
| `src/bioetl/application/core/batch_writer_columns_mixin.py` | 2 | 0 | 2 |
| `src/bioetl/application/services/ops/health_service.py` | 2 | 0 | 2 |
| `src/bioetl/application/workflow/transforms/reconcile_foreign_keys.py` | 2 | 0 | 2 |
| `src/bioetl/composition/services/versioning.py` | 2 | 0 | 2 |
| `src/bioetl/infrastructure/adapters/decorators/_circuit_breaker_snapshot.py` | 2 | 0 | 2 |
| `src/bioetl/infrastructure/export/debug_export_ops.py` | 2 | 0 | 2 |
| `src/bioetl/infrastructure/storage/gold/writer_metrics.py` | 2 | 0 | 2 |
| `src/bioetl/infrastructure/storage/lineage_persistence.py` | 2 | 0 | 2 |

## Unjustified free-form reason tags

| Reason | Count |
| --- | ---: |
| `host default (PD4)` | 71 |
| `dynamic compat patch target` | 4 |
| `Windows STARTUPINFO duck-type` | 3 |
| `export port accepts Arrow/table duck-type` | 3 |
| `pyarrow Table after read boundary` | 3 |
| `pyarrow.Table returned via executor is untyped to mypy` | 3 |
| `DeltaTable runtime type has no complete type stubs` | 2 |
| `external mutation summary compatibility` | 2 |
| `gold write request duck-type` | 2 |
| `lineage bundle duck-type` | 2 |
| `reconciliation mutation helper uses structural host` | 2 |
| `structural FK reconcile result port` | 2 |
| `CSV exporter Arrow table duck-type` | 1 |
| `DQ metrics .dict() duck-type` | 1 |
| `asdict over caller-guaranteed dataclass` | 1 |
| `builder protocol compatibility` | 1 |
| `cast for nullable numeric coercion` | 1 |
| `concrete BatchWriter supplies the host context` | 1 |
| `concrete host injects an optional async validator` | 1 |
| `concrete host supplies the classifier` | 1 |
| `concrete host supplies the metrics recorder` | 1 |
| `delta schema boundary` | 1 |
| `duck-type model_dump on config object` | 1 |
| `duck-type version attr on config object` | 1 |
| `duck-typed Pandera schema class` | 1 |
| `duck-typed async HTTP client context` | 1 |
| `duck-typed async context manager` | 1 |
| `duck-typed lineage fragment without CP import` | 1 |
| `dynamic provider class attribute` | 1 |
| `export writer accepts Arrow table duck-type` | 1 |
| `factory schema Protocol→concrete` | 1 |
| `heterogeneous factory config union` | 1 |
| `heterogeneous schema adapter` | 1 |
| `host method duck-type` | 1 |
| `inspect accepts arbitrary callables` | 1 |
| `legacy breaker attribute` | 1 |
| `legacy breaker duck type` | 1 |
| `openpyxl Workbook duck-type` | 1 |
| `openpyxl Worksheet duck-type` | 1 |
| `optional column-order service` | 1 |
| `optional substance field` | 1 |
| `payload = dict(vars(ctx))` | 1 |
| `phased postrun methods are supplied by mixins` | 1 |
| `pyarrow StructType lacks __iter__ in stubs` | 1 |
| `pyarrow Table after isinstance gate` | 1 |
| `pyarrow dataset duck-type` | 1 |
| `pydantic model_dump duck-type` | 1 |
| `pydantic narrowing at runtime` | 1 |
| `runtime config mapping unpack` | 1 |
| `schema columns duck-type` | 1 |
| `structural boundary cast` | 1 |
| `structural host callback` | 1 |
| `structural to_dict duck-type` | 1 |
| `tracing port returns an OTel-compatible runtime object` | 1 |
