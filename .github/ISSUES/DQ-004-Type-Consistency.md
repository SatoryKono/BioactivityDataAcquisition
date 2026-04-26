# Ensure Type Consistency for Flags and Boolean Fields

**Status**: Completed ✅
**Priority**: P1 (High)
**Labels**: `normalization`, `DQ`, `type-safety`
**Epic**: Data Quality Improvements 2024Q2

## 🎯 Problem

Boolean flag fields like `manual_curation_flag` are currently treated as floats in the normalization profile but should be integers. This creates type inconsistencies and potential validation issues.

## 🔍 Root Cause

1. **Type Mismatch**: Flags defined as float vs. int
1. **Profile Inconsistency**: manual_curation_flag in FLOAT_FIELDS
1. **Validation Gaps**: Pandera expects float, schema allows both
1. **Analysis Issues**: Type inconsistencies affect data processing

## 📋 Scope

**Affected Components:**

- `src/bioetl/domain/normalization/profiles/chembl_activity.py` - Fix type definitions
- `src/bioetl/domain/schemas/activity.py` - Update Pandera schema
- Test files - Validate type consistency
- Documentation - Update type handling

**Impact Analysis:**

```bash
# Check current flag types
grep -rn "manual_curation_flag" src/bioetl/domain/ --include="*.py" | head -5
```

## 🎯 Solution Plan

### Phase 1: Analysis (2 days)

1. **Review Current Types**

   ```bash
   # Check profile vs. schema types
   grep -A5 "manual_curation_flag" src/bioetl/domain/normalization/profiles/chembl_activity.py
   ```

1. **Identify Inconsistencies**

   ```bash
   # Compare with domain model
   grep -A5 "manual_curation_flag" src/bioetl/domain/schemas/activity.py
   ```

1. **Document Findings**

   ```markdown
   # Create type consistency report
   reports/type-consistency-analysis.md
   ```

### Phase 2: Implementation (3 days)

1. **Fix Profile Types**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   INT_FIELDS = ["manual_curation_flag", "potential_duplicate", "original_activity_id"]
   ```

1. **Update Pandera Schema**

   ```python
   # src/bioetl/domain/schemas/activity.py
   manual_curation_flag: pa.typing.Series[pa.Int64] = pa.Field(ge=0, le=1, nullable=True)
   ```

1. **Add Validation Tests**

   ```python
   # tests/unit/domain/test_normalization.py
   def test_flag_types():
       assert isinstance(record["manual_curation_flag"], int)
   ```

### Phase 3: Validation (2 days)

1. **Test Type Consistency**

   ```bash
   pytest tests/unit/domain/test_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --type-check
   ```

1. **Monitor Production**

   ```bash
   # Check type validation logs
   grep "type" logs/production.log
   ```

## ✅ Success Criteria

- [ ] Type inconsistencies identified and documented
- [ ] Profile types corrected (float → int)
- [ ] Pandera schema updated for flags
- [ ] All flag fields use consistent types
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check type consistency
grep -rn "INT_FIELDS" src/bioetl/domain/ --include="*.py"

# Run normalization tests
pytest tests/unit/domain/test_normalization.py -v

# Validate data quality
python scripts/validate_data_quality.py --type-check

# Type checking
mypy src/bioetl/domain/normalization/ --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Type Safety**: Consistent flag types
- **Validation**: Improved data quality
- **Maintainability**: Clear type definitions
- **Documentation**: Updated type specs

### Potential Risks

- **Breaking Changes**: Existing float flags become int
- **Performance**: Type conversion overhead
- **Complexity**: More type rules

### Mitigation Strategies

- **Backward Compatibility**: Support both types temporarily
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all scenarios

## 🎯 Related Issues

- **Depends On**: DQ-001 (Enum Externalization)
- **Blocks**: None
- **Related To**: DQ-002 (Case Normalization), DQ-003 (Null Handling)

## ⏳ Time Estimate

**Total**: 7 days
**Start Date**: 2024-06-10
**Target Completion**: 2024-06-21

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Type inconsistencies identified
- [ ] Profile types corrected
- [ ] Pandera schema updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified

## 🎯 Notes

This issue addresses type consistency for boolean flags to ensure proper type handling throughout the ChEMBL activity processing pipeline. By standardizing flag types, we improve data quality and reduce type-related errors.
