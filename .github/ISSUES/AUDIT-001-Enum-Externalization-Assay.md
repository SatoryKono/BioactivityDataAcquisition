# Externalize Enum Configurations for ChEMBL Assay Fields

**Status**: Open
**Priority**: P1 (High)
**Labels**: `normalization`, `configuration`, `audit`, `chembl_assay`
**Epic**: Assay Normalization Improvements 2024Q3

## 🎯 Problem

Enum-like fields in ChEMBL assay normalization (assay_type, relationship_type, assay_category, etc.) have hardcoded values or limited validation. This creates maintainability issues and makes it difficult to update enum values consistently.

## 🔍 Root Cause Analysis

1. **Hardcoded Values**: Enum values scattered across code files
1. **Limited Validation**: Some enum fields lack proper validation
1. **Maintainability Issues**: Updating enum values requires changes in multiple places
1. **Inconsistent Handling**: Different fields use different approaches
1. **Missing Externalization**: No YAML config for assay-specific enums

## 📋 Scope

**Affected Components:**

- `configs/enums/chembl.yaml` - Extend with assay-specific enums
- `src/bioetl/domain/normalization/profiles/chembl_assay.py` - Update to use external enums
- `src/bioetl/domain/schemas/assay.py` - Add Pandera validation
- Test files - Update to reflect new enum handling

**Impact Analysis:**

```bash
# Find current enum usage in assay
grep -rn "assay_type\|relationship_type\|assay_category" src/bioetl/domain/ --include="*.py" | wc -l
```

## 🎯 Solution Plan

### Phase 1: Enum Inventory (2 days)

1. **Identify Enum Fields**

   - assay_type: "B", "F" (ChEMBL assay types)
   - relationship_type: "D", "E", etc.
   - assay_category: "B", "F", etc.
   - assay_test_type: "PRIMARY", "SECONDARY"
   - assay_group: "FUNCTIONAL", "BINDING"
   - confidence_description: "Likely active", "Active", etc.
   - assay_subcellular_fraction: "Membrane", "Nucleus", etc.

1. **Create Enum Configuration**

   ```yaml
   # configs/enums/chembl.yaml
   assay:
     types: ["B", "F"]
     relationship_types: ["D", "E", "M", "S"]
     categories: ["screening", "confirmatory", "panel"]
     test_types: ["PRIMARY", "SECONDARY"]
     groups: ["FUNCTIONAL", "BINDING"]
     confidence_descriptions: ["Likely active", "Active", "Inactive"]
     subcellular_fractions: ["Membrane", "Nucleus", "Cytoplasm"]
   ```

### Phase 2: Implementation (3 days)

1. **Update Normalization Profile**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_assay.py
   from bioetl.domain.config.enum_loader import get_enum_config

   ASSAY_TYPES = frozenset(get_enum_config("assay", "types"))
   RELATIONSHIP_TYPES = frozenset(get_enum_config("assay", "relationship_types"))

   CHEMBL_ASSAY_PROFILE = build_standard_profile(
       enum_fields={
           "assay_type": ASSAY_TYPES,
           "relationship_type": RELATIONSHIP_TYPES,
           # ... other enum fields
       }
   )
   ```

1. **Add Enum Normalization Rules**

   ```python
   case_fields = {
       "assay_type": ASSAY_TYPES,
       "relationship_type": RELATIONSHIP_TYPES,
   }
   ```

1. **Update Pandera Schema**

   ```python
   # src/bioetl/domain/schemas/assay.py
   assay_type: Series[str] = pa.Field(isin=list(ASSAY_TYPES), nullable=False)
   ```

### Phase 3: Validation (2 days)

1. **Test Enum Normalization**

   ```bash
   pytest tests/unit/domain/test_assay_normalization.py -v
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --assay-enum-check
   ```

1. **Monitor Production**

   ```bash
   grep "enum" reports/logs/bioetl.log
   ```

## ✅ Success Criteria

- [ ] Enum configurations externalized to YAML
- [ ] All enum fields use external configurations
- [ ] Pandera validation added for enum fields
- [ ] Case normalization implemented for enum fields
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check enum usage
grep -rn "get_enum_config" src/bioetl/domain/normalization/profiles/chembl_assay.py

# Run enum tests
pytest tests/unit/domain/test_assay_normalization.py -v

# Validate enum consistency
python scripts/validate_data_quality.py --enum-check

# Type checking
mypy src/bioetl/domain/normalization/profiles/chembl_assay.py --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Maintainability**: Single source of truth for enum values
- **Consistency**: Uniform enum handling across pipeline
- **Validation**: Improved data quality checks
- **Documentation**: Clear enum definitions

### Potential Risks

- **Breaking Changes**: Existing enum values may need updates
- **Performance**: Additional enum validation overhead
- **Complexity**: More enum configurations to maintain

### Mitigation Strategies

- **Backward Compatibility**: Support both old and new enum values temporarily
- **Gradual Rollout**: Deploy enum changes in stages
- **Comprehensive Testing**: Validate all enum scenarios

## 🎯 Related Issues

- **Depends On**: DQ-001 (Enum Externalization Pattern)
- **Blocks**: AUDIT-002 (Case Normalization)
- **Related To**: AUDIT-003 (Pseudo-Null Handling)

## ⏳ Time Estimate

**Total**: 7 days
**Start Date**: 2024-07-01
**Target Completion**: 2024-07-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Enum fields identified and documented
- [ ] YAML configuration created
- [ ] Normalization profile updated
- [ ] Pandera schema updated
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified

## 🎯 Notes

This issue extends the enum externalization pattern (DQ-001) to ChEMBL assay fields, ensuring consistent enum handling and improved data quality throughout the assay processing pipeline. The implementation should follow the same pattern established for activity fields.
