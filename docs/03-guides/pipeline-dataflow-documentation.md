# Pipeline Dataflow Documentation Guide

## Overview

Pipeline dataflow documentation provides a comprehensive view of how data flows through BioETL pipelines from source to Gold layer. This documentation is automatically generated from pipeline configurations and schema contracts, ensuring it stays synchronized with the actual runtime behavior.

## Purpose

Pipeline dataflow documentation serves several key purposes:

- **Transparency**: Shows exactly what data is extracted, filtered, and transformed at each stage
- **Validation**: Provides a reference for understanding pipeline behavior and DQ policies
- **Debugging**: Helps identify where data issues occur in the pipeline
- **Communication**: Enables clear discussion about pipeline logic between team members

## Generated Artifacts

For each pipeline, the following artifacts are generated:

### 1. Pipeline Passport
A comprehensive document describing the pipeline's dataflow, including:
- Source profile and query criteria
- Silver and Gold filtering rules
- DQ policy and validation rules
- Output field specifications
- Linked diagram references

**Location**: `docs/02-architecture/generated/pipeline-dataflows/{pipeline_name}/pipeline-passport.md`

### 2. Dataflow Diagrams
Six Mermaid diagrams visualizing different aspects of the pipeline:
- **Dataflow**: Overall data movement through stages
- **Filter Criteria**: Source query and filtering logic
- **Silver Fields**: Field mappings and transformations (2 diagrams)
- **Gold Fields**: Final output field structure (2 diagrams)

**Location**: `docs/02-architecture/diagrams/architecture/svg/`

### 3. Machine-Readable Artifacts
- **IR JSON**: Intermediate representation for programmatic access
- **Field CSV**: Tabular field specification for analysis

**Location**: `docs/02-architecture/generated/pipeline-dataflows/{pipeline_name}/`

## Reading a Pipeline Passport

### Header Information

Each passport begins with metadata:

```markdown
Generated: 2026-08-05
Generator: 1.0.0
IR schema: 1.0.0
Effective config SHA256: 90b2b848882ce0d0681dd613c91724859a19ad23d2d82e43686e2054919a4204
```

- **Generated**: When the documentation was last updated
- **Effective config SHA256**: Hash of the configuration used to generate this passport
- **IR schema**: Version of the intermediate representation schema

### Source Profile

Describes where and how data is extracted:

```markdown
Profile: chembl.activity.curated
Version: 1.0.0
Status: baseline
Extraction hash: d4c7fc76dfcd88aa075762c96795ebd6de8af735540cf28a551a6d75149e4078
```

### Query Criteria Tables

The passport includes detailed tables showing filtering logic at each stage:

#### Source Query Criteria
```markdown
| Stage | Category | Field | Operator | Value | Enabled |
|-------|----------|-------|----------|-------|---------|
| source | api query | assay_type | in | B,F | true |
| source | api query | standard_type | in | IC50,Ki | true |
```

#### Silver Filtering Criteria
```markdown
| Stage | Category | Field | Operator | Value | Enabled |
|-------|----------|-------|----------|-------|---------|
| silver | structural | activity_id | is not null | true | true |
| silver | structural | molecule_id | is not null | true | true |
```

#### Gold Filtering Criteria
```markdown
| Stage | Category | Field | Operator | Value | Enabled |
|-------|----------|-------|----------|-------|---------|
| gold | column | assay_type | in | B, F | true |
| gold | range | pchembl_value | range | [3.0, 10.0] | true |
```

### DQ Policy Section

Documents the data quality enforcement:

```markdown
Soft-fail threshold: 0.05
Hard-fail threshold: 0.5
Strict validation: false
Invalid-record policy: quarantine
```

**Field validations**: Individual field constraints (required, pattern, range, enum)
**Cross-field validations**: Relationships between fields
**Conditional validations**: Rules that apply under specific conditions

### Output Field Specifications

Complete field listings for Silver and Gold layers:

```markdown
## Silver Output Fields (77)
Schema: bioetl.infrastructure.schemas.silver_chembl_core.CHEMBL_ACTIVITY_SCHEMA
Included groups: system, business, dq

| # | Field | Type | Nullable | Required | Group |
|---|-------|------|----------|----------|-------|
| 1 | entity_id | string | true | true | system |
| 2 | content_hash | string | true | true | system |
```

## Using Pipeline Dataflow Documentation

### For Pipeline Developers

When developing or modifying a pipeline:

1. **Check current behavior**: Review the passport to understand existing filtering and transformations
2. **Validate changes**: After configuration changes, regenerate documentation to see the impact
3. **DQ policy alignment**: Ensure DQ rules match business requirements
4. **Field mapping verification**: Confirm field transformations are correct

### For Data Engineers

When debugging data issues:

1. **Trace data flow**: Use the filter criteria tables to understand why records were excluded
2. **Identify validation failures**: Check the DQ policy section for field constraints
3. **Understand output structure**: Review output field specifications to know what to expect
4. **Compare stages**: Use Silver vs Gold field lists to understand transformations

### For Data Scientists

When analyzing data for ML/research:

1. **Understand data provenance**: Review source profile to know data origin
2. **Check filtering logic**: Use filter criteria to understand data selection bias
3. **Validate assumptions**: Confirm DQ thresholds match analysis requirements
4. **Field availability**: Use output field lists to plan feature engineering

### For Operations Teams

When troubleshooting production issues:

1. **Identify configuration changes**: Compare effective config SHA256 across runs
2. **Validate DQ compliance**: Check if hard-fail thresholds explain pipeline failures
3. **Understand data quality**: Review field validation rules to diagnose data issues
4. **Plan capacity**: Use field counts and types to estimate storage requirements

## CI Integration

Pipeline dataflow documentation is integrated into CI to prevent drift:

```yaml
# Example CI check
- name: Check pipeline dataflow drift
  run: python scripts/diagrams/generate_pipeline_dataflows.py --check-drift
```

If configuration changes would affect the dataflow without corresponding documentation updates, the CI will fail, ensuring documentation stays synchronized.

## Regenerating Documentation

To regenerate pipeline dataflow documentation:

```bash
# Regenerate all pipelines
python scripts/diagrams/generate_pipeline_dataflows.py

# Regenerate specific pipeline
python scripts/diagrams/generate_pipeline_dataflows.py --pipeline chembl_activity

# Check for drift without regenerating
python scripts/diagrams/generate_pipeline_dataflows.py --check-drift
```

## Common Use Cases

### Use Case 1: Understanding Why Records Were Filtered

**Scenario**: Pipeline ran but output has fewer records than expected

**Solution**:
1. Check Source Query Criteria table for API query filters
2. Review Silver Filtering Criteria for structural requirements
3. Examine Gold Filtering Criteria for final output constraints
4. Use DQ policy section to understand validation failures

### Use Case 2: Validating New Field Requirements

**Scenario**: Need to add a new field to the Gold output

**Solution**:
1. Check current Gold Output Fields to understand existing structure
2. Review transformer documentation in passport
3. Validate field requirements against DQ policy
4. Regenerate documentation after configuration changes

### Use Case 3: Debugging DQ Failures

**Scenario**: High quarantine rate in production

**Solution**:
1. Check DQ policy thresholds (soft-fail, hard-fail)
2. Review field validations for failing constraints
3. Examine cross-field validations for relationship issues
4. Use conditional validations to understand context-specific rules

### Use Case 4: Pipeline Comparison

**Scenario**: Comparing two pipelines for consistency

**Solution**:
1. Compare Source Profiles to understand extraction differences
2. Compare Filter Criteria tables to identify filtering logic differences
3. Compare DQ policies to understand quality enforcement differences
4. Compare Output Field specifications to understand structural differences

## Best Practices

### For Documentation Consumers

- **Always check the generation date** to ensure you're looking at current documentation
- **Use the effective config SHA256** to verify which configuration version is documented
- **Cross-reference with diagrams** for visual understanding of dataflow
- **Consult machine-readable artifacts** for programmatic analysis

### For Documentation Maintainers

- **Regenerate after configuration changes** to keep documentation current
- **Review CI failures** for drift detection issues
- **Validate generated artifacts** before committing to ensure accuracy
- **Update this guide** when new documentation features are added

## Troubleshooting

### Documentation Out of Sync

**Symptoms**: Passport doesn't match current pipeline behavior

**Solution**:
```bash
# Regenerate documentation
python scripts/diagrams/generate_pipeline_dataflows.py

# Verify generation succeeded
git diff docs/02-architecture/generated/pipeline-dataflows/
```

### Missing Pipeline Documentation

**Symptoms**: Pipeline passport doesn't exist for a pipeline

**Solution**:
```bash
# Generate specific pipeline
python scripts/diagrams/generate_pipeline_dataflows.py --pipeline <pipeline_name>

# Verify generation
ls docs/02-architecture/generated/pipeline-dataflows/<pipeline_name>/
```

### Diagram Rendering Issues

**Symptoms**: Mermaid diagrams don't render correctly

**Solution**:
1. Check Mermaid syntax in source files
2. Verify diagram generation script completed successfully
3. Review SVG files in the diagrams directory
4. Report issues if diagrams are consistently broken

## Related Documentation

- [Pipeline Configuration Guide](pipeline-configuration.md) - How to configure pipelines
- [DQ Configuration Guide](dq-configuration.md) - Data quality policy setup
- [ADR-054: Passport Documentation Projections](../02-architecture/decisions/ADR-054-passport-documentation-projections.md) - Architecture decision
- [Pipeline Catalog](../04-reference/pipeline-catalog.md) - Complete pipeline inventory
- [Passport Guide](../04-reference/passports/pipeline-passport-guide.md) - Cross-layer passport documentation

## Summary

Pipeline dataflow documentation provides a comprehensive, automatically generated view of pipeline behavior. By understanding how to read and use these artifacts, team members can more effectively develop, debug, and optimize BioETL pipelines while ensuring documentation stays synchronized with actual runtime behavior.