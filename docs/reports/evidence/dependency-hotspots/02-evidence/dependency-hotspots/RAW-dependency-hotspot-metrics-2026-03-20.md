# Raw Dependency Hotspot Metrics

Date: 2026-03-20

## Method

- Scope: `src/bioetl/**/*.py`
- Size metric: filesystem bytes (`st_size`)
- LOC metric: file line count from current working tree text content
- Thresholds:
  - size hotspot: `>10 KB` (`>10240` bytes)
  - LOC hotspot: `>350 LOC`

These counts are independent from the generated dependency map, which uses its own module scan logic.

## Summary Counts

| Metric | Count |
|---|---:|
| Total Python files under `src/bioetl` | 1198 |
| Files `>10 KB` | 95 |
| Files `>350 LOC` | 17 |
| Files exceeding both thresholds | 17 |

## Layer Distribution

### Files `>10 KB`

| Layer | Count |
|---|---:|
| `infrastructure` | 42 |
| `application` | 31 |
| `composition` | 12 |
| `domain` | 6 |
| `interfaces` | 4 |

### Files `>350 LOC`

| Layer | Count |
|---|---:|
| `infrastructure` | 12 |
| `application` | 3 |
| `interfaces` | 2 |

## Package Distribution for Overlap Set (`>10 KB` and `>350 LOC`)

| Package Prefix | Count |
|---|---:|
| `src/bioetl/infrastructure/adapters` | 7 |
| `src/bioetl/application/pipelines` | 2 |
| `src/bioetl/infrastructure/storage` | 2 |
| `src/bioetl/interfaces/cli` | 2 |
| `src/bioetl/application/services` | 1 |
| `src/bioetl/infrastructure/config` | 1 |
| `src/bioetl/infrastructure/quality` | 1 |
| `src/bioetl/infrastructure/schemas` | 1 |

## Top Files by Size (`>10 KB`)

| File | Bytes | LOC | Layer | Package Prefix |
|---|---:|---:|---|---|
| `src/bioetl/infrastructure/schemas/silver_publications.py` | 17131 | 341 | `infrastructure` | `src/bioetl/infrastructure/schemas` |
| `src/bioetl/infrastructure/schemas/silver_chembl_core.py` | 16735 | 366 | `infrastructure` | `src/bioetl/infrastructure/schemas` |
| `src/bioetl/infrastructure/adapters/crossref/batch.py` | 14792 | 445 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py` | 13789 | 407 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/adapters/health_check_mixin.py` | 13354 | 404 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/config/_base.py` | 13204 | 361 | `infrastructure` | `src/bioetl/infrastructure/config` |
| `src/bioetl/application/core/_filtered_data_source_mixins.py` | 13114 | 343 | `application` | `src/bioetl/application/core` |
| `src/bioetl/composition/factories/pipeline/configs.py` | 13101 | 326 | `composition` | `src/bioetl/composition/factories` |
| `src/bioetl/infrastructure/storage/base_delta_writer.py` | 12868 | 365 | `infrastructure` | `src/bioetl/infrastructure/storage` |
| `src/bioetl/application/pipelines/pubmed/blocks.py` | 12821 | 349 | `application` | `src/bioetl/application/pipelines` |
| `src/bioetl/interfaces/cli/commands/domains/run/command.py` | 12798 | 412 | `interfaces` | `src/bioetl/interfaces/cli` |
| `src/bioetl/application/services/dq/silver_statistics_helpers.py` | 12795 | 373 | `application` | `src/bioetl/application/services` |
| `src/bioetl/application/pipelines/uniprot/transformer_business_data_mixin.py` | 12592 | 286 | `application` | `src/bioetl/application/pipelines` |
| `src/bioetl/infrastructure/quality/_governance_validation.py` | 12591 | 371 | `infrastructure` | `src/bioetl/infrastructure/quality` |
| `src/bioetl/application/core/runner.py` | 12579 | 309 | `application` | `src/bioetl/application/core` |

## Top Files by LOC (`>350 LOC`)

| File | Bytes | LOC | Layer | Package Prefix |
|---|---:|---:|---|---|
| `src/bioetl/infrastructure/adapters/crossref/batch.py` | 14792 | 445 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/interfaces/cli/commands/domains/run/command.py` | 12798 | 412 | `interfaces` | `src/bioetl/interfaces/cli` |
| `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py` | 13789 | 407 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/adapters/health_check_mixin.py` | 13354 | 404 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/storage/gold/io_delta_mixins.py` | 12496 | 397 | `infrastructure` | `src/bioetl/infrastructure/storage` |
| `src/bioetl/application/pipelines/pubmed/extractors/date.py` | 12205 | 384 | `application` | `src/bioetl/application/pipelines` |
| `src/bioetl/application/services/dq/silver_statistics_helpers.py` | 12795 | 373 | `application` | `src/bioetl/application/services` |
| `src/bioetl/infrastructure/quality/_governance_validation.py` | 12591 | 371 | `infrastructure` | `src/bioetl/infrastructure/quality` |
| `src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py` | 11695 | 367 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/adapters/error_handling.py` | 11532 | 367 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/adapters/http/health_monitor.py` | 11999 | 367 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/infrastructure/schemas/silver_chembl_core.py` | 16735 | 366 | `infrastructure` | `src/bioetl/infrastructure/schemas` |
| `src/bioetl/infrastructure/storage/base_delta_writer.py` | 12868 | 365 | `infrastructure` | `src/bioetl/infrastructure/storage` |
| `src/bioetl/application/pipelines/uniprot/extractors/_comment_facets.py` | 11483 | 363 | `application` | `src/bioetl/application/pipelines` |
| `src/bioetl/infrastructure/config/_base.py` | 13204 | 361 | `infrastructure` | `src/bioetl/infrastructure/config` |
| `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py` | 11060 | 360 | `infrastructure` | `src/bioetl/infrastructure/adapters` |
| `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py` | 10852 | 354 | `interfaces` | `src/bioetl/interfaces/cli` |
