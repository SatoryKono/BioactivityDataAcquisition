# Open CodeRabbit residual — CRITICAL + MAJOR

Live `gh` snapshot, repo `SatoryKono/BioactivityDataAcquisition`.

| Class | Open |
|-------|-----:|
| **critical path-cluster** | **0** |
| **major path-cluster** | **29** |
| **TOTAL C+M path-clusters** | **29** |

## CRITICAL path-clusters

_Нет открытых critical residual path-cluster issues._

## MAJOR path-clusters (полный список)

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

## Campaign / meta open (не path-cluster implement)

- **#7688** — [CR-FULL][meta] Exhaustive CodeRabbit residual audit campaign (2026-08)
- **#7946** — [CR-FULL][Wave A][P2] Retry rate-limited domain residual leaves
- **#8031** — [CR-FULL][Wave E][P2] CLI residual blocked: docs/grafana/scripts All files ignored
- **#8032** — [CR-FULL][Wave F][P2] CLI residual blocked: tests All files ignored

## 5 независимых потоков (exclusive path ownership)

Все major path-clusters сейчас под `src/bioetl/application/core/*`.
Critical / domain / observability / storage path-clusters закрыты.

```
S1 lifecycle-runner       ──┐
S2 config-services        ──┼── parallel worktrees
S3 record-quarantine-fetch──┤
S4 transformer            ──┤
S5 publication            ──┘
```

| Stream | Exclusive paths | Issues | IDs |
|--------|-----------------|-------:|-----|
| **S1 lifecycle-runner** | `postrun, wiring, lifecycle, preflight, runner, pre_silver, runner_flow_metrics` | 7 | #7760, #7763, #7783, #7784, #7785, #7786, #7848 |
| **S2 config-services** | `config.py, pipeline_services.py, entity_id.py, subcellular_fraction_support.py` | 4 | #7777, #7787, #7841, #7844 |
| **S3 record-quarantine-fetch** | `record_*, quarantine_*, fetch_*, filtered_*, data_sources, normalization_*` | 12 | #7772, #7773, #7797, #7798, #7799, #7800, #7801, #7802, #7803, #7842, #7843, #7847 |
| **S4 transformer** | `base_transformer*` | 3 | #7795, #7811, #7812 |
| **S5 publication** | `publication_term_*` | 3 | #7762, #7845, #7846 |

### S1 lifecycle-runner (7)

- **#7760** `src/bioetl/application/core/postrun`
- **#7763** `src/bioetl/application/core/wiring`
- **#7783** `src/bioetl/application/core/lifecycle`
- **#7784** `src/bioetl/application/core/pre_silver_finalization_flow.py`
- **#7785** `src/bioetl/application/core/preflight`
- **#7786** `src/bioetl/application/core/runner.py`
- **#7848** `src/bioetl/application/core/runner_flow_metrics.py`

### S2 config-services (4)

- **#7777** `src/bioetl/application/core/entity_id.py`
- **#7787** `src/bioetl/application/core/subcellular_fraction_support.py`
- **#7841** `src/bioetl/application/core/config.py`
- **#7844** `src/bioetl/application/core/pipeline_services.py`

### S3 record-quarantine-fetch (12)

- **#7772** `src/bioetl/application/core/_quarantine_metrics_support.py`
- **#7773** `src/bioetl/application/core/_record_normalization_mapping.py`
- **#7797** `src/bioetl/application/core/_fetch_forwarding.py`
- **#7798** `src/bioetl/application/core/_filtered_data_source_fetch_support.py`
- **#7799** `src/bioetl/application/core/_filtered_data_source_support.py`
- **#7800** `src/bioetl/application/core/_quarantine_support.py`
- **#7801** `src/bioetl/application/core/_quarantine_write_support.py`
- **#7802** `src/bioetl/application/core/_record_normalization_hash_support.py`
- **#7803** `src/bioetl/application/core/_record_processor_span_support.py`
- **#7842** `src/bioetl/application/core/data_sources`
- **#7843** `src/bioetl/application/core/normalization_fallbacks.py`
- **#7847** `src/bioetl/application/core/record_processor.py`

### S4 transformer (3)

- **#7795** `src/bioetl/application/core/_base_transformer_structural_support.py`
- **#7811** `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`
- **#7812** `src/bioetl/application/core/base_transformer_execution_mixin.py`

### S5 publication (3)

- **#7762** `src/bioetl/application/core/publication_term_extraction_mixin.py`
- **#7845** `src/bioetl/application/core/publication_term_filtering_mixin.py`
- **#7846** `src/bioetl/application/core/publication_term_runtime.py`

## Правила параллелизма

1. Один worktree/agent на stream; path ownership не пересекается.
2. Все потоки под `application/core/` — разные файлы.
3. Не увеличивать бюджеты техдолга.
4. Meta issues (#7688, #7946, #8031, #8032) — не в implement-streams.
5. После PR: close + evidence; пересчёт inventory.
