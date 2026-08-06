# Open CodeRabbit residual — CRITICAL + MAJOR (refreshed)

Live `gh` search, repo `SatoryKono/BioactivityDataAcquisition`.

| Severity | Open |
|----------|-----:|
| **critical** | **0** |
| **major** | **54** |
| **TOTAL C+M** | **54** |

## CRITICAL

_Нет открытых critical residual path-cluster issues_ (ранее #7992/#7996 и storage FK cluster закрыты).

## MAJOR (полный список по path)

- **#7795** — `src/bioetl/application/core/_base_transformer_structural_support.py`
- **#7797** — `src/bioetl/application/core/_fetch_forwarding.py`
- **#7798** — `src/bioetl/application/core/_filtered_data_source_fetch_support.py`
- **#7799** — `src/bioetl/application/core/_filtered_data_source_support.py`
- **#7772** — `src/bioetl/application/core/_quarantine_metrics_support.py`
- **#7800** — `src/bioetl/application/core/_quarantine_support.py`
- **#7801** — `src/bioetl/application/core/_quarantine_write_support.py`
- **#7802** — `src/bioetl/application/core/_record_normalization_hash_support.py`
- **#7773** — `src/bioetl/application/core/_record_normalization_mapping.py`
- **#7803** — `src/bioetl/application/core/_record_processor_span_support.py`
- **#7811** — `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`
- **#7812** — `src/bioetl/application/core/base_transformer_execution_mixin.py`
- **#7841** — `src/bioetl/application/core/config.py`
- **#7842** — `src/bioetl/application/core/data_sources`
- **#7777** — `src/bioetl/application/core/entity_id.py`
- **#7783** — `src/bioetl/application/core/lifecycle`
- **#7843** — `src/bioetl/application/core/normalization_fallbacks.py`
- **#7844** — `src/bioetl/application/core/pipeline_services.py`
- **#7760** — `src/bioetl/application/core/postrun`
- **#7784** — `src/bioetl/application/core/pre_silver_finalization_flow.py`
- **#7785** — `src/bioetl/application/core/preflight`
- **#7762** — `src/bioetl/application/core/publication_term_extraction_mixin.py`
- **#7845** — `src/bioetl/application/core/publication_term_filtering_mixin.py`
- **#7846** — `src/bioetl/application/core/publication_term_runtime.py`
- **#7847** — `src/bioetl/application/core/record_processor.py`
- **#7786** — `src/bioetl/application/core/runner.py`
- **#7848** — `src/bioetl/application/core/runner_flow_metrics.py`
- **#7787** — `src/bioetl/application/core/subcellular_fraction_support.py`
- **#7763** — `src/bioetl/application/core/wiring`
- **#7920** — `src/bioetl/domain/ports/audit.py`
- **#7904** — `src/bioetl/domain/ports/control_plane`
- **#8017** — `src/bioetl/infrastructure/observability/__init__.py`
- **#8013** — `src/bioetl/infrastructure/observability/_metrics_defs_adapter.py`
- **#8018** — `src/bioetl/infrastructure/observability/_metrics_defs_core.py`
- **#8007** — `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py`
- **#8019** — `src/bioetl/infrastructure/observability/_metrics_defs_pipeline_checkpoint.py`
- **#8020** — `src/bioetl/infrastructure/observability/_metrics_defs_storage.py`
- **#8008** — `src/bioetl/infrastructure/observability/_metrics_gateway_publication.py`
- **#8009** — `src/bioetl/infrastructure/observability/_metrics_server_state.py`
- **#8021** — `src/bioetl/infrastructure/observability/_prometheus_metric_label_normalizers.py`
- **#8022** — `src/bioetl/infrastructure/observability/_prometheus_metric_label_vocab_publication.py`
- **#8012** — `src/bioetl/infrastructure/observability/anomaly`
- **#8023** — `src/bioetl/infrastructure/observability/circuit_breaker_mapping.py`
- **#8010** — `src/bioetl/infrastructure/observability/debug_adapters.py`
- **#8024** — `src/bioetl/infrastructure/observability/logging.py`
- **#8014** — `src/bioetl/infrastructure/observability/logging_config.py`
- **#8025** — `src/bioetl/infrastructure/observability/logging_helpers.py`
- **#8011** — `src/bioetl/infrastructure/observability/metrics_collector.py`
- **#8026** — `src/bioetl/infrastructure/observability/metrics_definitions.py`
- **#8027** — `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py`
- **#8015** — `src/bioetl/infrastructure/observability/prometheus_metric_registries.py`
- **#8028** — `src/bioetl/infrastructure/observability/server.py`
- **#8016** — `src/bioetl/infrastructure/observability/tracing.py`
- **#8029** — `src/bioetl/infrastructure/observability/unified_logger.py`

## 5 независимых потоков (exclusive path ownership)

Перебалансировка после закрытий: critical / application-batch / infrastructure-storage = 0 open → 5 потоков на оставшиеся major.

```
S1 app-lifecycle-runner ──┐
S2 app-record-transform ──┼── parallel worktrees
S3 obs-metrics          ──┤
S4 obs-logging-tracing  ──┤
S5 domain               ──┘
```

| Stream | Exclusive paths | Issues | IDs |
|--------|-----------------|-------:|-----|
| **S1 app-lifecycle-runner** | `application/core` runner/lifecycle/preflight/postrun/wiring/config/… | 11 | #7760, #7763, #7777, #7783, #7784, #7785, #7786, #7787, … +3 |
| **S2 app-record-transform** | `application/core` record/quarantine/fetch/transformer/publication/… | 18 | #7762, #7772, #7773, #7795, #7797, #7798, #7799, #7800, … +10 |
| **S3 obs-metrics** | `infrastructure/observability` metrics/prometheus/server/anomaly/… | 16 | #8007, #8008, #8009, #8011, #8012, #8013, #8015, #8017, … +8 |
| **S4 obs-logging-tracing** | `infrastructure/observability` logging/tracing/debug/circuit_breaker | 7 | #8010, #8014, #8016, #8023, #8024, #8025, #8029 |
| **S5 domain** | `domain/ports/*` | 2 | #7904, #7920 |

### S1 app-lifecycle-runner (11)

- **#7760** `src/bioetl/application/core/postrun`
- **#7763** `src/bioetl/application/core/wiring`
- **#7777** `src/bioetl/application/core/entity_id.py`
- **#7783** `src/bioetl/application/core/lifecycle`
- **#7784** `src/bioetl/application/core/pre_silver_finalization_flow.py`
- **#7785** `src/bioetl/application/core/preflight`
- **#7786** `src/bioetl/application/core/runner.py`
- **#7787** `src/bioetl/application/core/subcellular_fraction_support.py`
- **#7841** `src/bioetl/application/core/config.py`
- **#7844** `src/bioetl/application/core/pipeline_services.py`
- **#7848** `src/bioetl/application/core/runner_flow_metrics.py`

### S2 app-record-transform (18)

- **#7762** `src/bioetl/application/core/publication_term_extraction_mixin.py`
- **#7772** `src/bioetl/application/core/_quarantine_metrics_support.py`
- **#7773** `src/bioetl/application/core/_record_normalization_mapping.py`
- **#7795** `src/bioetl/application/core/_base_transformer_structural_support.py`
- **#7797** `src/bioetl/application/core/_fetch_forwarding.py`
- **#7798** `src/bioetl/application/core/_filtered_data_source_fetch_support.py`
- **#7799** `src/bioetl/application/core/_filtered_data_source_support.py`
- **#7800** `src/bioetl/application/core/_quarantine_support.py`
- **#7801** `src/bioetl/application/core/_quarantine_write_support.py`
- **#7802** `src/bioetl/application/core/_record_normalization_hash_support.py`
- **#7803** `src/bioetl/application/core/_record_processor_span_support.py`
- **#7811** `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`
- **#7812** `src/bioetl/application/core/base_transformer_execution_mixin.py`
- **#7842** `src/bioetl/application/core/data_sources`
- **#7843** `src/bioetl/application/core/normalization_fallbacks.py`
- **#7845** `src/bioetl/application/core/publication_term_filtering_mixin.py`
- **#7846** `src/bioetl/application/core/publication_term_runtime.py`
- **#7847** `src/bioetl/application/core/record_processor.py`

### S3 obs-metrics (16)

- **#8007** `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py`
- **#8008** `src/bioetl/infrastructure/observability/_metrics_gateway_publication.py`
- **#8009** `src/bioetl/infrastructure/observability/_metrics_server_state.py`
- **#8011** `src/bioetl/infrastructure/observability/metrics_collector.py`
- **#8012** `src/bioetl/infrastructure/observability/anomaly`
- **#8013** `src/bioetl/infrastructure/observability/_metrics_defs_adapter.py`
- **#8015** `src/bioetl/infrastructure/observability/prometheus_metric_registries.py`
- **#8017** `src/bioetl/infrastructure/observability/__init__.py`
- **#8018** `src/bioetl/infrastructure/observability/_metrics_defs_core.py`
- **#8019** `src/bioetl/infrastructure/observability/_metrics_defs_pipeline_checkpoint.py`
- **#8020** `src/bioetl/infrastructure/observability/_metrics_defs_storage.py`
- **#8021** `src/bioetl/infrastructure/observability/_prometheus_metric_label_normalizers.py`
- **#8022** `src/bioetl/infrastructure/observability/_prometheus_metric_label_vocab_publication.py`
- **#8026** `src/bioetl/infrastructure/observability/metrics_definitions.py`
- **#8027** `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py`
- **#8028** `src/bioetl/infrastructure/observability/server.py`

### S4 obs-logging-tracing (7)

- **#8010** `src/bioetl/infrastructure/observability/debug_adapters.py`
- **#8014** `src/bioetl/infrastructure/observability/logging_config.py`
- **#8016** `src/bioetl/infrastructure/observability/tracing.py`
- **#8023** `src/bioetl/infrastructure/observability/circuit_breaker_mapping.py`
- **#8024** `src/bioetl/infrastructure/observability/logging.py`
- **#8025** `src/bioetl/infrastructure/observability/logging_helpers.py`
- **#8029** `src/bioetl/infrastructure/observability/unified_logger.py`

### S5 domain (2)

- **#7904** `src/bioetl/domain/ports/control_plane`
- **#7920** `src/bioetl/domain/ports/audit.py`

## Правила параллелизма

1. Один worktree/agent на stream; **path ownership не пересекается**.
2. S1 и S2 оба под `application/core/` — **разные файлы**; не править «чужие».
3. S3 и S4 оба под `observability/` — **разные файлы**.
4. S5 domain — 2 issue; можно закрыть быстро или прицепить к S4 (paths всё равно exclusive).
5. Не увеличивать бюджеты техдолга.
6. После PR: close issue + evidence; пересчёт inventory.
