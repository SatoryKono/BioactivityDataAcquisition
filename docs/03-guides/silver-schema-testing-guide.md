______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Silver Schema Testing Guide

**Created:** 2026-02-10
**Purpose:** Guidelines for testing and maintaining Silver layer schemas

______________________________________________________________________

## Overview

Silver layer schemas define the structure and validation rules for normalized data. Schema stability is critical because changes affect:

- ✅ Gold layer contracts
- ✅ Downstream analytics
- ✅ External data consumers
- ✅ Historical data compatibility

This guide covers the **Silver Schema Contract Tests** that protect against accidental schema modifications.

______________________________________________________________________

## Test Suite Location

```
tests/contract/silver_schemas/
├── conftest.py                    # Schema registry and introspection
├── test_schema_stability.py       # Snapshot tests (~60 tests)
├── test_field_types.py            # Type safety tests (~50 tests)
├── test_validations.py            # Validation rules tests (~40 tests)
├── test_naming_conventions.py     # Naming consistency tests (~35 tests)
├── snapshots/                     # JSON snapshots (auto-generated)
│   ├── chembl_activity-schema.json
│   ├── chembl_molecule-schema.json
│   └── ...
└── README.md                      # Detailed test documentation
```

**Total:** ~185 contract tests covering 18 Silver schemas (100% coverage)

______________________________________________________________________

## Running Tests

### Quick Start

```bash
# Run all Silver schema contract tests (offline / no live API required)
uv run pytest tests/contract/silver_schemas/ -m contracts -v

# Run with coverage
uv run pytest tests/contract/silver_schemas/ -m contracts --cov=src/bioetl/domain/schemas --cov-report=term-missing

# Run for specific schema
uv run pytest tests/contract/silver_schemas/ -m contracts -k chembl_activity -v
```

These tests are marked `contracts` and `no_api`, so they do **not** require:

- `BIOETL_LIVE_API_TESTS=true`
- `BIOETL_NETWORK_TESTS=true`
- `--network`

### By Test Category

```bash
# Schema stability (snapshot tests)
uv run pytest tests/contract/silver_schemas/test_schema_stability.py -m contracts -v

# Representative CI schema drift gate
uv run pytest tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py -m contracts -v

# Type safety
uv run pytest tests/contract/silver_schemas/test_field_types.py -m contracts -v

# Validation rules
uv run pytest tests/contract/silver_schemas/test_validations.py -m contracts -v

# Naming conventions
uv run pytest tests/contract/silver_schemas/test_naming_conventions.py -m contracts -v
```

### Continuous Integration

```bash
# Run the schema-only contract subset locally
uv run pytest tests/contract/silver_schemas/ -m contracts -v

# Run the fast representative subset used as the initial per-PR schema-watch gate
uv run pytest tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py -m contracts -v
```

In CI these tests are included in the broader `contract-tests.yml` workflow.
They run alongside live API contract suites, but unlike provider live contracts
the Silver schema subset itself is offline and `no_api`.

The initial regular CI gate does not run every Silver schema on every PR. It
uses a representative subset to keep schema drift protection cheap and fast
while still covering distinct pipeline families:

- `chembl_activity`
- `pubchem_compound`
- `pubmed_publication`
- `uniprot_protein`

______________________________________________________________________

## Understanding Snapshot Tests

### What Are Snapshot Tests?

Snapshot tests capture the **current state** of a schema and detect ANY deviation:

- ✅ Field additions
- ✅ Field deletions (BREAKING)
- ✅ Type changes (BREAKING)
- ✅ Nullability changes
- ✅ Validation changes

### How They Work

1. **First run:** Creates `snapshots/{schema-name}-schema.json`
1. **Subsequent runs:** Compares current schema against snapshot
1. **On mismatch:** Test fails with detailed diff

### Example Snapshot

```json
{
  "activity_id": {
    "dtype": "str",
    "nullable": false,
    "unique": false,
    "coerce": false,
    "required": true,
    "description": "Primary key.",
    "checks": []
  },
  "standard_value": {
    "dtype": "float64",
    "nullable": true,
    "unique": false,
    "coerce": false,
    "required": true,
    "description": "Standardized value.",
    "checks": [
      {
        "name": "greater-than-or-equal-to",
        "type": "ge"
      }
    ]
  }
}
```

______________________________________________________________________

## Workflow: Adding New Schema

### Step 1: Create Pandera Schema

```python
# src/bioetl/domain/schemas/{provider}/{entity}.py
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class EntitySchema(ETLRecordSchema):
    """Pandera schema for Provider Entity.

    Aligned with RULES.md v6.1 and Provider API v2.0.
    """

    # Primary key
    entity_id: Series[str] = pa.Field(nullable=False, description="Primary key.")

    # Other fields...
```

### Step 2: Register Schema

```python
# tests/contract/silver_schemas/conftest.py
from bioetl.domain.schemas.{provider}.{entity} import EntitySchema

SILVER_SCHEMAS = {
    # ... existing schemas ...
    "provider_entity": EntitySchema,  # Add new schema
}
```

### Step 3: Generate Snapshot

```bash
# Run tests to create initial snapshot
uv run pytest tests/contract/silver_schemas/test_schema_stability.py -k {provider}_{entity}

# Verify snapshot created
ls tests/contract/silver_schemas/snapshots/{provider}_{entity}-schema.json
```

### Step 4: Commit Together

```bash
git add src/bioetl/domain/schemas/{provider}/{entity}.py
git add tests/contract/silver_schemas/conftest.py
git add tests/contract/silver_schemas/snapshots/{provider}-{entity}-schema.json
git commit -m "feat(schemas): add EntitySchema for Provider"
```

______________________________________________________________________

## Workflow: Modifying Existing Schema

### Step 1: Understand Impact

**Questions to ask:**

1. Is this a **breaking change**? (field deletion, type change, nullability change)
1. Will Gold layer contracts need updates?
1. Are there downstream consumers using this field?
1. Is historical data compatible?

### Step 2: Modify Schema

```python
# Example: Adding optional field (NON-BREAKING)
class ActivitySchema(ETLRecordSchema):
    # ... existing fields ...

    # NEW: Additional metadata
    data_source_version: Series[str] | None = pa.Field(
        nullable=True, description="Provider API version."
    )
```

### Step 3: Run Tests (They WILL Fail)

```bash
uv run pytest tests/contract/silver_schemas/test_schema_stability.py -k chembl_activity

# Example failure:
# FAILED: chembl_activity: New fields detected: ['data_source_version']
# If intentional, run: UPDATE_SNAPSHOTS=1 uv run pytest ...
```

### Step 4: Review Diff Carefully

The test output shows:

- **Added fields** — Usually safe
- **Removed fields** — **BREAKING CHANGE**
- **Type changes** — **BREAKING CHANGE**
- **Validation changes** — Review impact

### Step 5: Update Downstream

If breaking change:

1. Update Gold contracts (`docs/04-reference/contracts/gold/`)
1. Update composite pipeline configs (if applicable)
1. Create migration guide
1. Notify data consumers

### Step 6: Update Snapshot

```bash
# After confirming change is intentional
UPDATE_SNAPSHOTS=1 uv run pytest tests/contract/silver_schemas/test_schema_stability.py -k chembl_activity

# Verify snapshot updated
git diff tests/contract/silver_schemas/snapshots/chembl_activity-schema.json
```

### Step 7: Commit with Context

```bash
git add src/bioetl/domain/schemas/chembl/activity.py
git add tests/contract/silver_schemas/snapshots/chembl_activity-schema.json
git commit -m "feat(schemas): add data-source-version to ActivitySchema

- Added optional field for API version tracking
- Non-breaking change (nullable)
- Updated snapshot contract

Related: #1234"
```

______________________________________________________________________

## Workflow: Deprecating Field

**NEVER delete fields directly** — this is a BREAKING CHANGE.

### Phase 1: Add Replacement (Release N)

```python
class PublicationSchema(ETLRecordSchema):
    # NEW field with correct name
    citations_received: Series[int] | None = pa.Field(
        nullable=True, description="Number of citations received (incoming)."
    )

    # OLD field marked deprecated
    citation_count: Series[int] | None = pa.Field(
        nullable=True,
        description="DEPRECATED: Use citations_received instead. Will be removed in v6.0.",
    )
```

### Phase 2: Update Transformers (Release N)

```python
def transform_publication(raw: dict) -> dict:
    # Populate BOTH fields during deprecation period
    citation_count = raw.get("citation_count", 0)

    return {
        "citations_received": citation_count,  # NEW
        "citation_count": citation_count,  # OLD (deprecated)
        # ... other fields
    }
```

### Phase 3: Update Documentation (Release N)

- Add to CHANGELOG.md: "DEPRECATED: citation_count field"
- Create migration guide showing field rename
- Update Gold contracts to use new field name

### Phase 4: Monitor Usage (Release N+1)

- Check logs for queries using old field
- Contact consumers to migrate
- Wait 1-2 releases

### Phase 5: Remove Field (Release N+2)

```python
class PublicationSchema(ETLRecordSchema):
    # NEW field (kept)
    citations_received: Series[int] | None = pa.Field(
        nullable=True, description="Number of citations received (incoming)."
    )

    # OLD field REMOVED
```

Update snapshot:

```bash
UPDATE_SNAPSHOTS=1 uv run pytest tests/contract/silver_schemas/test_schema_stability.py -k publication
```

______________________________________________________________________

## Test Categories Explained

### 1. Schema Stability Tests (`test_schema_stability.py`)

**Purpose:** Prevent accidental schema modifications

**Tests:**

- ✅ `test_schema_fields_unchanged` — Snapshot comparison
- ✅ `test_primary_key_field_exists` — PK presence
- ✅ `test_etl_metadata_fields_present` — ETL metadata
- ✅ `test_schema_has_docstring` — Documentation
- ✅ `test_fields_have_descriptions` — Field descriptions

**Coverage:** All 18 schemas

______________________________________________________________________

### 2. Field Type Tests (`test_field_types.py`)

**Purpose:** Ensure type safety and consistency

**Tests:**

- ✅ `test_no_object_dtype_without_reason` — Avoid generic `object`
- ✅ `test_id_fields_are_strings` — IDs are `str`, not `int`
- ✅ `test_numeric_fields_not_nullable_without_union` — `Series[float] | None`
- ✅ `test_boolean_fields_use_bool_type` — Booleans use `bool`
- ✅ `test_timestamp_fields_use_datetime` — Timestamps use `datetime64[ns]`
- ✅ `test_year_fields_are_int` — Years are `int`
- ✅ `test_coerce_used_appropriately` — Coercion justified

**Coverage:** All 18 schemas

______________________________________________________________________

### 3. Validation Tests (`test_validations.py`)

**Purpose:** Ensure validation consistency

**Tests:**

- ✅ `test_chembl_id_pattern_consistent` — ChEMBL ID regex
- ✅ `test_pmid_pattern_if_present` — PMID format
- ✅ `test_year_fields_have_range_check` — Year bounds
- ✅ `test_percentage_fields_bounded` — Percentages 0-100
- ✅ `test-pchembl_value-range` — pChEMBL 0-14
- ✅ `test_enum_fields_have_isin_check` — Enum validation
- ✅ `test_primary_keys_not_nullable` — PKs non-nullable
- ✅ `test-publication_doi-validation-consistent` — Cross-provider DOI
- ✅ `test-publication_year-range-consistent` — Cross-provider year

**Coverage:** All 18 schemas

______________________________________________________________________

### 4. Naming Convention Tests (`test_naming_conventions.py`)

**Purpose:** Enforce naming consistency

**Tests:**

- ✅ `test_field_names_are_snake_case` — snake-case only
- ✅ `test_no_camelcase_fields` — No camelCase
- ✅ `test_no_abbreviations_without_glossary` — Documented abbreviations
- ✅ `test_boolean_fields_start_with_is_has_can` — Boolean prefixes
- ✅ `test_metadata_fields_start_with_underscore` — Metadata `-` prefix
- ✅ `test_foreign_keys_have_id_suffix` — FKs end with `-id`
- ✅ `test_chembl_fk_naming_consistency` — ChEMBL FK patterns
- ✅ `test_common_fields_same_name_across_publications` — Publication consistency
- ✅ `test_id_field_naming_by_provider` — Provider conventions
- ✅ `test_no_legacy_dq_field_names` — No legacy DQ names

**Coverage:** All 18 schemas

______________________________________________________________________

## Troubleshooting

### Test Fails: "New fields detected"

**Cause:** You added a field to the schema

**Solution:**

```bash
# If addition is intentional
UPDATE_SNAPSHOTS=1 uv run pytest tests/contract/silver_schemas/test_schema_stability.py -k schema-name
```

______________________________________________________________________

### Test Fails: "Fields removed"

**Cause:** You deleted a field — **BREAKING CHANGE**

**Solution:**

1. **STOP** — Do not delete fields without deprecation
1. Follow deprecation workflow (Phase 1-5)
1. Only delete after 1-2 releases

______________________________________________________________________

### Test Fails: "Type changed"

**Cause:** You changed field dtype — **BREAKING CHANGE**

**Solution:**

1. Verify change is necessary
1. Check impact on historical data
1. Update Gold contracts
1. Create migration guide
1. Update snapshot

______________________________________________________________________

### Test Fails: "Validation checks changed"

**Cause:** You added/removed validation (regex, range, enum)

**Solution:**

1. Verify validation is correct
1. Check if change affects existing data
1. Update DQ configs if needed
1. Update snapshot

______________________________________________________________________

### Test Fails: "Field not snake-case"

**Cause:** Field name violates naming conventions

**Solution:**

```python
# BAD
publicationYear: Series[int]
PublicationYear: Series[int]

# GOOD
publication_year: Series[int]
```

______________________________________________________________________

## Best Practices

### DO ✅

- ✅ Run contract tests before committing schema changes
- ✅ Update snapshots explicitly with `UPDATE_SNAPSHOTS=1`
- ✅ Add field descriptions for all new fields
- ✅ Follow deprecation workflow for field removal
- ✅ Keep commits atomic (schema + snapshot together)
- ✅ Document breaking changes in CHANGELOG.md

### DON'T ❌

- ❌ Delete fields without deprecation period
- ❌ Change field types without migration plan
- ❌ Use `object` dtype without justification
- ❌ Ignore failed contract tests
- ❌ Update snapshots without reviewing diff
- ❌ Commit schema without updating snapshot

______________________________________________________________________

## Integration with CI/CD

Silver schema contract tests are part of the broader contract workflow, but they
are the offline subset of that workflow:

```yaml
# .github/workflows/contract-tests.yml
- name: Run full contract suite
  run: |
    BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true uv run pytest tests/contract/ -v --tb=short --network
```

Local schema-only verification stays simpler:

```bash
uv run pytest tests/contract/silver_schemas/ -m contracts -v
```

**On failure:** The contract workflow fails, preventing unnoticed schema drift.

**Manual override:** Requires `UPDATE_SNAPSHOTS=1` flag (not available in CI by design).

______________________________________________________________________

## Performance

| Test Category      | Execution Time     | Parallelizable |
| ------------------ | ------------------ | -------------- |
| Schema Stability   | ~5-10 seconds      | ✅ Yes         |
| Field Types        | ~3-5 seconds       | ✅ Yes         |
| Validations        | ~5-10 seconds      | ✅ Yes         |
| Naming Conventions | ~3-5 seconds       | ✅ Yes         |
| **Total**          | **~20-30 seconds** | ✅ Yes         |

**Optimization:** optional explicit parallel run:

```bash
uv run pytest tests/contract/silver_schemas/ -m contracts -n auto --dist loadscope
```

______________________________________________________________________

## Maintenance Schedule

| Task                      | Frequency             | Owner         |
| ------------------------- | --------------------- | ------------- |
| Run contract tests        | Every commit          | Developer     |
| Review snapshots          | Every schema change   | Code reviewer |
| Update documentation      | Every breaking change | Developer     |
| Audit schema consistency  | Quarterly             | Data team     |
| Cleanup deprecated fields | Every major release   | Maintainer    |

______________________________________________________________________

## References

- **RULES.md §2.2**: Silver Layer Validation
- **ADR-018**: Gold Strict Validation
- **ADR-024**: Entity Naming Unification
- **ADR-027**: DQ Rules Externalization
- **docs/glossary.md**: Ubiquitous Language
- **tests/contract/silver_schemas/README.md**: Detailed test documentation

______________________________________________________________________

## Statistics

**Test Count:** ~185 tests
**Schemas Covered:** 18 (100%)
**Snapshot Coverage:** 18/18 (100%)
**Maintenance Time:** \<5 min per schema change
**Value:** Prevents accidental breaking changes

**Last Updated:** 2026-03-26
