# Implement Case Normalization and Canonicalization for ChEMBL Assay Fields

**Status**: Open
**Priority**: P1 (High)
**Labels**: `normalization`, `data-quality`, `audit`, `chembl_assay`
**Epic**: Assay Normalization Improvements 2024Q3

## 🎯 Problem

Fields like `assay_type`, `relationship_type`, and other enum-like fields in ChEMBL assay normalization lack consistent case handling and canonicalization. This leads to data inconsistencies and potential analysis errors.

## 🔍 Root Cause Analysis

1. **Inconsistent Case**: Enum fields use mixed case (e.g., "binding" vs "BINDING")
1. **No Canonicalization**: Missing standardized representation rules
1. **Analysis Issues**: Inconsistent data affects downstream processing
1. **Validation Gaps**: Case variations not properly handled
1. **DQ Rule Mismatch**: Filters expect specific case but normalization doesn't enforce it

## 📋 Scope

**Affected Components:**

- `src/bioetl/domain/normalization/profiles/chembl_assay.py` - Add normalization rules
- `src/bioetl/domain/normalization/rules.py` - Extend case/unit rules
- `src/bioetl/domain/schemas/assay.py` - Update validation
- Test files - Validate normalization
- Documentation - Update normalization specs

**Impact Analysis:**

```bash
# Check current case variations
grep -rn "assay_type\|relationship_type" src/bioetl/domain/ --include="*.py" | head -5
```

## 🎯 Solution Plan

### Phase 1: Rule Definition (2 days)

1. **Define Case Rules for Assay Fields**

   ```python
   # src/bioetl/domain/normalization/rules.py
   def normalize_assay_case(value: str, enum_values: list) -> str:
       """Normalize assay fields to uppercase if in enum, else return as-is."""
       return value.upper() if value in enum_values else value
   ```

1. **Update Normalization Profile**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_assay.py
   CHEMBL_ASSAY_PROFILE = build_standard_profile(
       case_fields={
           "assay_type": ASSAY_TYPES,
           "relationship_type": RELATIONSHIP_TYPES,
           "assay_category": ASSAY_CATEGORIES,
           "assay_test_type": ASSAY_TEST_TYPES,
           "assay_group": ASSAY_GROUPS,
       }
   )
   ```

1. **Add Special Rules for BAO Fields**

   ```python
   special_rules = {
       "bao_format": (normalize_bao_identifier, "Canonical BAO format"),
       "bao_label": (normalize_bao_label, "Canonical BAO label"),
   }
   ```

### Phase 2: Implementation (3 days)

1. **Apply Case Normalization**

   ```python
   # src/bioetl/domain/normalization/normalizer.py
   def normalize_assay_field(field_value: str, field_name: str) -> str:
       if field_name in CASE_FIELDS:
           return normalize_assay_case(field_value, get_enum(field_name))
       return field_value
   ```

1. **Update Pandera Schema**

   ```python
   # src/bioetl/domain/schemas/assay.py
   assay_type: Series[str] = pa.Field(
       str_matches=r"^[A-Z]+$", nullable=False  # Uppercase only
   )
   ```

1. **Add Validation Tests**

   ```python
   # tests/unit/domain/test_assay_normalization.py
   def test_case_normalization():
       assert normalize_assay_case("binding", ["BINDING"]) == "BINDING"
       assert normalize_assay_case("functional", ["FUNCTIONAL"]) == "FUNCTIONAL"
   ```

### Phase 3: Validation (2 days)

1. **Test Case Normalization**

   ```bash
   pytest tests/unit/domain/test_assay_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --assay-case-check
   ```

1. **Monitor Production**

   ```bash
   grep "normalize.*case" logs/production.log
   ```

## ✅ Success Criteria

- [ ] Case normalization rules implemented and tested
- [ ] All enum fields use consistent case (uppercase)
- [ ] BAO fields use canonical format
- [ ] DQ filters aligned with normalization rules
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check case normalization rules
grep -rn "normalize.*case" src/bioetl/domain/normalization/ --include="*.py"

# Run normalization tests
pytest tests/unit/domain/test_assay_normalization.py -v

# Validate case consistency
python scripts/validate_data_quality.py --case-check

# Type checking
mypy src/bioetl/domain/normalization/profiles/chembl_assay.py --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform field representation across pipeline
- **Accuracy**: Reduced analysis errors from case variations
- **DQ Alignment**: Normalization matches filter expectations
- **Maintainability**: Clear case handling rules

### Potential Risks

- **Breaking Changes**: Existing case variations will be standardized
- **Performance**: Additional case processing overhead
- **Data Migration**: Case changes affect content hashes

### Mitigation Strategies

- **Backward Compatibility**: Support both cases temporarily
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all case scenarios
- **Hash Migration**: Plan for content hash recalculation

## 🎯 Related Issues

- **Depends On**: AUDIT-001 (Enum Externalization)
- **Blocks**: AUDIT-003 (Pseudo-Null Handling)
- **Related To**: DQ-002 (Activity Case Normalization)

## ⏳ Time Estimate

**Total**: 7 days
**Start Date**: 2024-07-16
**Target Completion**: 2024-07-30

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Case normalization rules defined
- [ ] BAO canonicalization rules defined
- [ ] Normalization profile updated
- [ ] Pandera schema updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Content hash migration planned

## 🎯 Notes

This issue builds on the enum externalization work (AUDIT-001) to ensure consistent case representation of enum values throughout the ChEMBL assay processing pipeline. The implementation should follow the same pattern established for activity fields in DQ-002.
