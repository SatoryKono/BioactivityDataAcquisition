# Silver Schema Contract Tests

**Purpose:** Comprehensive contract tests ensuring Silver layer schema stability and consistency.

**Version:** 1.0.0
**Created:** 2026-02-10
**Related:** RULES.md §2.2 (Silver Layer Validation), ADR-018 (Gold Strict Validation)

______________________________________________________________________

## Overview

These tests protect against acmolecule_idental schema changes that would break:

- Downstream consumers (Gold layer, analytics, reports)
- Data contracts with external teams
- Historical data compatibility

**Test Categories:**

1. **Schema Stability** — Snapshot tests for field structure
1. **Field Types** — Type safety and consistency
1. **Validations** — Regex, range, enum checks
1. **Naming Conventions** — snake_case, prefixes, consistency

______________________________________________________________________

## Running Tests

### All Silver Schema Tests

```bash
pytest tests/contract/silver_schemas/ -v
```

### Representative CI Drift Gate

Use the fast representative subset when you want the same snapshot-based drift
signal that CI enforces for the initial selected pipelines:

```bash
pytest tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py -v
```

Representative pipelines in the current gate:

- `chembl_activity`
- `pubchem_compound`
- `pubmed_publication`
- `uniprot_protein`

### By Category

```bash
# Stability (snapshot) tests
pytest tests/contract/silver_schemas/test_schema_stability.py -v

# Type safety tests
pytest tests/contract/silver_schemas/test_field_types.py -v

# Validation rules
pytest tests/contract/silver_schemas/test_validations.py -v

# Naming conventions
pytest tests/contract/silver_schemas/test_naming_conventions.py -v
```

### Single Schema

```bash
pytest tests/contract/silver_schemas/ -v -k chembl_activity
```

______________________________________________________________________

## Snapshot Tests

Snapshot tests detect ANY schema change: field additions, deletions, type changes, validation changes.

### How Snapshots Work

1. **First run:** Creates initial snapshot JSON in `snapshots/`
1. **Subsequent runs:** Compares current schema against snapshot
1. **On mismatch:** Test fails with detailed diff

**Example snapshot:** `snapshots/chembl_activity_schema.json`

```json
{
  "activity_id": {
    "dtype": "str",
    "nullable": false,
    "checks": [],
    "description": "Primary key."
  },
  "standard_value": {
    "dtype": "float64",
    "nullable": true,
    "checks": [{"name": "greater_than_or_equal_to", "type": "ge"}],
    "description": "Standardized value."
  }
}
```

### Updating Snapshots

When schema change is **intentional**:

```bash
# Update all snapshots
UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py

# Update single schema snapshot
UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py -k chembl_activity
```

**IMPORTANT:** Only update snapshots after:

1. Reviewing impact on downstream consumers
1. Updating Gold contracts (`docs/04-reference/contracts/gold/`)
1. Creating migration guide (if breaking change)
1. Notifying data consumers

______________________________________________________________________

## Test Coverage

| Test File                    | Tests    | Schemas Covered | Purpose                                      |
| ---------------------------- | -------- | --------------- | -------------------------------------------- |
| `test_schema_stability.py`   | ~60      | All 18          | Snapshot tests for field structure           |
| `test_field_types.py`        | ~50      | All 18          | Type safety (str, int, float, datetime)      |
| `test_validations.py`        | ~40      | All 18          | Validation consistency (regex, range, enum)  |
| `test_naming_conventions.py` | ~35      | All 18          | Naming consistency (snake_case, conventions) |
| **Total**                    | **~185** | **18 schemas**  | **Full contract coverage**                   |

______________________________________________________________________

## Schemas Tested

### ChEMBL (12 schemas)

- `chembl_activity` — Bioactivity measurements
- `chembl_assay` — Assay protocols
- `chembl_assay_parameters` — Assay parameters
- `chembl_cell_line` — Cell lines
- `chembl_compound_record` — Compound records
- `chembl_molecule` — Molecules
- `chembl_protein_class` — Protein classifications
- `chembl_publication` — Publications
- `chembl_publication_similarity` — Publication similarity
- `chembl_publication_term` — Publication terms
- `chembl_target` — Drug targets
- `chembl_target_component` — Target components

### PubChem (1 schema)

- `pubchem_compound` — Chemical compounds

### UniProt (2 schemas)

- `uniprot_protein` — Protein sequences
- `uniprot_idmapping` — ID mappings

### Publications (5 schemas)

- `pubmed_publication` — PubMed articles
- `crossref_publication` — CrossRef works
- `openalex_publication` — OpenAlex publications
- `semanticscholar_publication` — Semantic Scholar papers
- `chembl_publication` — ChEMBL documents

______________________________________________________________________

## Test Details

### 1. Schema Stability Tests

**What:** Snapshot-based regression tests

**Detects:**

- ✅ Field additions
- ✅ Field deletions (BREAKING)
- ✅ Type changes (BREAKING)
- ✅ Nullability changes
- ✅ Validation rule changes

**Example:**

```python
def test_schema_fields_unchanged(schema_name: str):
    """Prevents acmolecule_idental schema modifications."""
    current = extract_field_metadata(schema)
    snapshot = load_snapshot(schema_name)
    assert current == snapshot  # Fails if ANY difference
```

______________________________________________________________________

### 2. Field Type Tests

**What:** Type safety and consistency checks

**Validates:**

- ✅ ID fields are `str` (not `int`)
- ✅ Nullable numerics use `Series[float] | None`
- ✅ Boolean fields use `bool` type
- ✅ Timestamps use `datetime64[ns]`
- ✅ Year fields are `int`
- ✅ No `object` dtype without justification

**Example:**

```python
def test_id_fields_are_strings(schema_name: str):
    """ID fields MUST be string type."""
    id_fields = [f for f in fields if "_id" in f]
    for field in id_fields:
        assert fields[field]["dtype"] == "str"
```

______________________________________________________________________

### 3. Validation Tests

**What:** Validation rule consistency

**Validates:**

- ✅ ChEMBL IDs match `^CHEMBL[0-9]+$`
- ✅ PMIDs match `^[1-9][0-9]*$`
- ✅ Year fields have range checks (1500-2100)
- ✅ Percentages bounded 0-100
- ✅ pChEMBL values in range 0-14
- ✅ Enum fields use `isin` validation
- ✅ Cross-provider consistency (DOI, year)

**Example:**

```python
def test_chembl_id_pattern_consistent(schema_name: str):
    """ChEMBL IDs MUST use CHEMBL_ID_PATTERN."""
    chembl_id_fields = [f for f in fields if f.endswith("_chembl_id")]
    for field in chembl_id_fields:
        assert has_regex_check(field, "^CHEMBL[0-9]+$")
```

______________________________________________________________________

### 4. Naming Convention Tests

**What:** Field naming consistency

**Validates:**

- ✅ All fields use `snake_case`
- ✅ No `camelCase` or `PascalCase`
- ✅ Boolean fields start with `is_`, `has_`, `can_`
- ✅ Metadata fields start with `_`
- ✅ Foreign keys end with `_id`
- ✅ Cross-provider consistency
- ✅ No legacy field names (e.g., `citation_count` → `citations_received`)

**Example:**

```python
def test_field_names_are_snake_case(schema_name: str):
    """All fields MUST use snake_case."""
    pattern = re.compile(r"^[a-z0-9_]+$")
    for field in fields:
        assert pattern.match(field), f"{field} not snake_case"
```

______________________________________________________________________

## CI/CD Integration

These tests run as part of the contract test suite:

```yaml
# .github/workflows/tests.yml
- name: Run Contract Tests
  run: pytest tests/contract/ --markers contracts
```

**On failure:** Pipeline blocks until schema change is intentional and snapshots updated.

______________________________________________________________________

## Maintenance

### Adding New Schema

1. Add schema class to `conftest.py::SILVER_SCHEMAS`
1. Run tests to create snapshot:
   ```bash
   pytest tests/contract/silver_schemas/ -k new_schema_name
   ```
1. Verify snapshot in `snapshots/new_schema_name_schema.json`
1. Commit snapshot with schema code

### Updating Existing Schema

1. Modify Pandera schema class
1. Run tests — they WILL fail:
   ```bash
   pytest tests/contract/silver_schemas/test_schema_stability.py -k schema_name
   ```
1. Review failure diff carefully
1. Update Gold contracts if needed
1. Update snapshots:
   ```bash
   UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py -k schema_name
   ```
1. Commit schema + snapshot together

### Deprecating Field

**NEVER delete fields directly** — breaking change!

Process:

1. Add new field with correct name
1. Mark old field as deprecated in description
1. Update transformers to populate both fields
1. Update documentation
1. After 1-2 releases: Remove old field + update snapshot

______________________________________________________________________

## FAQ

### Why snapshot tests?

**Problem:** Pandera schemas can change acmolecule_identally during refactoring.

**Solution:** Snapshot tests detect ANY change and require explicit approval via `UPDATE_SNAPSHOTS=1`.

### What if I just want to add a field?

Adding fields is usually safe (non-breaking), but:

1. Run tests — they'll fail showing new field
1. Review that field name follows conventions
1. Update snapshot: `UPDATE_SNAPSHOTS=1 pytest ...`

### What about removing fields?

**STOP!** Field removal is a BREAKING CHANGE.

1. Check if field is used by Gold layer contracts
1. Check if field is used by downstream consumers
1. Create deprecation plan
1. Update documentation
1. THEN remove + update snapshot

### Tests fail but I didn't change schemas?

**Causes:**

- Dependency update changed Pandera behavior
- Python version change
- Upstream schema inheritance change

**Fix:**

1. Investigate root cause
1. If legitimate: Update snapshots
1. If bug: Fix and keep snapshots unchanged

______________________________________________________________________

## References

- **RULES.md §2.2**: Silver Layer Validation
- **ADR-018**: Gold Strict Validation
- **ADR-024**: Entity Naming Unification
- **ADR-027**: DQ Rules Externalization
- **docs/glossary.md**: Ubiquitous Language

______________________________________________________________________

## Statistics

**Test Count:** ~185 tests
**Schemas Covered:** 18 (100% of Silver schemas)
**Snapshot Coverage:** 18/18 (100%)
**Naming Tests:** 35 (100% of schemas × naming rules)
**Validation Tests:** 40 (100% of schemas × validation rules)
**Type Safety Tests:** 50 (100% of schemas × type rules)

**Maintenance:** Low (snapshots update automatically with `UPDATE_SNAPSHOTS=1`)
**Value:** High (prevents acmolecule_idental breaking changes)
