# Handle Pseudo-Null Values in ChEMBL Assay Fields

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `normalization`, `data-quality`, `audit`, `chembl_assay`
**Epic**: Assay Normalization Improvements 2024Q3

## 🎯 Problem

Strings like "N/A", "None", "-", and "." in ChEMBL assay fields are not systematically converted to proper null values during normalization. This leads to inconsistent data representation and potential analysis issues.

## 🔍 Root Cause Analysis

1. **Inconsistent Null Handling**: Pseudo-null strings remain as strings
1. **Missing Rules**: No explicit normalization for null-like values
1. **Analysis Issues**: String nulls affect data quality metrics
1. **Validation Gaps**: Pandera doesn't catch pseudo-nulls
1. **DQ Rule Mismatch**: Filters may not handle string nulls properly

## 📋 Scope

**Affected Components:**

- `src/bioetl/domain/normalization/profiles/chembl_assay.py` - Add null rules
- `src/bioetl/domain/normalization/rules.py` - Implement null handling
- `src/bioetl/domain/schemas/assay.py` - Update schema validation
- Test files - Validate null normalization
- Documentation - Update null handling specs

**Impact Analysis:**

```bash
# Find pseudo-null values in assay data
grep -rn "N/A\|None\|-" src/bioetl/domain/ --include="*.py" | head -5
```

## 🎯 Solution Plan

### Phase 1: Pattern Definition (1 day)

1. **Define Null Patterns for Assay Fields**

   ```python
   # src/bioetl/domain/normalization/rules.py
   ASSAY_NULL_PATTERNS = frozenset(
       [
           "N/A",
           "NA",
           "n/a",
           "na",
           "None",
           "NONE",
           "none",
           "Null",
           "NULL",
           "null",
           "-",
           "--",
           ".",
           "..",
           "...",
           "",
           " ",
           "  ",
           "   ",
           "<NA>",
           "<NULL>",
           "NAN",
           "NaN",
           "nan",
           "MISSING",
           "missing",
           "UNKNOWN",
           "unknown",
       ]
   )
   ```

1. **Add Null Normalization Function**

   ```python
   def normalize_assay_null(value: Any) -> Any:
       """Convert pseudo-null values to proper None for assay fields."""
       if value is None:
           return None
       if not isinstance(value, str):
           return value
       normalized = normalize_string(value)
       return None if normalized in ASSAY_NULL_PATTERNS else value
   ```

### Phase 2: Implementation (2 days)

1. **Update Normalization Profile**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_assay.py
   NULL_FIELDS = frozenset(
       [
           "assay_type_description",
           "relationship_description",
           "assay_pref_name",
           "confidence_description",
           "assay_organism",
           "assay_cell_type",
           "assay_tissue",
           "assay_strain",
       ]
   )

   CHEMBL_ASSAY_PROFILE = build_standard_profile(null_fields=NULL_FIELDS)
   ```

1. **Add Profile Normalizer**

   ```python
   # src/bioetl/domain/normalization/profiles/profile_normalizers.py
   def normalize_profile_assay_null(value: object) -> object:
       """Convert pseudo-null values to None for assay fields."""
       return normalize_assay_null(value)
   ```

1. **Update Pandera Schema**

   ```python
   # src/bioetl/domain/schemas/assay.py
   assay_type_description: Series[str] = pa.Field(
       nullable=True,  # Now properly handles None
       description="Assay type description (may be null)",
   )
   ```

### Phase 3: Validation (1 day)

1. **Test Null Normalization**

   ```bash
   pytest tests/unit/domain/test_assay_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --assay-null-check
   ```

1. **Monitor Production**

   ```bash
   grep "null" reports/logs/bioetl.log
   ```

## ✅ Success Criteria

- [ ] Null patterns defined for assay fields
- [ ] Null normalization rules implemented
- [ ] Pandera schema updated for null handling
- [ ] All pseudo-null values converted to None
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check null normalization rules
grep -rn "normalize.*null" src/bioetl/domain/normalization/profiles/chembl_assay.py

# Run normalization tests
pytest tests/unit/domain/test_assay_normalization.py -v

# Validate null handling
python scripts/validate_data_quality.py --null-check

# Type checking
mypy src/bioetl/domain/normalization/profiles/chembl_assay.py --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Data Quality**: Consistent null handling across assay fields
- **Analysis**: Reduced null-related errors in processing
- **Validation**: Comprehensive null checks
- **Storage**: Proper None values instead of string nulls

### Potential Risks

- **Breaking Changes**: Existing string nulls become None
- **Performance**: Additional null processing overhead
- **Data Migration**: Null changes affect content hashes
- **Query Impact**: None vs string null affects filtering

### Mitigation Strategies

- **Backward Compatibility**: Support both formats temporarily
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all null scenarios
- **Hash Migration**: Plan for content hash recalculation
- **Query Updates**: Update filters to handle None properly

## 🎯 Related Issues

- **Depends On**: AUDIT-001 (Enum Externalization)
- **Blocks**: None
- **Related To**: DQ-003 (Activity Null Handling)

## ⏳ Time Estimate

**Total**: 4 days
**Start Date**: 2024-07-31
**Target Completion**: 2024-08-07

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Null patterns defined for assay fields
- [ ] Null normalization rules implemented
- [ ] Pandera schema updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Content hash migration planned

## 🎯 Notes

This issue extends the pseudo-null handling pattern (DQ-003) to ChEMBL assay fields, ensuring consistent null value handling and improved data quality throughout the assay processing pipeline. The implementation should follow the same pattern established for activity fields.
