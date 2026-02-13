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

### 2.2 Confirmed DEAD Objects (grep-verified, zero callers anywhere)

> **CRITICAL CORRECTION v2 (post-verification):** The original list in this report
> contained **107 items**, of which **only 5 are truly DEAD**. The remaining 102
> were **SELF_ONLY** (called within the same file) or **ACTIVE** (imported by other
> modules). All 4 original codex branches AND the initial version of this
> consolidated report made the same error: using cross-file grep patterns that
> miss intra-module calls. The corrected list below is verified via
> `grep -rn <name> src/bioetl/ tests/`.

| # | Object | Type | Layer | File:Line | Verified |
|---|--------|------|-------|-----------|----------|
| 1 | `VALIDATION_API` | constant | domain | domain/validation.py:412 | 0 refs outside definition |
| 2 | `compute_subcellular_fraction_entity_id` | function | application | application/core/entity_id.py:36 | 0 callers anywhere |
| 3 | `PARSER_HELPERS` | constant | application | application/pipelines/pubmed/xml_parser.py:79 | 0 refs outside definition |
| 4 | `CIRCUIT_BREAKER_HELPERS` | constant | infrastructure | infrastructure/adapters/http/circuit_breaker.py:235 | 0 refs outside definition |
| 5 | `METRICS_COLLECTOR` | constant | infrastructure | infrastructure/observability/metrics.py:221 | 0 refs outside definition |

### 2.2.1 False Positives Corrected (were listed as DEAD, actually SELF_ONLY or ACTIVE)

The following items were classified as DEAD by one or more branches but are **verified active**:

| Object | Actual Status | Evidence |
|--------|--------------|----------|
| `_get_default_config` (validation.py) | SELF_ONLY | Called at validation.py:154 by `validate_publication_year` |
| `_match_error_type` (error_classifier.py) | SELF_ONLY | Called at error_classifier.py:154 by `ErrorClassifier.classify` |
| `_safe_json` (bioactivity.py) | SELF_ONLY | Called at bioactivity.py:290 by `Bioactivity` |
| `_validate_threshold_order` (composite/config.py) | SELF_ONLY | Called at config.py:672 |
| `_validate_non_negative` (resilience.py) | SELF_ONLY | Called at resilience.py:182 |
| All serialization helpers (serialization.py:142-200) | SELF_ONLY | Called by `serialize_to_json`/`deserialize_from_json` |
| All normalization page helpers (normalization.py:116-179) | SELF_ONLY | Called by `parse_page_range` at normalization.py:188-199 |
| All normalization author helpers (normalization.py:223-273) | SELF_ONLY | Called by `parse_authors_to_list` chain |
| All transformation normalizers (transformations.py:37-85) | SELF_ONLY | Used in `_NORMALIZERS` tuple at transformations.py:76-81 |
| `_extract_variant` (assay_transformer.py) | SELF_ONLY | Called at assay_transformer.py:178 |
| All crossref author_extractors helpers | SELF_ONLY | Called within `extract_author_details`/`extract_author_orcids` |
| All crossref reference_extractors helpers | SELF_ONLY | Called within `extract_references` |
| All openalex extractors helpers | SELF_ONLY | Called by extractors in same file |
| All uniprot comments.py helpers | SELF_ONLY | Called by `CommentExtractor` methods |
| All uniprot features.py helpers | SELF_ONLY | Called by `FeatureExtractor` methods |
| `_extract_nested_values` (dict_transformers.py) | SELF_ONLY | Called at dict_transformers.py:181 |
| `_span_context` (span_helpers.py) | SELF_ONLY | Called at span_helpers.py:49 and :60 |
| `_scan_provider_for_tables` (export_service.py) | SELF_ONLY | Called at export_service.py:131 |
| `_write_xlsx_file` (export_service.py) | SELF_ONLY | Called at export_service.py:381 |
| All config_service.py Protocols | SELF_ONLY | Used as type annotations in `ConfigService` (lines 202-205) |
| All runner_helpers.py functions | ACTIVE | Imported by `composite/runner.py:19-22`, called at :570, :623, :750, :755 |
| All quarantine/operations.py functions | ACTIVE | Imported by `quarantine/unified.py:24-27`, called at :140, :161, :183, :208 |
| All config_loader.py helpers | SELF_ONLY | Called within `load_pipeline_config()` flow |
| `_check_psutil_available` (memory_monitor.py) | SELF_ONLY | Called at memory_monitor.py:90 |
| `_get_metadata_filename` (metadata_writer.py) | SELF_ONLY | Called at metadata_writer.py:198 |
| `BaseConfigLoader` | ACTIVE | Imported by filter_config_loader.py:19, __init__.py:33 |
| `YamlSettingsSource` (_base.py) | SELF_ONLY | Used at _base.py:431 in `settings_customise_sources` |
| All _base.py config helpers | SELF_ONLY | Called within `yaml_config_to_domain` at lines 157-160 |
| All field_group_loader helpers | SELF_ONLY | Called within `load_field_groups` chain |
| `PubchemMoleculeRecord` | ACTIVE | Imported by pubchem/client.py:31, used at :53 |
| `AssayRecord` | ACTIVE | Imported by chembl/client.py:21, used at :67 |
| `CachedBronzeEmptyError` | ACTIVE | Imported by cached_bronze_data_source.py:23, raised at :227 |
| `AuthFailureError` | ACTIVE (API) | Re-exported in domain/__init__.py:117, domain/exceptions/__init__.py:75 |
| ChEMBL pipeline aliases (_pipelines.py) | TEST_ONLY | Re-exported in __init__.py, used in test_pipeline_registrations.py |

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

## 6. Recommendations (corrected)

### 6.1 Immediate Actions (Quick Wins)

| # | Action | Scope | Impact | Effort |
|---|--------|-------|--------|--------|
| 1 | Delete 5 confirmed DEAD constants/functions (§2.2) | 5 objects | Reduces noise | S |
| 2 | Fix `__all__` export gaps (§2.4) | 11 modules | API clarity | S |
| 3 | Run `ruff check --select F401` for unused imports | project-wide | Lint cleanliness | S |

### 6.2 Refactoring Tasks (require planning)

| # | RF-ID | Description | Impact | Risk |
|---|-------|-------------|--------|------|
| 1 | RF-DUP-001 | Extract shared `_MetadataBuilderBase` from Silver/Gold metadata builders | Remove ~50 LOC duplication | LOW |
| 2 | RF-DUP-002 | Consolidate `_load_yaml` between BaseConfigLoader and DQConfigLoader | Remove ~20 LOC duplication | LOW |
| 3 | RF-DUP-003 | Extract shared `get_source_metadata` into base data source | Remove ~30 LOC duplication | LOW |
| 4 | RF-NAME-001 | Resolve `LineageMetadata` name collision within domain layer | Naming clarity | MEDIUM |
| 5 | RF-NAME-002 | Resolve `CleanupResult` name collision within application layer | Naming clarity | MEDIUM |
| 6 | RF-CROSS-001 | Document `normalize_string`/`parse_date_field`/`validate_smiles` delegation pattern (verified as intentional REFACTOR-004 wrappers) | Documentation | LOW |
| 7 | RF-CROSS-002 | Consolidate `_get_bioetl_version` to single location | Remove ~10 LOC | LOW |
| 8 | RF-DEPS-001 | Run cyclic dependency analysis with import-linter or grimp | Architecture health | MEDIUM |

### 6.3 Per-Layer Health Summary (corrected)

| Layer | Dead Objects | Confirmed Dupes | Name Collisions | Health |
|-------|-------------|----------------|-----------------|--------|
| domain | 1 | 0 | 2 (LineageMetadata, tiny validators) | ✅ |
| application | 2 | 1 | 2 (CleanupResult, delegation wrappers) | ✅ |
| infrastructure | 2 | 2 | 0 (intentional DTO separation) | ⚠️ |
| composition | 0 | 0 | 0 | ✅ |
| interfaces | 0 | 0 | 1 (_run_pipeline_async) | ✅ |

## 7. Methodology Notes for Future Audits

1. **Define DEAD vs SELF_ONLY explicitly** before counting. SELF_ONLY private helpers are NOT dead code.
2. **Always verify with intra-file grep.** The pattern `grep -rn <name> src/` catches cross-file references, but MUST also check usage within the same file (e.g. `grep -n <name> <file>`). ALL four original branches AND this report's v1 missed this.
3. **Do not count protocol conformance as duplication.** Methods like `aclose()`, `health_check()`, `fetch()` that implement a shared Protocol/Port are polymorphism, not copy-paste.
4. **Constants counting must specify**: UPPER_SNAKE_CASE only? Include `__all__`? Include TypeVars?
5. **Use AST hashing** for confirmed duplicates, not just name matching.
6. **Always include cyclic dependency analysis** — this is the most consistently missing section.
7. **Spot-check at least 20%** of DEAD claims with `grep -n <name> <file>` to catch SELF_ONLY.
8. **Delegation wrappers are not duplication.** Functions like `dict_transformers.normalize_string` that delegate to `domain.normalization.normalize_string` with `return _domain_func(args)` are intentional backward-compatibility layers (REFACTOR-004).

---

## 8. Code Modification Prompts

Below are ready-to-use prompts for each recommended action. Each prompt is self-contained
and can be given to a code agent to execute.

### PROMPT-001: Delete DEAD Constants and Functions

```
Task: Remove 5 verified dead objects from the BioETL codebase.

Objects to delete (zero references anywhere in the codebase):

1. `VALIDATION_API` tuple in src/bioetl/domain/validation.py at line 412.
   It's a one-line assignment: `VALIDATION_API = (validate_publication_year, validate_inchi_key)`
   Delete just that line. The functions it references (validate_publication_year, validate_inchi_key)
   are actively used and MUST NOT be deleted.

2. `compute_subcellular_fraction_entity_id` function in
   src/bioetl/application/core/entity_id.py starting at line 36.
   Delete the entire function definition (def + body + docstring).
   Also remove it from `__all__` if present, and from
   application/core/__init__.py re-exports if present.

3. `PARSER_HELPERS` tuple in
   src/bioetl/application/pipelines/pubmed/xml_parser.py at line 79.
   It's a one-line assignment: `PARSER_HELPERS = (get_text, get_int)`
   Delete just that line. The functions it references are actively used.

4. `CIRCUIT_BREAKER_HELPERS` tuple in
   src/bioetl/infrastructure/adapters/http/circuit_breaker.py at line 235.
   Delete just that line.

5. `METRICS_COLLECTOR` assignment in
   src/bioetl/infrastructure/observability/metrics.py at line 221.
   Delete just that line.

After deletion:
- Run `ruff check --select F401` to ensure no new unused imports appeared.
- Run `pytest tests/` to confirm nothing breaks.
- Do NOT delete any SELF_ONLY helpers or functions that are called within the same file.
```

### PROMPT-002: Fix `__all__` Export Gaps

```
Task: Add missing constants to `__all__` in 11 modules.

For each module below, add the listed constants to the existing `__all__` list.
If the module has no `__all__`, create one containing all public names.

1. src/bioetl/infrastructure/serialization/encoders.py
   Add: "ORJSON_AVAILABLE"

2. src/bioetl/composition/factories/pipeline_factories.py
   Add: "PIPELINE_CONFIGS"

3. src/bioetl/interfaces/cli/exit_codes.py
   Add: "EXCEPTION_EXIT_CODES"

4. src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py
   Add: "KNOWN_PARAM_TYPES"

5. src/bioetl/application/core/field_specs.py
   Add: "FLOAT", "INT", "PMID", "STR"

6. src/bioetl/domain/composite/field_groups.py
   Add: "DEFAULT_PROVIDER_ORDER"

7. src/bioetl/domain/schemas/column_order.py
   Add: "ALL_SYSTEM_FIELDS", "DQ_FIELDS_SUFFIX", "SYSTEM_FIELDS_PREFIX"

8. src/bioetl/domain/schemas/constants.py
   Add all public UPPER_SNAKE_CASE constants that are currently missing from __all__.

9. src/bioetl/domain/value_objects/column_order.py
   Add: "DEFAULT_COLUMN_ORDER", "PUBLICATION_FIELD_GROUPS"

10. src/bioetl/domain/value_objects/publication_field_groups.py
    Add: "DEFAULT_FIELD_GROUP_CONFIG", "FIELD_TO_GROUP_MAPPING"

11. src/bioetl/domain/value_objects/column_qualifier.py
    Add: "JOIN_KEY_COLUMNS"

Rules:
- Do NOT modify any logic. Only add names to `__all__` lists.
- Verify each constant actually exists in the module before adding it.
- Maintain alphabetical order in `__all__` if the existing list is alphabetical.
- Run `ruff check` after changes.
```

### PROMPT-003: Run Unused Import Scan

```
Task: Find and remove unused imports across the BioETL codebase.

Steps:
1. Run `ruff check --select F401 src/bioetl/` to get the list of unused imports.
2. For each finding, verify it's truly unused (not a re-export for public API):
   - If the import is in an `__init__.py` and is part of `__all__`, it's a re-export — KEEP it.
   - If the import is in a `TYPE_CHECKING` block, it's a type annotation — KEEP it.
   - Otherwise, delete the unused import line.
3. Run `ruff check` again to confirm clean.
4. Run `pytest tests/` to confirm nothing breaks.

Known unused imports from prior analysis:
- src/bioetl/infrastructure/adapters/pubmed/_search.py:12 — `PubMedXmlProcessor`
- src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:10 — `time`
```

### PROMPT-004: Extract Shared MetadataBuilder Base (RF-DUP-001)

```
Task: Deduplicate identical __init__ methods in SilverMetadataBuilder and GoldMetadataBuilder.

File: src/bioetl/infrastructure/storage/metadata_builder.py

Current state:
- SilverMetadataBuilder.__init__ (line ~185) and GoldMetadataBuilder.__init__ (line ~321)
  have IDENTICAL implementations:
    def __init__(self, transform_version: str | None = None,
                 transform_steps: tuple[str, ...] | None = None) -> None:
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

Action:
1. Create a private base class `_MetadataBuilderBase` in the same file that contains
   the shared __init__.
2. Make both SilverMetadataBuilder and GoldMetadataBuilder inherit from it (in addition
   to any existing base classes).
3. Remove the __init__ from both subclasses since they now inherit it.
4. Add a brief docstring to _MetadataBuilderBase explaining it holds shared init logic.
5. Do NOT change any other methods or behavior.
6. Run `pytest tests/ -k metadata_builder` to verify.

Architecture rules:
- _MetadataBuilderBase stays in infrastructure layer (same file).
- Use single underscore prefix since it's internal.
- Follow NAME-004: private attributes use single underscore.
```

### PROMPT-005: Consolidate _load_yaml (RF-DUP-002)

```
Task: Deduplicate identical _load_yaml methods between BaseConfigLoader and DQConfigLoader.

Files:
- src/bioetl/infrastructure/config/base_config_loader.py (line ~70)
- src/bioetl/infrastructure/config/dq_config_loader.py (line ~131)

Both have identical _load_yaml implementations.

Action:
1. Read both files to confirm the methods are still identical.
2. Since DQConfigLoader likely doesn't inherit from BaseConfigLoader, create a small
   shared utility function `_load_yaml_file(path: Path) -> dict[str, Any]` as a
   module-level function in base_config_loader.py (or a new shared _yaml_utils.py
   if it fits better).
3. Have both _load_yaml methods delegate to this shared function.
4. Run `pytest tests/ -k config_loader` to verify.

Architecture rules:
- Both files are in infrastructure layer — no cross-layer concern.
- Keep the public interface (_load_yaml method signature) unchanged.
```

### PROMPT-006: Extract Shared get_source_metadata (RF-DUP-003)

```
Task: Deduplicate identical get_source_metadata between FilteredDataSource and
PublicationTermDataSource.

Files:
- src/bioetl/application/core/filtered_data_source.py (line ~353)
- src/bioetl/application/core/publication_term_data_source.py (line ~574)

Action:
1. Read both methods to confirm they're still identical.
2. Check if both classes share a common base class. If yes, move get_source_metadata
   to that base class.
3. If no common base, create a mixin class `SourceMetadataMixin` in the application
   layer with the shared method, and have both classes inherit from it.
4. Remove the method from both subclasses.
5. Run `pytest tests/ -k "filtered_data_source or publication_term"` to verify.

Architecture rules:
- Stay in application layer.
- Follow NAME-001: use *Mixin suffix if creating a mixin.
```

### PROMPT-007: Resolve LineageMetadata Name Collision (RF-NAME-001)

```
Task: Investigate and resolve the `LineageMetadata` name collision within the domain layer.

Files:
- src/bioetl/domain/composite/lineage.py — defines LineageMetadata
- src/bioetl/domain/models/metadata.py — defines LineageMetadata

Action:
1. Read both class definitions to understand the differences.
2. Determine if they serve different purposes or if one is a legacy duplicate.
3. Options:
   a) If one is a superset of the other, keep the richer one and make the other
      an alias (with deprecation comment).
   b) If they serve different purposes, rename the less-used one to be more specific
      (e.g., CompositeLineageMetadata for the composite module version).
   c) If one is unused, delete it.
4. Update all imports and __all__ exports accordingly.
5. Run `pytest tests/` to verify.

Architecture rules:
- Both are in domain layer — no cross-layer concern.
- Follow NAME-001: class names must be descriptive.
- Check domain/__init__.py and domain/composite/__init__.py for re-exports.
```

### PROMPT-008: Resolve CleanupResult Name Collision (RF-NAME-002)

```
Task: Investigate and resolve the `CleanupResult` name collision within the application layer.

Files:
- src/bioetl/application/core/cleanup_service.py — defines CleanupResult
- src/bioetl/application/services/bronze_cleanup_service.py — defines CleanupResult

Action:
1. Read both class definitions to understand the differences.
2. Determine if they serve different purposes (generic vs bronze-specific).
3. Options:
   a) If the bronze version is a specialization, rename it to BronzeCleanupResult.
   b) If they're identical, consolidate into one and have both modules import it.
   c) If one is unused, delete it.
4. Update all imports, __all__ exports, and callers.
5. Run `pytest tests/ -k cleanup` to verify.
```

### PROMPT-009: Consolidate _get_bioetl_version (RF-CROSS-002)

```
Task: Consolidate _get_bioetl_version to a single location.

Files:
- src/bioetl/infrastructure/storage/metadata_builder.py — defines _get_bioetl_version
- src/bioetl/composition/services/metadata_coordinator.py — defines _get_bioetl_version

Action:
1. Read both implementations to confirm they're identical or nearly identical.
2. Move the canonical version to domain layer as a utility:
   - Add `get_version() -> str` to src/bioetl/domain/version.py (create if needed),
     or to an existing domain utility module.
3. Replace both local _get_bioetl_version calls with imports from the canonical location.
4. Run `pytest tests/` to verify.

Architecture rules:
- Version info is domain-level knowledge.
- Both infrastructure and composition may import from domain (ARCH-001 allows this).
- Follow NAME-002: use `get_` prefix for local data retrieval.
```

### PROMPT-010: Investigate _run_pipeline_async Duplication

```
Task: Investigate whether _run_pipeline_async is truly duplicated between CLI commands.

Files:
- src/bioetl/interfaces/cli/commands/run.py — defines _run_pipeline_async
- src/bioetl/interfaces/cli/commands/run_all.py — defines _run_pipeline_async

Action:
1. Read both implementations carefully, comparing:
   - Function signatures
   - Core logic flow
   - Error handling
   - Click integration
2. If logic is >80% identical:
   a) Extract shared logic to a helper in interfaces/cli/commands/_pipeline_runner.py
   b) Have both commands call the shared helper with different parameters.
3. If logic is substantially different (different orchestration for single vs multi-pipeline):
   a) Rename one to `_run_single_pipeline_async` / `_run_all_pipelines_async` for clarity.
   b) Document why they're separate.
4. Run `pytest tests/ -k cli` to verify.

Architecture rules:
- Both are in interfaces layer — no cross-layer concern.
- CLI commands may have unique orchestration logic — duplication may be acceptable.
```

### PROMPT-011: Run Cyclic Dependency Analysis (RF-DEPS-001)

```
Task: Perform cyclic dependency analysis on the BioETL codebase.

Steps:
1. Install import-linter if not present:
   pip install import-linter

2. Create .importlinter config (or use existing if present) with these contracts:
   - domain MUST NOT import from application, infrastructure, composition, interfaces
   - application MUST NOT import from infrastructure, composition, interfaces
   - infrastructure MUST NOT import from application, composition, interfaces

3. Run: lint-imports

4. Alternatively, use grimp for graph analysis:
   pip install grimp
   Then write a small script to detect cycles:

   import grimp
   graph = grimp.build_graph("bioetl")
   # Check for intra-layer cycles
   for layer in ["domain", "application", "infrastructure", "composition", "interfaces"]:
       modules = [m for m in graph.modules if f".{layer}." in m]
       for mod in modules:
           chains = graph.find_illegal_dependencies_for_module(mod)
           if chains:
               print(f"CYCLE: {mod} -> {chains}")

5. Report findings as a list of:
   - Module A -> Module B -> ... -> Module A (cycle path)
   - Layer and severity

6. Do NOT fix cycles — only report them. Fixing requires architectural decisions.
```

### PROMPT-012: Document Cross-Layer DTO Separation Pattern

```
Task: Document the intentional cross-layer name duplication pattern for DTO/Domain separation.

The following classes share names across domain and infrastructure layers BY DESIGN:
- DQConfig, DQReportConfig
- CircuitBreakerConfig
- BaseClientConfig
- InputFilterConfig
- ValidationResult
- RateLimitConfig

Action:
1. Check if docs/02-architecture/decisions/ contains an ADR covering this pattern.
2. If NOT:
   a) Create ADR-NNN-cross-layer-config-naming.md following existing ADR format.
   b) Document:
      - Context: domain defines pure data models, infrastructure defines Pydantic schemas
        for YAML parsing.
      - Decision: same names are acceptable because they live in different namespaces
        (fully qualified imports disambiguate).
      - Consequences: grep for class names may return multiple hits; developers must check
        the import path.
      - Alternative considered: adding Yaml prefix to infrastructure variants.
3. If ADR already exists, verify it covers all 7 name pairs listed above.

Do NOT rename any classes. This is documentation-only.
```

### PROMPT-013: Verify and Document Delegation Wrappers (RF-CROSS-001)

```
Task: Document the application→domain delegation pattern for backward compatibility.

File: src/bioetl/application/core/dict_transformers.py

Current state (verified):
- normalize_string (line 198) → delegates to _domain_normalize_string (domain.normalization)
- parse_date_field (line 223) → delegates to _domain_parse_date_field (domain.normalization)
- validate_smiles (line 252) → delegates to _domain_validate_smiles (domain.validation)

Each wrapper has a "Note: Delegated to domain... per REFACTOR-004" comment.

Action:
1. Verify all callers of these wrapper functions still import from dict_transformers
   (not directly from domain). Run:
   grep -rn "from bioetl.application.core.dict_transformers import.*normalize_string\|parse_date_field\|validate_smiles" src/bioetl/ tests/
2. If callers exist → wrappers are needed, keep them. Add them to __all__ if missing.
3. If no callers besides tests → consider deprecation warning with:
   import warnings
   warnings.warn("Use bioetl.domain.normalization.normalize_string directly", DeprecationWarning)
4. Do NOT delete these wrappers — they may be part of the public API.
```
