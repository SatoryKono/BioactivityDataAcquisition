# Implement Case Normalization and Unit Canonicalization

**Status**: Completed ✅
**Priority**: P1 (High)
**Labels**: `normalization`, `DQ`, `refactoring`
**Epic**: Data Quality Improvements 2024Q2

## 🎯 Problem

Fields like `standard_units`, `assay_type`, and `standard_type` lack consistent case handling and unit canonicalization. This leads to inconsistencies in data representation and potential analysis errors.

## 🔍 Root Cause

1. **Inconsistent Case**: Enum fields use mixed case (e.g., "INHIBITOR" vs "inhibitor")
1. **Unit Variations**: Units appear in different formats (nM, NM, nm)
1. **No Canonicalization**: Missing standardized representation rules
1. **Analysis Issues**: Inconsistent data affects downstream processing

## 📋 Scope

**Affected Components:**

- `src/bioetl/domain/normalization/profiles/chembl_activity.py` - Add normalization rules
- `src/bioetl/domain/normalization/rules.py` - Implement case/unit rules
- Test files - Validate normalization
- Documentation - Update normalization specs

**Impact Analysis:**

```bash
# Check current unit variations
grep -rn "standard_units" src/bioetl/domain/ --include="*.py" | head -5
```

## 🎯 Solution Plan

### Phase 1: Rule Definition (2 days)

1. **Define Case Rules**

   ```python
   # src/bioetl/domain/normalization/rules.py
   def normalize_case(value: str, enum_values: list) -> str:
       """Normalize to uppercase if in enum, else return as-is."""
       return value.upper() if value in enum_values else value
   ```

1. **Define Unit Mapping**

   ```python
   # src/bioetl/domain/normalization/rules.py
   UNIT_MAPPING = {"nM": "nM", "NM": "nM", "nm": "nM", "uM": "uM", "UM": "uM", "µM": "uM"}
   ```

1. **Update Profile**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   FIELD_RULES = {
       "assay_type": {"type": "enum", "case": "upper"},
       "standard_units": {"type": "unit", "mapping": UNIT_MAPPING},
   }
   ```

### Phase 2: Implementation (3 days)

1. **Apply Case Normalization**

   ```python
   # src/bioetl/domain/normalization/normalizer.py
   def normalize_field(field_value: str, field_name: str) -> str:
       if field_name in CASE_FIELDS:
           return normalize_case(field_value, get_enum(field_name))
       return field_value
   ```

1. **Apply Unit Canonicalization**

   ```python
   def normalize_unit(unit_value: str) -> str:
       return UNIT_MAPPING.get(unit_value, unit_value)
   ```

1. **Update Tests**

   ```python
   # tests/unit/domain/test_normalization.py
   def test_case_normalization():
       assert normalize_case("inhibitor", ["INHIBITOR"]) == "INHIBITOR"


   def test_unit_canonicalization():
       assert normalize_unit("NM") == "nM"
   ```

### Phase 3: Validation (2 days)

1. **Test Normalization**

   ```bash
   pytest tests/unit/domain/test_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --case-check
   ```

1. **Monitor Production**

   ```bash
   # Check normalization logs
   grep "normalize" logs/production.log
   ```

## ✅ Success Criteria

- [ ] Case normalization rules implemented and tested
- [ ] Unit canonicalization rules implemented and tested
- [ ] All enum fields use consistent case
- [ ] All units use canonical format
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check case normalization
grep -rn "normalize_case" src/bioetl/domain/ --include="*.py"

# Run normalization tests
pytest tests/unit/domain/test_normalization.py -v

# Validate data quality
python scripts/validate_data_quality.py --case-check

# Type checking
mypy src/bioetl/domain/normalization/ --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform field representation
- **Accuracy**: Reduced analysis errors
- **Maintainability**: Clear normalization rules
- **Documentation**: Improved specs

### Potential Risks

- **Breaking Changes**: Existing data format changes
- **Performance**: Additional processing overhead
- **Complexity**: More rules to maintain

### Mitigation Strategies

- **Backward Compatibility**: Support both formats temporarily
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all scenarios

## 🎯 Related Issues

- **Depends On**: DQ-001 (Enum Externalization)
- **Blocks**: DQ-003 (Null Handling)
- **Related To**: DQ-004 (Type Consistency)

## ⏳ Time Estimate

**Total**: 7 days
**Start Date**: 2024-05-27
**Target Completion**: 2024-06-07

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Case normalization rules defined
- [ ] Unit canonicalization rules defined
- [ ] Normalization profile updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified

## 🎯 Notes

This issue builds on the enum externalization work (DQ-001) to ensure consistent representation of enum values and units throughout the ChEMBL activity processing pipeline.
