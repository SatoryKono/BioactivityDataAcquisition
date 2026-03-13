# Silver Schema Testing Guide

**Version:** 1.0.0
**Created:** 2026-02-10
**Purpose:** Guidelines for testing and maintaining Silver layer schemas

---

## Overview

Silver layer schemas define the structure and validation rules for normalized data. Schema stability is critical because changes affect:
- ✅ Gold layer contracts
- ✅ Downstream analytics
- ✅ External data consumers
- ✅ Historical data compatibility

This guide covers the **Silver Schema Contract Tests** that protect against accidental schema modifications.

---

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

---

## Running Tests

### Quick Start

```bash
# Run all Silver schema contract tests
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/ --network -v

# Run with coverage
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/ --network --cov=src/bioetl/domain/schemas

# Run for specific schema
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/ --network -k chembl_activity
```

### By Test Category

```bash
# Schema stability (snapshot tests)
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/test_schema_stability.py --network -v

# Type safety
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/test_field_types.py --network -v

# Validation rules
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/test_validations.py --network -v

# Naming conventions
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/silver_schemas/test_naming_conventions.py --network -v
```

### Continuous Integration

```bash
# Run as part of contract test suite
BIOETL_LIVE_API_TESTS=true BIOETL_NETWORK_TESTS=true pytest tests/contract/ --network -m contracts -v
```

---

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
2. **Subsequent runs:** Compares current schema against snapshot
3. **On mismatch:** Test fails with detailed diff

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

---

## Workflow: Adding New Schema

### Step 1: Create Pandera Schema

```python
# src/bioetl/domain/schemas/provider/entity.py
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

class EntitySchema(ETLRecordSchema):
    """Pandera schema for Provider Entity.

    Aligned with RULES.md v5.24 and Provider API v2.0.
    """

    # Primary key
    entity-id: Series[str] = pa.Field(
        nullable=False,
        description="Primary key."
    )

    # Other fields...
```

### Step 2: Register Schema

```python
# tests/contract/silver_schemas/conftest.py
from bioetl.domain.schemas.provider.entity import EntitySchema

SILVER_SCHEMAS = {
    # ... existing schemas ...
    "provider-entity": EntitySchema,  # Add new schema
}
```

### Step 3: Generate Snapshot

```bash
# Run tests to create initial snapshot
pytest tests/contract/silver_schemas/test_schema_stability.py -k provider-entity

# Verify snapshot created
ls tests/contract/silver_schemas/snapshots/provider-entity-schema.json
```

### Step 4: Commit Together

```bash
git add src/bioetl/domain/schemas/provider/entity.py
git add tests/contract/silver_schemas/conftest.py
git add tests/contract/silver_schemas/snapshots/provider-entity-schema.json
git commit -m "feat(schemas): add EntitySchema for Provider"
```

---

## Workflow: Modifying Existing Schema

### Step 1: Understand Impact

**Questions to ask:**
1. Is this a **breaking change**? (field deletion, type change, nullability change)
2. Will Gold layer contracts need updates?
3. Are there downstream consumers using this field?
4. Is historical data compatible?

### Step 2: Modify Schema

```python
# Example: Adding optional field (NON-BREAKING)
class ActivitySchema(ETLRecordSchema):
    # ... existing fields ...

    # NEW: Additional metadata
    data-source-version: Series[str] | None = pa.Field(
        nullable=True,
        description="Provider API version."
    )
```

### Step 3: Run Tests (They WILL Fail)

```bash
pytest tests/contract/silver_schemas/test_schema_stability.py -k chembl_activity

# Example failure:
# FAILED: chembl_activity: New fields detected: ['data-source-version']
# If intentional, run: UPDATE_SNAPSHOTS=1 pytest ...
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
2. Update composite pipeline configs (if applicable)
3. Create migration guide
4. Notify data consumers

### Step 6: Update Snapshot

```bash
# After confirming change is intentional
UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py -k chembl_activity

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

---

## Workflow: Deprecating Field

**NEVER delete fields directly** — this is a BREAKING CHANGE.

### Phase 1: Add Replacement (Release N)

```python
class PublicationSchema(ETLRecordSchema):
    # NEW field with correct name
    citations-received: Series[int] | None = pa.Field(
        nullable=True,
        description="Number of citations received (incoming)."
    )

    # OLD field marked deprecated
    citation_count: Series[int] | None = pa.Field(
        nullable=True,
        description="DEPRECATED: Use citations-received instead. Will be removed in v6.0."
    )
```

### Phase 2: Update Transformers (Release N)

```python
def transform_publication(raw: dict) -> dict:
    # Populate BOTH fields during deprecation period
    citation_count = raw.get("citation_count", 0)

    return {
        "citations-received": citation_count,  # NEW
        "citation_count": citation_count,      # OLD (deprecated)
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
    citations-received: Series[int] | None = pa.Field(
        nullable=True,
        description="Number of citations received (incoming)."
    )

    # OLD field REMOVED
```

Update snapshot:
```bash
UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py -k publication
```

---

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

---

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

---

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

---

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

---

## Troubleshooting

### Test Fails: "New fields detected"

**Cause:** You added a field to the schema

**Solution:**
```bash
# If addition is intentional
UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py -k schema-name
```

---

### Test Fails: "Fields removed"

**Cause:** You deleted a field — **BREAKING CHANGE**

**Solution:**
1. **STOP** — Do not delete fields without deprecation
2. Follow deprecation workflow (Phase 1-5)
3. Only delete after 1-2 releases

---

### Test Fails: "Type changed"

**Cause:** You changed field dtype — **BREAKING CHANGE**

**Solution:**
1. Verify change is necessary
2. Check impact on historical data
3. Update Gold contracts
4. Create migration guide
5. Update snapshot

---

### Test Fails: "Validation checks changed"

**Cause:** You added/removed validation (regex, range, enum)

**Solution:**
1. Verify validation is correct
2. Check if change affects existing data
3. Update DQ configs if needed
4. Update snapshot

---

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

---

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

---

## Integration with CI/CD

Contract tests run automatically in CI:

```yaml
# .github/workflows/tests.yml
- name: Run Contract Tests
  run: |
    pytest tests/contract/ -m contracts -v --tb=short
```

**On failure:** Pipeline blocks, preventing broken schemas from merging.

**Manual override:** Requires `UPDATE_SNAPSHOTS=1` flag (not available in CI by design).

---

## Performance

| Test Category | Execution Time | Parallelizable |
|---------------|----------------|----------------|
| Schema Stability | ~5-10 seconds | ✅ Yes |
| Field Types | ~3-5 seconds | ✅ Yes |
| Validations | ~5-10 seconds | ✅ Yes |
| Naming Conventions | ~3-5 seconds | ✅ Yes |
| **Total** | **~20-30 seconds** | ✅ Yes |

**Optimization:** Tests run in parallel with `pytest-xdist`:
```bash
pytest tests/contract/silver_schemas/ -n auto
```

---

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Run contract tests | Every commit | Developer |
| Review snapshots | Every schema change | Code reviewer |
| Update documentation | Every breaking change | Developer |
| Audit schema consistency | Quarterly | Data team |
| Cleanup deprecated fields | Every major release | Maintainer |

---

## References

- **RULES.md §2.2**: Silver Layer Validation
- **ADR-018**: Gold Strict Validation
- **ADR-024**: Entity Naming Unification
- **ADR-027**: DQ Rules Externalization
- **docs/glossary.md**: Ubiquitous Language
- **tests/contract/silver_schemas/README.md**: Detailed test documentation

---

## Statistics

**Test Count:** ~185 tests
**Schemas Covered:** 18 (100%)
**Snapshot Coverage:** 18/18 (100%)
**Maintenance Time:** <5 min per schema change
**Value:** Prevents accidental breaking changes

**Last Updated:** 2026-02-10
