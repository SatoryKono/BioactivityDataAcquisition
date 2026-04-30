# Implement Consistent Case Normalization and Ontology ID Canonicalization

**Status**: In Progress 🚧
**Priority**: P1 (High)
**Labels**: `normalization`, `data-quality`, `architecture`, `cross-pipeline`
**Epic**: Cross-Pipeline Normalization Improvements 2024Q3

## 🎯 Problem

Case handling and ontology ID formatting are inconsistent across ChEMBL pipelines. Some fields use uppercase, some lowercase, and ontology IDs (CLO, EFO, UBERON) lack standardized formatting.

## 🔍 Root Cause Analysis

1. **Inconsistent Case Handling**: Mixed case for enum-like fields ("Binding" vs "BINDING")
1. **Ontology ID Variations**: CLO, EFO, UBERON IDs not consistently formatted
1. **No Standard Rules**: Missing cross-pipeline case normalization strategy
1. **Content Hash Impact**: Case variations affect deterministic hashing
1. **DQ Rule Mismatches**: Filters expect specific case but normalization doesn't enforce it

## 📋 Scope

**Affected Components:**

- `src/bioetl/domain/normalization/rules.py` - Extended normalization rules
- `src/bioetl/domain/normalization/profiles/chembl_*.py` - All pipeline profiles
- `src/bioetl/domain/normalization/identifiers.py` - Ontology ID normalization
- Test files - Cross-pipeline validation

**Impact Analysis:**

```bash
# Check case variations across pipelines
grep -rn "normalize.*case\|uppercase\|lowercase" src/bioetl/domain/normalization/ --include="*.py" | wc -l
```

## 🎯 Solution Plan

### Phase 1: Rule Definition (2 days)

1. **Define Cross-Pipeline Case Rules**

   ```python
   # src/bioetl/domain/normalization/rules.py
   def normalize_cross_pipeline_case(value: str, strategy: str = "uppercase") -> str:
       """Normalize case using consistent strategy across all pipelines."""
       if strategy == "uppercase":
           return value.upper()
       elif strategy == "lowercase":
           return value.lower()
       else:
           return value
   ```

1. **Define Ontology ID Rules**

   ```python
   # src/bioetl/domain/normalization/identifiers.py
   ONTOLOGY_PREFIXES = {"CLO": "CLO_", "EFO": "EFO_", "UBERON": "UBERON_", "BAO": "BAO_"}


   def normalize_ontology_id(value: str) -> str:
       """Canonicalize ontology IDs with consistent prefix format."""
       # Handle both colon and underscore formats
       # Convert to underscore format consistently
   ```

1. **Create Case Strategy Configuration**

   ```yaml
   # configs/normalization/strategies.yaml
   case_strategies:
     enum_fields: "uppercase"  # assay_type, relationship_type, etc.
     ontology_fields: "original"  # Preserve original case for ontology terms
     description_fields: "original"  # Preserve case for free text
     id_fields: "uppercase"  # Standardize ID fields
   ```

### Phase 2: Pipeline Integration (4 days)

1. **Update All Normalization Profiles**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_activity.py
   CHEMBL_ACTIVITY_PROFILE = build_standard_profile(
       case_fields={
           "standard_type": ACTIVITY_STANDARD_TYPES,
           "standard_relation": STANDARD_RELATIONS,
       },
       special_rules={
           "bao_format": normalize_bao_identifier,
           "bao_label": normalize_bao_label,
       },
   )
   ```

1. **Add Ontology ID Normalization**

   ```python
   # src/bioetl/domain/normalization/profiles/chembl_cell_line.py
   CHEMBL_CELL_LINE_PROFILE = build_standard_profile(
       special_rules={
           "source_cell_id": normalize_ontology_id,
           "cell_ontology_id": normalize_ontology_id,
       }
   )
   ```

1. **Apply to All Pipelines**

   - chembl_activity: enum fields, BAO ✅
   - chembl_assay: enum fields, ontology IDs 📋
   - chembl_molecule: structure types 📋
   - chembl_target: target types 📋
   - chembl_cell_line: CLO IDs 📋
   - chembl_tissue: EFO/UBERON IDs 📋

### Phase 3: Validation and Testing (2 days)

1. **Create Cross-Pipeline Case Tests**

   ```python
   # tests/unit/domain/test_case_consistency.py
   def test_cross_pipeline_case_normalization():
       """Verify consistent case handling across all pipelines."""
       # Test that assay_type is uppercase in both assay and activity contexts
       # Test that ontology IDs use consistent format
   ```

1. **Validate Data Quality**

   ```bash
   python scripts/validate_data_quality.py --cross-pipeline-case-check
   ```

1. **Monitor Production**

   ```bash
   grep "normalize.*case\|ontology" reports/logs/bioetl.log
   ```

## ✅ Success Criteria

- [ ] Consistent case normalization rules implemented
- [ ] Ontology ID canonicalization implemented
- [ ] All pipelines use same case strategies
- [ ] Cross-pipeline tests passing
- [ ] Test coverage ≥95%
- [ ] Content hash consistency verified

## 📊 Verification Commands

```bash
# Check case normalization rules
grep -rn "normalize.*case\|case_fields" src/bioetl/domain/normalization/profiles/ | wc -l

# Check ontology ID rules
grep -rn "normalize.*ontology\|normalize.*identifier" src/bioetl/domain/normalization/ | wc -l

# Run cross-pipeline tests
pytest tests/unit/domain/test_case_consistency.py -v

# Validate case consistency
python scripts/validate_data_quality.py --case-check
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform case handling across all pipelines
- **Data Quality**: Reduced case-related duplicates and errors
- **Determinism**: Consistent content hashing
- **Maintainability**: Clear case normalization rules

### Potential Risks

- **Breaking Changes**: Existing case variations will be standardized
- **Content Hash Changes**: Case changes affect existing hashes
- **Performance**: Additional case processing overhead
- **Migration Complexity**: Multiple pipelines affected

### Mitigation Strategies

- **Backward Compatibility**: Support both cases temporarily
- **Gradual Rollout**: Deploy pipeline by pipeline
- **Hash Migration**: Plan for content hash recalculation
- **Communication**: Notify all pipeline consumers
- **Testing**: Comprehensive validation of case changes

## 🎯 Related Issues

- **Depends On**: CROSS-001 (Unified Enum Configuration)
- **Blocks**: None
- **Related To**: DQ-002, AUDIT-002

## ⏳ Time Estimate

**Total**: 8 days
**Start Date**: 2024-08-21
**Target Completion**: 2024-09-05

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Case normalization rules defined
- [ ] Ontology ID rules defined
- [ ] All normalization profiles updated
- [ ] Cross-pipeline tests created
- [ ] Tests updated and passing
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Migration plan communicated

## 🎯 Progress Update

### ✅ Completed (Phase 1 - 2/2 days)

- **Day 1**: Created `normalize_cross_pipeline_case()` function with 3 strategies (uppercase, lowercase, preserve)
- **Day 2**: Created comprehensive ontology ID normalization with support for 9 ontology prefixes
- All core normalization functions implemented and tested

### ✅ Completed (Phase 2 - 2/4 days)

- **Day 3**: Integrated case normalization into activity profile ✅
  - Added `create_case_normalizer()` helper function
  - Configured `standard_type` and `standard_relation` with uppercase strategy
  - All tests passing
- **Day 4**: Apply case strategies to enum fields ✅
  - Activity profile now uses cross-pipeline case normalization
  - Enum fields consistently normalized to uppercase

### 📋 In Progress (Phase 2 - 2/4 days)

- **Day 5**: Add ontology ID normalization to assay profile
- **Day 6**: Update remaining pipelines (molecule, target, cell_line, tissue)
  \=======

### ✅ Completed (Phase 2 - 2/4 days)

- **Day 3**: Integrated case normalization into activity profile ✅
  - Added `create_case_normalizer()` helper function
  - Configured `standard_type` and `standard_relation` with uppercase strategy
  - All tests passing
- **Day 4**: Apply case strategies to enum fields ✅
  - Activity profile now uses cross-pipeline case normalization
  - Enum fields consistently normalized to uppercase

### 📋 In Progress (Phase 2 - 2/4 days)

- **Day 5**: Add ontology ID normalization to assay profile
- **Day 6**: Update remaining pipelines (molecule, target, cell_line, tissue)

### 📋 Remaining (Phase 2 - 3/4 days)

- **Day 4-6**: Update remaining pipelines (assay, molecule, target, cell_line, tissue)
- Apply consistent patterns across all profiles

### 📋 Remaining (Phase 3 - 2/2 days)

- **Day 7-8**: Create comprehensive cross-pipeline tests
- Validate data quality and content hash consistency

## 🎯 Notes

This issue builds on the enum externalization work (CROSS-001) to ensure consistent case handling and ontology ID formatting across all ChEMBL pipelines. The implementation should establish clear cross-pipeline standards for case normalization and identifier canonicalization.
