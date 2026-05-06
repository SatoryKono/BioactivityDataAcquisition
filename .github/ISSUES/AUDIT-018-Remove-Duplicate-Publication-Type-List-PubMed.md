# Remove Duplicate Publication Type List in PubMed Pipeline

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dq`, `refactoring`, `audit`, `pubmed`
**Epic**: PubMed Pipeline Cleanup 2024Q3

## 🎯 Problem

PubMed pipeline outputs two identical fields: `publication_types` and `publication_type_list`. Both contain the same JSON-serialized list of publication types, violating the "single source of truth" principle and creating confusion in schema validation and downstream processing.

## 🔍 Root Cause Analysis

1. **Redundant Field**: `publication_type_list` duplicates `publication_types` with identical data
2. **No Functional Difference**: Both fields serve the same purpose with no distinction
3. **Schema Confusion**: Unclear which field is canonical for validation
4. **Maintenance Risk**: Future changes may accidentally desynchronize the fields

## 📋 Scope

**Affected Components:**

- `src/bioetl/application/pipelines/pubmed/block_definitions.py` - Remove duplicate field (lines 308-309)
- `src/bioetl/domain/mapping/pubmed_publication.py` - Verify no dependencies on `publication_type_list`
- Silver/Gold schemas - Remove `publication_type_list` column
- Test files - Update/remove tests checking for `publication_type_list`
- DQ rules - Remove rules referencing `publication_type_list`

**Impact Analysis:**

```bash
# Check publication_type_list usage
grep -rn "publication_type_list" src/bioetl/ --include="*.py"
```

## 🎯 Solution Plan

### Phase 1: Dependency Check (0.5 day)

1. **Search for publication_type_list References**

   ```bash
   grep -rn "publication_type_list" src/bioetl/ tests/ configs/
   ```

1. **Verify No External Dependencies**

   - Check domain mappings don't reference `publication_type_list`
   - Check schemas don't require `publication_type_list`
   - Check DQ rules don't validate `publication_type_list`

1. **Document Findings**

   - List all files referencing `publication_type_list`
   - Confirm safe to remove

### Phase 2: Code Removal (0.5 day)

1. **Remove from Block Definition**

   ```python
   # src/bioetl/application/pipelines/pubmed/block_definitions.py
   # In _PubMedClassificationBlock.extract(), line 309:
   # DELETE this line:
   "publication_type_list": self._serialize_json_list(publication_types),
   ```

1. **Keep publication_types Only**

   ```python
   # Line 308 remains:
   "publication_types": self._serialize_json_list(publication_types),
   ```

### Phase 3: Schema Updates (0.5 day)

1. **Update Silver Schema**

   ```python
   # src/bioetl/domain/schemas/publication.py
   # Remove publication_type_list column if present
   ```

1. **Update Gold Contract**

   - Remove `publication_type_list` from Gold schema
   - Bump contract version for breaking change

1. **Update DQ Rules**

   ```python
   # configs/dq/publication.yaml
   # Remove any rules referencing publication_type_list
   # Ensure publication_types validation remains
   ```

### Phase 4: Test Updates (0.5 day)

1. **Remove publication_type_list Tests**

   ```python
   # tests/unit/application/pipelines/pubmed/test_block_definitions.py
   # Remove assertions checking for publication_type_list
   ```

1. **Update Golden Snapshots**

   - Regenerate golden test data without `publication_type_list`
   - Verify `publication_types` still present

1. **Integration Tests**

   ```bash
   pytest tests/integration/test_pubmed_pipeline.py -v
   ```

### Phase 5: Validation (0.5 day)

1. **Run Unit Tests**

   ```bash
   pytest tests/unit/application/pipelines/pubmed/ -v
   ```

1. **Run Integration Tests**

   ```bash
   pytest tests/integration/test_publication_pipelines.py -v -k pubmed
   ```

1. **Validate Schema**

   ```python
   python -m bioetl.domain.schemas.publication
   ```

## ✅ Success Criteria

- [ ] `publication_type_list` removed from `block_definitions.py`
- [ ] No code references to `publication_type_list` remain
- [ ] Silver schema updated (column removed)
- [ ] Gold contract updated (column removed)
- [ ] DQ rules updated (no references to removed field)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Golden snapshots updated
- [ ] `publication_types` field remains functional
- [ ] No breaking changes to `publication_types` usage

## 📊 Verification Commands

```bash
# Verify no publication_type_list references
grep -rn "publication_type_list" src/bioetl/ tests/ configs/

# Run PubMed tests
pytest tests/unit/application/pipelines/pubmed/ -v
pytest tests/integration/test_pubmed_pipeline.py -v

# Validate schema
python -m bioetl.domain.schemas.publication

# Check DQ rules
grep -rn "publication_type" configs/dq/
```

## 📈 Impact Assessment

### Positive Impacts

- **Schema Clarity**: Single canonical field for publication types
- **Maintainability**: No risk of desynchronization
- **Validation**: Clear DQ rule targets
- **Code Quality**: Removes redundancy

### Potential Risks

- **Breaking Change**: Downstream consumers may expect `publication_type_list`
- **Contract Version**: Requires schema version bump
- **Data Migration**: Existing data may need column removal

### Mitigation Strategies

- **Deprecation Period**: Mark field as deprecated before removal (if needed)
- **Communication**: Notify downstream consumers of schema change
- **Migration Script**: Remove column from existing silver data
- **Backward Compatibility**: Keep `publication_types` unchanged

## 🎯 Related Issues

- **Related To**: AUDIT-017 (ISSN Field Standardization)
- **Related To**: AUDIT-001 (Enum Externalization Assay)
- **Epic**: PubMed Pipeline Cleanup 2024Q3

## ⏳ Time Estimate

**Total**: 2.5 days
**Start Date**: 2024-08-08
**Target Completion**: 2024-08-10

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Dependency check completed
- [ ] All references documented
- [ ] `publication_type_list` removed from block_definitions.py
- [ ] Silver schema updated
- [ ] Gold contract updated
- [ ] DQ rules updated
- [ ] Unit tests updated
- [ ] Golden snapshots regenerated
- [ ] Integration tests passing
- [ ] Migration script created (if needed)
- [ ] Documentation updated
- [ ] Downstream consumers notified

## 🎯 Notes

This is a straightforward refactoring to remove a redundant field. The canonical field is `publication_types`, which should remain unchanged. All validation and processing should use `publication_types` exclusively. The change follows the principle of "single source of truth" and improves schema clarity.
