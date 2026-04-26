# Handle Pseudo-Null Values in Activity Fields

**Status**: Completed ✅
**Priority**: P2 (Medium)
**Labels**: `normalization`, `DQ`, `data-quality`
**Epic**: Data Quality Improvements 2024Q2

## 🎯 Problem

Strings like "N/A", "None", "-", and "." are not systematically converted to proper null values during ChEMBL activity normalization. This leads to inconsistent data representation and potential analysis issues.

## 🔍 Root Cause

1. **Inconsistent Null Handling**: Pseudo-null strings remain as strings
2. **Missing Rules**: No explicit normalization for null-like values
3. **Analysis Issues**: String nulls affect data quality metrics
4. **Validation Gaps**: Pandera doesn't catch pseudo-nulls

## 📋 Scope

**Affected Components:**
- `src/bioetl/domain/normalization/profiles/chembl_activity.py` - Add null rules
- `src/bioetl/domain/normalization/rules.py` - Implement null handling
- Test files - Validate null normalization
- Documentation - Update null handling specs

**Impact Analysis:**
```bash
# Find pseudo-null values
grep -rn "N/A\|None\|-" src/bioetl/domain/ --include="*.py" | head -5
```

## 🎯 Solution Plan

### Phase 1: Rule Definition (2 days)

1. **Define Null Patterns**
   ```python
   # src/bioetl/domain/normalization/rules.py
   NULL_PATTERNS = ["N/A", "None", "-", ".", "null", ""]
   ```

2. **Add Null Rule**
   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   FIELD_RULES = {
       "standard_value": {
           "type": "float",
           "null_patterns": NULL_PATTERNS
       }
   }
   ```

3. **Update Normalizer**
   ```python
   # src/bioetl/domain/normalization/normalizer.py
   def normalize_null_value(value: str) -> Any:
       """Convert pseudo-null strings to None."""
       return None if value in NULL_PATTERNS else value
   ```

### Phase 2: Implementation (3 days)

1. **Apply Null Normalization**
   ```python
   # src/bioetl/domain/normalization/normalizer.py
   def normalize_field(field_value: str, field_name: str) -> Any:
       if field_name in NULL_FIELDS:
           return normalize_null_value(field_value)
       return field_value
   ```

2. **Update Pandera Schema**
   ```python
   # src/bioetl/domain/schemas/activity.py
   import pandera as pa

   class ActivitySchema(pa.DataFrameModel):
       standard_value: pa.typing.Series[pa.Float] = pa.Field(
           nullable=True,
           allow_na=True
       )
   ```

3. **Add Validation Tests**
   ```python
   # tests/unit/domain/test_normalization.py
   def test_null_normalization():
       assert normalize_null_value("N/A") is None
       assert normalize_null_value("0") == "0"
   ```

### Phase 3: Validation (2 days)

1. **Test Null Handling**
   ```bash
   pytest tests/unit/domain/test_normalization.py -v
   ```

2. **Validate Data Quality**
   ```bash
   python scripts/validate_data_quality.py --null-check
   ```

3. **Monitor Production**
   ```bash
   # Check null handling logs
   grep "null" logs/production.log
   ```

## ✅ Success Criteria

- [ ] Null patterns defined and documented
- [ ] Null normalization rules implemented
- [ ] Pandera schema updated for null handling
- [ ] All pseudo-null values converted to None
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check null normalization rules
grep -rn "normalize_null" src/bioetl/domain/ --include="*.py"

# Run normalization tests
pytest tests/unit/domain/test_normalization.py -v

# Validate data quality
python scripts/validate_data_quality.py --null-check

# Type checking
mypy src/bioetl/domain/normalization/ --strict
```

## 📈 Impact Assessment

### Positive Impacts
- **Data Quality**: Consistent null handling
- **Analysis**: Reduced null-related errors
- **Validation**: Comprehensive null checks
- **Documentation**: Clear null rules

### Potential Risks
- **Breaking Changes**: Existing null strings become None
- **Performance**: Additional null processing
- **Complexity**: More rules to maintain

### Mitigation Strategies
- **Backward Compatibility**: Support both formats temporarily
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all scenarios

## 🎯 Related Issues

- **Depends On**: DQ-001 (Enum Externalization)
- **Blocks**: DQ-004 (Type Consistency)
- **Related To**: DQ-002 (Case Normalization)

## ⏳ Time Estimate

**Total**: 7 days
**Start Date**: 2024-06-03
**Target Completion**: 2024-06-14

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Null patterns defined
- [ ] Null normalization rules implemented
- [ ] Pandera schema updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified

## 🎯 Notes

This issue addresses pseudo-null value handling to ensure consistent data representation. By systematically converting null-like strings to proper null values, we improve data quality and reduce analysis errors in the ChEMBL activity processing pipeline.
