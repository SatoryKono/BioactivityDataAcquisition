# Externalize Enum Configurations for ChEMBL Activity Fields

**Status**: Open
**Priority**: P1 (High)
**Labels**: `normalization`, `configuration`, `DQ`
**Epic**: Data Quality Improvements 2024Q2

## 🎯 Problem

Current enum-like fields (assay_type, action_type, standard_units, etc.) have hardcoded values or limited validation in the ChEMBL activity normalization process. This creates maintainability issues and makes it difficult to update enum values consistently across the codebase.

## 🔍 Root Cause

1. **Hardcoded Values**: Enum values are scattered across code files
1. **Limited Validation**: Some enum fields lack proper Pandera validation
1. **Maintainability Issues**: Updating enum values requires changes in multiple places
1. **Inconsistent Handling**: Different fields use different approaches

## 📋 Scope

**Affected Components:**

- `configs/enums/` - New configuration files needed
- `src/bioetl/domain/normalization/profiles/chembl_activity.py` - Update to use external enums
- `src/bioetl/domain/schemas/activity.py` - Add Pandera validation
- Test files - Update to reflect new enum handling

**Impact Analysis:**

```bash
# Find current enum usage
grep -rn "assay_type\|action_type\|standard_units" src/bioetl/domain/ --include="*.py" | wc -l
```

## 🎯 Solution Plan

### Phase 1: Configuration Setup (3 days)

1. **Create Enum Configuration Files**

   ```yaml
   # configs/enums/chembl.yaml
   activity:
     assay_types: ["B", "F", "A", "T", "P", "U"]
     action_types: ["INHIBITOR", "AGONIST", "ANTAGONIST", "ACTIVATOR"]
     standard_units: ["nM", "μM", "mM", "g/L"]
     relations: ["=", "<", "<=", ">", ">=", "~"]
   ```

1. **Update Normalization Profile**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   from bioetl.configs.enums import chembl

   FIELD_RULES = {"assay_type": {"type": "enum", "values": chembl.activity.assay_types}}
   ```

1. **Add Pandera Validation**

   ```python
   # src/bioetl/domain/schemas/activity.py
   import pandera as pa
   from bioetl.configs.enums import chembl


   class ActivitySchema(pa.DataFrameModel):
       assay_type: pa.typing.Series[pa.String] = pa.Field(isin=chembl.activity.assay_types)
   ```

### Phase 2: Implementation (4 days)

1. **Update Normalization Logic**

   ```python
   # Apply enum configurations in normalization
   def normalize_activity(activity: dict) -> dict:
       activity["assay_type"] = normalize_enum(
           activity["assay_type"], chembl.activity.assay_types
       )
   ```

1. **Add Validation Tests**

   ```python
   # tests/unit/domain/test_normalization.py
   def test_enum_normalization():
       assert normalize_enum("B", chembl.activity.assay_types) == "B"
       assert normalize_enum("invalid", chembl.activity.assay_types) is None
   ```

1. **Update Documentation**

   ```markdown
   # docs/02-architecture/normalization.md
   ## Enum Configuration

   All enum fields are configured in `configs/enums/chembl.yaml`
   ```

### Phase 3: Validation (2 days)

1. **Test Enum Handling**

   ```bash
   pytest tests/unit/domain/test_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --enum-check
   ```

1. **Monitor Production**

   ```bash
   # Check for enum validation errors
   grep "enum" reports/logs/bioetl.log
   ```

## ✅ Success Criteria

- [ ] Enum configuration files created and documented
- [ ] Normalization profile updated to use external enums
- [ ] Pandera validation added for all enum fields
- [ ] All existing functionality preserved (backward compatibility)
- [ ] Test coverage ≥95% for enum handling
- [ ] No breaking changes in production

## 📊 Verification Commands

```bash
# Check enum configuration exists
ls -la configs/enums/chembl.yaml

# Run normalization tests
pytest tests/unit/domain/test_normalization.py -v

# Validate data quality
python scripts/validate_data_quality.py --enum-check

# Type checking
mypy src/bioetl/domain/normalization/ --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Maintainability**: Centralized enum management
- **Consistency**: Uniform enum handling across codebase
- **Validation**: Comprehensive Pandera checks
- **Documentation**: Clear enum configuration

### Potential Risks

- **Breaking Changes**: Existing data might not match new enums
- **Performance**: Additional validation overhead
- **Complexity**: More configuration to maintain

### Mitigation Strategies

- **Backward Compatibility**: Support both old and new enum values
- **Gradual Rollout**: Deploy in stages
- **Comprehensive Testing**: Validate all scenarios

## 🎯 Related Issues

- **Depends On**: None
- **Blocks**: DQ-002 (Case Normalization)
- **Related To**: DQ-003 (Null Handling), DQ-004 (Type Consistency)

## ⏳ Time Estimate

**Total**: 9 days
**Start Date**: 2024-05-20
**Target Completion**: 2024-06-03

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Enum configuration files created
- [ ] Normalization profile updated
- [ ] Pandera validation added
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified

## 🎯 Notes

This issue is foundational for improving data quality in the ChEMBL activity processing pipeline. By externalizing enum configurations, we establish a maintainable and consistent approach to handling enumerated values throughout the system.
