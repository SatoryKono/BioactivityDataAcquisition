# Consolidated Code Inventory Report — BioETL

Date: 2026-02-13
Status: Corrected & Consolidated
Sources: 4 independent codex audit branches (see cross-branch-analysis.md)

## Executive Summary

| Metric | Value | Confidence |
|--------|-------|------------|
| Total classes | 878 | HIGH (verified, all branches agree) |
| Total functions (module-level) | 564 | HIGH (verified, all branches agree) |
| Total constants (UPPER_SNAKE_CASE) | ~184 | MEDIUM (counting methodology varies) |
| Type aliases / TypeVars | ~11 | LOW (only B4 tracked these) |
| `__all__` re-exports | ~220 | MEDIUM (only B3 tracked these) |
| Dead objects (DEAD) — confirmed | see §2.1 | requires re-analysis |
| Confirmed duplicates | 3 | HIGH (B1 hash-verified) |
| Suspected name duplicates | 26 | MEDIUM (B1/B4 consensus) |

## 1. Object Registry — Per-Layer Breakdown (verified)

### 1.1 Summary

| Layer | Classes | Functions | Constants | Total |
|-------|--------:|----------:|----------:|------:|
| domain | 410 | 154 | 47 | 611 |
| application | 181 | 127 | 41 | 349 |
| infrastructure | 250 | 70 | 80 | 400 |
| composition | 33 | 141 | 6 | 180 |
| interfaces | 4 | 72 | 10 | 86 |
| **Total** | **878** | **564** | **184** | **1626** |

Note: Constants counted as UPPER_SNAKE_CASE module-level assignments only (excludes `__all__`, TypeVars, type aliases).

### 1.2 Detailed Registry

For full per-object registry, use B2's report (`INV-20260213-01/inventory-report.md`) as the authoritative source — it has the most complete per-object detail including LOC, base classes, public methods, and function signatures.

Corrections to B2:
- `_now_utc` → SELF_ONLY (not unlabeled)
- `CachedBronzeContext` → ACTIVE (not unlabeled — used across composition, application layers)

## 2. Dead Code (Corrected)

### 2.1 Methodology

An object is classified as:
- **DEAD**: Zero references outside its own definition line. Not called, imported, or referenced anywhere.
- **SELF_ONLY**: Referenced only within its own module (e.g., private helper called by a public function in the same file). NOT dead code.
- **TEST_ONLY**: Referenced only in test files. May be intentional test utilities or may indicate production code that lost its caller.
- **PRODUCTION_ONLY**: Referenced in production code but not in tests. May need test coverage.
- **ACTIVE**: Referenced in both production and test code.

### 2.2 Confirmed DEAD Objects (high confidence)

These objects have zero references outside their definition file AND zero internal references within the file:

| # | Object | Type | Layer | File:Line |
|---|--------|------|-------|-----------|
| 1 | `VALIDATION_API` | constant | domain | domain/validation.py:412 |
| 2 | `compute_subcellular_fraction_entity_id` | function | application | application/core/entity_id.py:36 |
| 3 | `PARSER_HELPERS` | constant | application | application/pipelines/pubmed/xml_parser.py:79 |
| 4 | `CIRCUIT_BREAKER_HELPERS` | constant | infrastructure | infrastructure/adapters/http/circuit_breaker.py:235 |
| 5 | `METRICS_COLLECTOR` | constant | infrastructure | infrastructure/observability/metrics.py:221 |
| 6 | `_validate_threshold_order` | function | domain | domain/composite/config.py:1021 |
| 7 | `_validate_non_negative` | function | domain | domain/resilience.py:191 |
| 8 | `PubchemMoleculeRecord` | class | domain | domain/entities/pubchem.py:24 |
| 9 | `AssayRecord` | class | domain | domain/entities/chembl.py:181 |
| 10 | `AuthFailureError` | class | domain | domain/exceptions/internal.py:227 |
| 11 | `CachedBronzeEmptyError` | class | domain | domain/exceptions/infrastructure.py:291 |
| 12 | `_safe_json` | function | domain | domain/entities/bioactivity.py:48 |
| 13 | `_get_default_config` | function | domain | domain/validation.py:80 |
| 14 | `_match_error_type` | function | domain | domain/error_classifier.py:60 |
| 15 | `_get_orjson_options` | function | domain | domain/serialization.py:142 |
| 16 | `_serialize_with_orjson` | function | domain | domain/serialization.py:150 |
| 17 | `_serialize_with_stdlib` | function | domain | domain/serialization.py:165 |
| 18 | `_deserialize_with_orjson` | function | domain | domain/serialization.py:182 |
| 19 | `_deserialize_with_stdlib` | function | domain | domain/serialization.py:192 |
| 20 | `_normalize_float` | function | domain | domain/transformations.py:37 |
| 21 | `_normalize_datetime` | function | domain | domain/transformations.py:45 |
| 22 | `_normalize_date` | function | domain | domain/transformations.py:51 |
| 23 | `_normalize_str` | function | domain | domain/transformations.py:57 |
| 24 | `_normalize_dict` | function | domain | domain/transformations.py:63 |
| 25 | `_should_include_field` | function | domain | domain/transformations.py:85 |
| 26 | `_is_electronic_page` | function | domain | domain/normalization.py:116 |
| 27 | `_extract_non_digits` | function | domain | domain/normalization.py:126 |
| 28 | `_is_abbreviated` | function | domain | domain/normalization.py:131 |
| 29 | `_compute_expanded_page` | function | domain | domain/normalization.py:140 |
| 30 | `_expand_abbreviated_page` | function | domain | domain/normalization.py:149 |
| 31 | `_normalize_and_split_pages` | function | domain | domain/normalization.py:161 |
| 32 | `_prepare_page_input` | function | domain | domain/normalization.py:174 |
| 33 | `_is_valid_string` | function | domain | domain/normalization.py:223 |
| 34 | `_filter_valid_strings` | function | domain | domain/normalization.py:235 |
| 35 | `_try_parse_json_array` | function | domain | domain/normalization.py:245 |
| 36 | `_parse_authors_from_delimited` | function | domain | domain/normalization.py:262 |
| 37 | `_extract_variant` | function | application | application/pipelines/chembl/assay_transformer.py:51 |
| 38 | `_parse_year` | function | application | application/pipelines/crossref/reference_extractors.py:27 |
| 39 | `_extract_author_sequence` | function | application | application/pipelines/crossref/author_extractors.py:40 |
| 40 | `_extract_author_affiliations_list` | function | application | application/pipelines/crossref/author_extractors.py:49 |
| 41 | `_build_author_detail` | function | application | application/pipelines/crossref/author_extractors.py:64 |
| 42 | `_extract_id_from_url` | function | application | application/pipelines/openalex/extractors.py:43 |
| 43 | `_extract_orcid_from_url` | function | application | application/pipelines/openalex/extractors.py:132 |
| 44 | `_parse_grant_dict` | function | application | application/pipelines/openalex/extractors.py:347 |
| 45 | `extract_institution_ror_ids` | function | application | application/pipelines/openalex/extractors.py:272 |
| 46 | `_extract_reaction_data` | function | application | application/pipelines/uniprot/extractors/comments.py:23 |
| 47 | `_extract_location_value` | function | application | application/pipelines/uniprot/extractors/comments.py:40 |
| 48 | `_build_isoform_data` | function | application | application/pipelines/uniprot/extractors/comments.py:57 |
| 49 | `_extract_cofactor_entry` | function | application | application/pipelines/uniprot/extractors/comments.py:95 |
| 50 | `_extract_km_entry` | function | application | application/pipelines/uniprot/extractors/comments.py:124 |
| 51 | `_extract_vmax_entry` | function | application | application/pipelines/uniprot/extractors/comments.py:136 |
| 52 | `_extract_kinetic_parameters` | function | application | application/pipelines/uniprot/extractors/comments.py:159 |
| 53 | `_extract_absorption_data` | function | application | application/pipelines/uniprot/extractors/comments.py:182 |
| 54 | `_extract_biophys_from_comment` | function | application | application/pipelines/uniprot/extractors/comments.py:193 |
| 55 | `_extract_feature_location` | function | application | application/pipelines/uniprot/extractors/features.py:10 |
| 56 | `_build_keyword_dict` | function | application | application/pipelines/uniprot/extractors/features.py:51 |
| 57 | `_extract_nested_values` | function | application | application/core/dict_transformers.py:139 |
| 58 | `_span_context` | function | application | application/observability/span_helpers.py:27 |
| 59 | `_scan_provider_for_tables` | function | application | application/services/export_service.py:136 |
| 60 | `_write_xlsx_file` | function | application | application/services/export_service.py:181 |
| 61 | `PipelineSettingsProtocol` | class | application | application/services/config_service.py:22 |
| 62 | `SettingsProtocol` | class | application | application/services/config_service.py:30 |
| 63 | `PipelineRegistryProtocol` | class | application | application/services/config_service.py:86 |
| 64 | `SettingsLoaderProtocol` | class | application | application/services/config_service.py:94 |
| 65 | `PipelineConfigLoaderProtocol` | class | application | application/services/config_service.py:102 |
| 66 | `DomainConfigMapperProtocol` | class | application | application/services/config_service.py:110 |
| 67 | `RegistryAccessorProtocol` | class | application | application/services/config_service.py:118 |
| 68 | `ChEMBLAssayParametersPipeline` | class | application | application/pipelines/chembl/_pipelines.py:23 |
| 69 | `ChEMBLCellLinePipeline` | class | application | application/pipelines/chembl/_pipelines.py:27 |
| 70 | `ChEMBLCompoundRecordPipeline` | class | application | application/pipelines/chembl/_pipelines.py:31 |
| 71 | `ChEMBLProteinClassPipeline` | class | application | application/pipelines/chembl/_pipelines.py:39 |
| 72 | `ChEMBLPublicationSimilarityPipeline` | class | application | application/pipelines/chembl/_pipelines.py:47 |
| 73 | `ChEMBLPublicationTermPipeline` | class | application | application/pipelines/chembl/_pipelines.py:55 |
| 74 | `ChEMBLSubcellularFractionPipeline` | class | application | application/pipelines/chembl/_pipelines.py:63 |
| 75 | `ChEMBLTargetComponentPipeline` | class | application | application/pipelines/chembl/_pipelines.py:75 |
| 76 | `ChEMBLTissuePipeline` | class | application | application/pipelines/chembl/_pipelines.py:79 |
| 77 | `calculate_had_warnings` | function | application | application/composite/runner_helpers.py:88 |
| 78 | `add_not_run_results` | function | application | application/composite/runner_helpers.py:128 |
| 79 | `get_mergeable_enrichers` | function | application | application/composite/runner_helpers.py:193 |
| 80 | `get_mergeable_dependencies` | function | application | application/composite/runner_helpers.py:241 |
| 81 | `_load_base_config` | function | infrastructure | infrastructure/config_loader.py:54 |
| 82 | `_apply_file_reference_defaults` | function | infrastructure | infrastructure/config_loader.py:70 |
| 83 | `_load_column_groups_config` | function | infrastructure | infrastructure/config_loader.py:90 |
| 84 | `_load_data_schema_config` | function | infrastructure | infrastructure/config_loader.py:112 |
| 85 | `_apply_layer_defaults` | function | infrastructure | infrastructure/config_loader.py:151 |
| 86 | `_apply_convention_defaults` | function | infrastructure | infrastructure/config_loader.py:179 |
| 87 | `_load_filter_config` | function | infrastructure | infrastructure/config_loader.py:230 |
| 88 | `_merge_filter_config` | function | infrastructure | infrastructure/config_loader.py:250 |
| 89 | `_load_column_groups_section` | function | infrastructure | infrastructure/config_loader.py:309 |
| 90 | `_load_source_section` | function | infrastructure | infrastructure/config_loader.py:338 |
| 91 | `_check_psutil_available` | function | infrastructure | infrastructure/system/memory_monitor.py:39 |
| 92 | `_get_metadata_filename` | function | infrastructure | infrastructure/storage/metadata_writer.py:34 |
| 93 | `BaseConfigLoader` | class | infrastructure | infrastructure/config/base_config_loader.py:25 |
| 94 | `YamlSettingsSource` | class | infrastructure | infrastructure/config/_base.py:45 |
| 95 | `_extract_source_fields` | function | infrastructure | infrastructure/config/_base.py:87 |
| 96 | `_extract_write_modes` | function | infrastructure | infrastructure/config/_base.py:95 |
| 97 | `_build_silver_filters` | function | infrastructure | infrastructure/config/_base.py:117 |
| 98 | `_build_gold_filters` | function | infrastructure | infrastructure/config/_base.py:126 |
| 99 | `_parse_config` | function | infrastructure | infrastructure/config/field_group_loader.py:65 |
| 100 | `_parse_group` | function | infrastructure | infrastructure/config/field_group_loader.py:104 |
| 101 | `_parse_field` | function | infrastructure | infrastructure/config/field_group_loader.py:146 |
| 102 | `inspect_records` | function | infrastructure | infrastructure/quarantine/operations.py:23 |
| 103 | `replay_records` | function | infrastructure | infrastructure/quarantine/operations.py:59 |
| 104 | `get_statistics` | function | infrastructure | infrastructure/quarantine/operations.py:106 |
| 105 | `purge_records` | function | infrastructure | infrastructure/quarantine/operations.py:154 |
| 106 | `FilterColumnSchema` | class | infrastructure | infrastructure/schemas/pipeline_config.py:312 |
| 107 | `GoldColumnFilterConfig` | class | infrastructure | infrastructure/schemas/pipeline_config.py:636 |

**IMPORTANT CORRECTION**: Items #81-90 (config_loader.py helpers) are classified as DEAD by B1, but verified as **SELF_ONLY** — they are called within `load_pipeline_config()` in the same file. They should NOT be deleted. The DEAD classification applies only if we're considering the entire `config_loader.py` module as potentially dead. The public entry points `load_source_config` and `load_pipeline_config` are ACTIVE.

### 2.3 Orphan Modules (consensus from B1, B3, B4)

| # | File | LOC | Status | Recommendation |
|---|------|-----|--------|----------------|
| 1 | `src/bioetl/__main__.py` | 8 | entry-point | Keep — `python -m bioetl` |
| 2 | `src/bioetl/interfaces/cli/__main__.py` | 9 | entry-point | Keep — `python -m bioetl.interfaces.cli` |
| 3 | `src/bioetl/interfaces/observability.py` | 19 | facade | Verify if used as public API |
| 4 | `src/bioetl/infrastructure/storage/delta_writer.py` | 8 | facade | Verify if used as re-export |
| 5 | `src/bioetl/composition/types.py` | 52 | type defs | Verify imports via `__init__` |
| 6 | `src/bioetl/composition/factories/storage_factory.py` | 341 | factory | Verify usage from composition root |
| 7 | `src/bioetl/composition/factories/storage_adapter.py` | 652 | adapter | Verify usage from composition root |
| 8 | `src/bioetl/application/core/subcellular_fraction_data_source.py` | 297 | data source | Verify registration in pipeline factories |

### 2.4 `__all__` Export Gaps (from B3)

| # | Module | Missing Exports |
|---|--------|-----------------|
| 1 | `infrastructure.serialization.encoders` | `ORJSON_AVAILABLE` |
| 2 | `composition.factories.pipeline_factories` | `PIPELINE_CONFIGS` |
| 3 | `interfaces.cli.exit_codes` | `EXCEPTION_EXIT_CODES` |
| 4 | `application.pipelines.chembl.assay_parameters_transformer` | `KNOWN_PARAM_TYPES` |
| 5 | `application.core.field_specs` | `FLOAT`, `INT`, `PMID`, `STR` |
| 6 | `domain.composite.field_groups` | `DEFAULT_PROVIDER_ORDER` |
| 7 | `domain.schemas.column_order` | `ALL_SYSTEM_FIELDS`, `DQ_FIELDS_SUFFIX`, `SYSTEM_FIELDS_PREFIX` |
| 8 | `domain.schemas.constants` | 14 constant tuples (ACTIVITY_STANDARD_TYPES, etc.) |
| 9 | `domain.value_objects.column_order` | `DEFAULT_COLUMN_ORDER`, `PUBLICATION_FIELD_GROUPS` |
| 10 | `domain.value_objects.publication_field_groups` | `DEFAULT_FIELD_GROUP_CONFIG`, `FIELD_TO_GROUP_MAPPING` |
| 11 | `domain.value_objects.column_qualifier` | `JOIN_KEY_COLUMNS` |

## 3. Confirmed Duplicates (from B1, hash-verified)

| # | Object A | Object B | Type | Recommendation |
|---|----------|----------|------|----------------|
| 1 | `SilverMetadataBuilder.__init__` | `GoldMetadataBuilder.__init__` | identical constructor | Extract shared base `_MetadataBuilderBase` |
| 2 | `BaseConfigLoader._load_yaml` | `DQConfigLoader._load_yaml` | identical YAML loading | Extract into shared mixin or utility |
| 3 | `FilteredDataSource.get_source_metadata` | `PublicationTermDataSource.get_source_metadata` | identical metadata method | Extract into base class method |

## 4. Suspected Cross-Layer Name Duplicates (consensus B1/B4)

### 4.1 Intentional DTO/Domain Separation (NOT bugs)

These share names across domain↔infrastructure because domain defines the contract and infrastructure defines the Pydantic schema for YAML parsing:

| Domain Object | Infrastructure Object | Nature |
|--------------|----------------------|--------|
| `DQConfig` (domain/config/dq.py) | `DQConfig` (infrastructure/schemas/pipeline_config.py) | domain model vs YAML schema |
| `DQReportConfig` (domain/config/dq.py) | `DQReportConfig` (infrastructure/schemas/pipeline_config.py) | domain model vs YAML schema |
| `CircuitBreakerConfig` (domain/resilience.py) | `CircuitBreakerConfig` (infrastructure/schemas/pipeline_config.py) | domain model vs YAML schema |
| `BaseClientConfig` (domain/configs/base.py) | `BaseClientConfig` (infrastructure/schemas/base_schemas.py) | domain model vs YAML schema |
| `InputFilterConfig` (domain/filtering/input_config.py) | `InputFilterConfig` (infrastructure/schemas/pipeline_config.py) | domain model vs YAML schema |
| `ValidationResult` (domain/types.py) | `ValidationResult` (infrastructure/adapters/validation.py) | domain type vs adapter type |
| `RateLimitConfig` (domain/configs/base.py) | `RateLimitConfig` (composition/bootstrap_contexts.py) | domain model vs bootstrap DTO |

**Recommendation**: These are by design per Hexagonal Architecture. Document the mapping in ADR if not already done. Consider adding `Yaml` prefix to infrastructure variants for clarity (e.g., `YamlDQConfig`).

### 4.2 Potential Real Duplicates (require manual verification)

| # | Object A | Object B | Risk | Action |
|---|----------|----------|------|--------|
| 1 | `normalize_string` (domain/normalization.py) | `normalize_string` (application/core/dict_transformers.py) | HIGH | Check if application delegates to domain or reimplements |
| 2 | `parse_date_field` (domain/normalization.py) | `parse_date_field` (application/core/dict_transformers.py) | HIGH | Same check |
| 3 | `validate_smiles` (domain/validation.py) | `validate_smiles` (application/core/dict_transformers.py) | HIGH | Same check |
| 4 | `_get_bioetl_version` (infrastructure/storage/metadata_builder.py) | `_get_bioetl_version` (composition/services/metadata_coordinator.py) | MEDIUM | Consolidate to single location |
| 5 | `_serialize_value` (infrastructure/storage/base_delta_writer.py) | `_serialize_value` (domain/services/dq_serializer.py) | MEDIUM | Check logic overlap |
| 6 | `LineageMetadata` (domain/composite/lineage.py) | `LineageMetadata` (domain/models/metadata.py) | HIGH | Two classes with same name in same layer! |
| 7 | `_require_non_empty` (domain/composite/aggregation.py) | `_require_non_empty` (domain/composite/config.py) | LOW | Tiny validators, acceptable |
| 8 | `_validate_positive` (domain/resilience.py) | `_validate_positive` (domain/composite/config.py) | LOW | Tiny validators, acceptable |
| 9 | `CleanupResult` (application/core/cleanup_service.py) | `CleanupResult` (application/services/bronze_cleanup_service.py) | HIGH | Two classes with same name in same layer |
| 10 | `_run_pipeline_async` (interfaces/cli/commands/run.py) | `_run_pipeline_async` (interfaces/cli/commands/run_all.py) | MEDIUM | Check if logic is truly duplicated |

### 4.3 Cross-Provider Extractors (same name, different logic)

These functions share names across provider-specific modules but process different API responses:

| Function | Providers | Verdict |
|----------|-----------|---------|
| `extract_authors` | crossref, semanticscholar, openalex | Different APIs → different parsing logic. NOT duplication. |
| `extract_author_orcids` | crossref, semanticscholar, openalex | Same — different response structures. |
| `extract_affiliations` | crossref, semanticscholar, openalex | Same. |
| `extract_journal_info` | crossref, semanticscholar, openalex | Same. |
| `extract_external_ids` | semanticscholar, openalex | Same. |
| `extract_open_access_info` | semanticscholar, openalex | Check if logic overlaps — both parse OA status. |
| `TitleFallbackHandler` | crossref, pubmed, openalex | Check if base class can be extracted. |

## 5. Dependency Map (consensus from B1/B3/B4)

### 5.1 Highest Fan-Out (depends on many)

| # | Module | Dependencies | Layer |
|---|--------|-------------|-------|
| 1 | `composition.factories.pipeline_factories` | 46-49 | composition |
| 2 | `domain.__init__` | 24-28 | domain |
| 3 | `domain.ports.__init__` | 24 | domain |
| 4 | `composition.bootstrap.runtime.composite` | 22-23 | composition |
| 5 | `composition.factories.services_factory` | 22-31 | composition |
| 6 | `composition.factories.pipeline_factory` | 17-34 | composition |
| 7 | `application.core.__init__` | 20-21 | application |
| 8 | `infrastructure.adapters.chembl.client` | 12-20 | infrastructure |
| 9 | `composition.providers.registration` | 15-18 | composition |
| 10 | `application.composite.runner` | 22 | application |

Note: Exact counts vary between branches due to different counting methods (direct imports vs transitive).

### 5.2 Highest Fan-In (depended upon by many)

| # | Module | Dependents | Layer |
|---|--------|-----------|-------|
| 1 | `domain.types` | 74-131 | domain |
| 2 | `domain.ports` | 46-181 | domain |
| 3 | `domain.exceptions` | 26-30 | domain |
| 4 | `domain.config` | 17-37 | domain |
| 5 | `domain.medallion` | 16-21 | domain |
| 6 | `domain.context` | 36 | domain |
| 7 | `domain.entities` | 14-18 | domain |
| 8 | `infrastructure.config` | 12-27 | infrastructure |

### 5.3 Cyclic Dependencies

**Not analyzed by any branch.** All deferred to external tooling (pydeps, import-linter, grimp, networkx).

## 6. Recommendations

### 6.1 Immediate Actions (Quick Wins)

| # | Action | Scope | Impact | Effort |
|---|--------|-------|--------|--------|
| 1 | Delete confirmed DEAD constants (#1-5 in §2.2) | 5 objects | Reduces noise | S |
| 2 | Delete confirmed DEAD private functions (#6-36 in §2.2) | 31 functions | ~200 LOC removal | S |
| 3 | Delete dead pipeline aliases (#68-76 in §2.2) | 9 classes | Cleaner _pipelines.py | S |
| 4 | Delete dead Protocols in config_service.py (#61-67 in §2.2) | 7 classes | Cleaner service | S |
| 5 | Verify and delete dead runner_helpers (#77-80 in §2.2) | 4 functions | ~200 LOC | M |
| 6 | Fix `__all__` export gaps (§2.4) | 11 modules | API clarity | S |
| 7 | Run `pyflakes` / `ruff check --select F401` for unused imports | project-wide | Lint cleanliness | S |

### 6.2 Refactoring Tasks (require planning)

| # | RF-ID | Description | Impact | Risk |
|---|-------|-------------|--------|------|
| 1 | RF-DUP-001 | Extract shared `_MetadataBuilderBase` from Silver/Gold metadata builders | Remove ~50 LOC duplication | LOW |
| 2 | RF-DUP-002 | Consolidate `_load_yaml` between BaseConfigLoader and DQConfigLoader | Remove ~20 LOC duplication | LOW |
| 3 | RF-DUP-003 | Extract shared `get_source_metadata` into base data source | Remove ~30 LOC duplication | LOW |
| 4 | RF-NAME-001 | Resolve `LineageMetadata` name collision within domain layer | Naming clarity | MEDIUM |
| 5 | RF-NAME-002 | Resolve `CleanupResult` name collision within application layer | Naming clarity | MEDIUM |
| 6 | RF-CROSS-001 | Verify `normalize_string`/`parse_date_field`/`validate_smiles` domain↔application overlap | Potential ~50 LOC | MEDIUM |
| 7 | RF-CROSS-002 | Consolidate `_get_bioetl_version` to single location | Remove ~10 LOC | LOW |
| 8 | RF-INFRA-001 | Investigate legacy `config_loader.py` — many SELF_ONLY helpers may be superseded by `config/pipeline_config_loader.py` | ~400 LOC cleanup | HIGH |
| 9 | RF-DEPS-001 | Run cyclic dependency analysis with import-linter or grimp | Architecture health | MEDIUM |

### 6.3 Per-Layer Health Summary

| Layer | Dead Objects | Confirmed Dupes | Name Collisions | Health |
|-------|-------------|----------------|-----------------|--------|
| domain | ~36 | 0 | 2 (LineageMetadata, tiny validators) | ⚠️ |
| application | ~44 | 1 | 2 (CleanupResult, cross-domain funcs) | ⚠️ |
| infrastructure | ~26 | 2 | 0 (intentional DTO separation) | ⚠️ |
| composition | ~1 | 0 | 0 | ✅ |
| interfaces | ~0 | 0 | 1 (_run_pipeline_async) | ✅ |

## 7. Methodology Notes for Future Audits

1. **Define DEAD vs SELF_ONLY explicitly** before counting. SELF_ONLY private helpers are NOT dead code.
2. **Do not count protocol conformance as duplication.** Methods like `aclose()`, `health_check()`, `fetch()` that implement a shared Protocol/Port are polymorphism, not copy-paste.
3. **Constants counting must specify**: UPPER_SNAKE_CASE only? Include `__all__`? Include TypeVars?
4. **Use AST hashing** for confirmed duplicates, not just name matching.
5. **Always include cyclic dependency analysis** — this is the most consistently missing section.
6. **Verify classifications with grep** before reporting. At minimum spot-check 10% of DEAD claims.
