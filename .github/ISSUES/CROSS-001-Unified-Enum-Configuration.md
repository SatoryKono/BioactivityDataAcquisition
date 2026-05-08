# Implement Unified Enum Configuration Across All ChEMBL Pipelines

**Status**: In Progress 🚧
**Priority**: P0 (Critical)
**Labels**: `normalization`, `configuration`, `architecture`, `cross-pipeline`
**Epic**: Cross-Pipeline Normalization Improvements 2026Q2

## 🎯 Problem

Enum-like fields across ChEMBL pipelines (activity, assay, molecule, target, etc.) use inconsistent enum handling approaches. Some enums are externalized, some are hardcoded, and there's no unified pattern across pipelines.

## 🔍 Root Cause Analysis

1. **Fragmented Enum Definitions**: Enums scattered across constants.py, YAML configs, and hardcoded values
1. **Inconsistent Usage**: Some pipelines use externalized enums, others don't
1. **Maintainability Issues**: Updating enum values requires changes in multiple places
1. **Validation Gaps**: Some enum fields lack proper Pandera validation
1. **Cross-Pipeline Drift**: Same logical fields handled differently in different pipelines

## 📋 Scope

**Affected Components:**

- `configs/enums/chembl.yaml` - Centralized enum configuration
- `src/bioetl/domain/schemas/constants.py` - Constants consolidation
- `src/bioetl/domain/normalization/profiles/chembl_*.py` - All pipeline profiles
- `src/bioetl/domain/schemas/chembl/*.py` - All pipeline schemas
- Test files - Cross-pipeline validation

**Impact Analysis:**

```bash
# Find enum usage across all pipelines
grep -rn "ASSAY_TYPES\|RELATIONSHIP_TYPES\|TARGET_TYPES" src/bioetl/domain/ --include="*.py" | wc -l
```

## 🎯 Solution Plan

### Phase 1: Enum Inventory and Standardization (3 days)

1. **Create Comprehensive Enum Inventory**

   ```yaml
   # configs/enums/chembl.yaml
   activity:
     standard_types: ["IC50", "EC50", "Ki", "Kd", "AC50", "GI50"]
     standard_relations: ["=", "<", "<=", ">", ">="]

   assay:
     types: ["B", "F", "A", "T", "P", "U"]
     relationship_types: ["D", "H", "M", "N", "S", "U"]
     categories: ["screening", "confirmatory", "panel", "summary", "other"]
     test_types: ["PRIMARY", "SECONDARY"]
     groups: ["FUNCTIONAL", "BINDING"]
     subcellular_fractions: ["Membrane", "Nucleus", "Cytoplasm", "Mitochondria"]

   molecule:
     types: ["Small molecule", "Inorganic small molecule", "Polymeric small molecule"]
     structure_types: ["MOL", "SEQ", "BOTH", "NONE"]

   target:
     types: ["SINGLE PROTEIN", "PROTEIN FAMILY", "PROTEIN COMPLEX"]
     component_relationships: ["SINGLE PROTEIN", "PROTEIN SUBUNIT", "RNA"]

   publication:
     types: ["journal-article", "patent", "dataset", "book", "review"]
   ```

1. **Consolidate Constants**

   ```python
   # src/bioetl/domain/schemas/constants.py
   # Move all pipeline-specific constants to YAML
   # Keep only truly global constants here
   ```

1. **Create Enum Loader Utility**

   ```python
   # src/bioetl/domain/config/enum_loader.py
   def get_chembl_enum(entity: str, field: str) -> list[str]:
       """Get enum values for any ChEMBL entity."""
       enums = load_chembl_enums()
       return enums[entity][field]
   ```

### Phase 2: Pipeline Integration (5 days)

1. **Update All Normalization Profiles**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   from bioetl.domain.config.enum_loader import get_chembl_enum

   STANDARD_TYPES = frozenset(get_chembl_enum("activity", "standard_types"))
   STANDARD_RELATIONS = frozenset(get_chembl_enum("activity", "standard_relations"))

   CHEMBL_ACTIVITY_PROFILE = build_standard_profile(
       enum_fields={
           "standard_type": STANDARD_TYPES,
           "standard_relation": STANDARD_RELATIONS,
       },
       case_fields={
           "standard_type": STANDARD_TYPES,
           "standard_relation": STANDARD_RELATIONS,
       },
   )
   ```

1. **Update All Pandera Schemas**

   ```python
   # src/bioetl/domain/schemas/chembl/activity.py
   from bioetl.domain.schemas.constants import STANDARD_TYPES

   standard_type: Series[str] = pa.Field(isin=list(STANDARD_TYPES), nullable=False)
   ```

1. **Apply to All Pipelines**

   - chembl_activity ✅ (DQ-001 pattern)
   - chembl_assay 📋 (AUDIT-001)
   - chembl_molecule 📋
   - chembl_target 📋
   - chembl_cell_line 📋
   - chembl_tissue 📋
   - chembl_publication 📋

### Phase 3: Validation and Testing (3 days)

1. **Create Cross-Pipeline Tests**

   ```python
   # tests/unit/domain/test_enum_consistency.py
   def test_cross_pipeline_enum_consistency():
       """Verify all pipelines use same enum values."""
       activity_enums = get_chembl_enum("activity", "standard_types")
       assay_enums = get_chembl_enum("assay", "types")
       # Verify consistency across pipelines
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --cross-pipeline-enum-check
   ```

1. **Monitor Production**

   ```bash
   grep "enum" reports/logs/bioetl.log | grep -E "activity|assay|molecule|target"
   ```

## ✅ Success Criteria

- [ ] Unified enum configuration in YAML
- [ ] All pipelines use externalized enums
- [ ] Consistent enum handling across pipelines
- [ ] Pandera validation for all enum fields
- [ ] Cross-pipeline tests passing
- [ ] Test coverage ≥95%
- [ ] No breaking changes

## 📊 Verification Commands

```bash
# Check enum usage across pipelines
grep -rn "get_chembl_enum" src/bioetl/domain/normalization/profiles/ | wc -l

# Run cross-pipeline tests
pytest tests/unit/domain/test_enum_consistency.py -v

# Validate enum consistency
python scripts/validate_data_quality.py --enum-check

# Type checking across all profiles
mypy src/bioetl/domain/normalization/profiles/ --strict
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform enum handling across all pipelines
- **Maintainability**: Single source of truth for all enum values
- **Validation**: Improved cross-pipeline data quality
- **Scalability**: Easy to add new enum fields

### Potential Risks

- **Breaking Changes**: Existing enum values may need updates
- **Migration Complexity**: Multiple pipelines affected
- **Performance**: Additional enum validation overhead
- **Content Hash Changes**: Enum standardization affects hashes

### Mitigation Strategies

- **Backward Compatibility**: Support both old and new enum values temporarily
- **Gradual Rollout**: Deploy pipeline by pipeline
- **Comprehensive Testing**: Validate all enum scenarios
- **Hash Migration**: Plan for content hash recalculation
- **Communication**: Notify all pipeline consumers

## 🎯 Related Issues

- **Depends On**: DQ-001 (Activity Enum Pattern)
- **Blocks**: CROSS-002 (Case Normalization)
- **Related To**: AUDIT-001, AUDIT-002, AUDIT-003

## ⏳ Time Estimate

**Total**: 11 days
**Start Date**: 2026-05-01
**Target Completion**: 2026-05-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Comprehensive enum inventory created
- [ ] YAML configuration extended
- [ ] All normalization profiles updated
- [ ] All Pandera schemas updated
- [ ] Cross-pipeline tests created
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Migration plan communicated

## 🎯 Progress Update

### ✅ Completed (Phase 1 - 3/3 days)

- **Day 1-2**: Created comprehensive enum inventory and extended YAML configuration
- **Day 3**: Enhanced enum loader with new functions (`get_chembl_enum`, `get_chembl_enum_set`)
- Added missing enum sections: `assay_groups`, `subcellular_fractions`, `confidence_descriptions`
- All enum loader tests passing

### ✅ Completed (Phase 2 - 2/5 days)

- **Day 4**: Updated assay profile to use externalized enums
- **Day 5**: Configured enum and case fields for assay pipeline
- All assay profile integration tests passing
- Cross-pipeline consistency verified

### 📋 In Progress (Phase 2 - 3/5 days)

- **Day 6-8**: Update remaining pipelines (molecule, target, cell_line, tissue, publication)
- Apply same pattern to all pipelines
- Create comprehensive cross-pipeline tests

### 📋 Remaining (Phase 3 - 3/3 days)

- **Day 9-11**: Final validation and testing
- Update Pandera schemas for all pipelines
- Create cross-pipeline consistency tests
- Document migration plan

## 🎯 Notes

This issue unifies the enum handling pattern established in DQ-001 across all ChEMBL pipelines, ensuring consistent enum management and improved data quality throughout the entire data processing ecosystem. The implementation should follow the same pattern but extend it to cover all entity types.
