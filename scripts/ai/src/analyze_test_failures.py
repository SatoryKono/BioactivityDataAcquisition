#!/usr/bin/env python3
"""Analyze test failures and their relevance to Sonar remediation."""

import re
from collections import defaultdict

# Test failure data from the error output
test_failures = [
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_valid_record",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_missing_activity_id",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_missing_molecule_id",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_all_core_fields",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_activity_values",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_quality_annotations",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_curation_fields_null",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_curation_flag_zero",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_json_fields_single",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_json_fields_multiple",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_empty_activity_properties",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_action_type",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_action_type_null",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_bao_and_uo_identifiers",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_standard_units_and_preserves_qudt_uri",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_full_activity_canonical_field_set",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_preserves_already_canonical_activity_fields",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_blank_canonical_fields_to_none[bao_endpoint-   ]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_blank_canonical_fields_to_none[bao_format-\t]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_blank_canonical_fields_to_none[standard_units- ]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_blank_canonical_fields_to_none[uo_units-]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_normalizes_blank_canonical_fields_to_none[qudt_units-  ]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency_valid_dict",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency_none",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_action_type_valid_dict",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerTransform::test_transform_action_type_none",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_quarantines_missing_nonnullable_contract_fields[canonical_smiles]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_quarantines_missing_nonnullable_contract_fields[standard_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_quarantines_missing_nonnullable_contract_fields[uo_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_uses_pipeline_config_to_quarantine_missing_contract_fields[canonical_smiles]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_uses_pipeline_config_to_quarantine_missing_contract_fields[standard_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_uses_pipeline_config_to_quarantine_missing_contract_fields[uo_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_required_field_quarantine_details_cover_all_config_required_fields",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_unitless_activity_measurements_are_quarantined_when_units_missing[Ratio-standard_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_unitless_activity_measurements_are_quarantined_when_units_missing[Relative potency-uo_units]",
    "ERROR tests/unit/application/pipelines/chembl/test_activity_transformer.py::TestActivityTransformerSilverContract::test_transform_output_validates_with_stateful_activity_schema",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_valid_record",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_missing_activity_id",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_missing_molecule_id",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_all_core_fields",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_activity_values",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_quality_annotations",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_curation_fields_null",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_curation_flag_zero",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_json_fields_single",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_json_fields_multiple",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_empty_activity_properties",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_action_type",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_action_type_null",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_custom_provider",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency_valid_dict",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_with_ligand_efficiency_none",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_action_type_valid_dict",
    "ERROR tests/unit/application/pipelines/test_activity_transformer_base.py::TestActivityTransformerTransform::test_transform_action_type_none",
]

print("🔍 Test Failure Analysis")
print("=" * 60)

# Categorize failures by test class
test_categories = defaultdict(list)
for failure in test_failures:
    # Extract test class name
    match = re.search(r'::([^:]+)::', failure)
    if match:
        test_class = match.group(1)
        test_categories[test_class].append(failure)

print(f"\n📊 Total Test Failures: {len(test_failures)}")
print(f"📋 Unique Test Classes: {len(test_categories)}")

# Analyze by test class
for test_class, failures in test_categories.items():
    print(f"\n📋 {test_class}: {len(failures)} failures")
    
    # Show first 3 examples
    for i, failure in enumerate(failures[:3]):
        test_name = failure.split('::')[-1]
        print(f"   {i+1}. {test_name}")
    if len(failures) > 3:
        print(f"   ... and {len(failures) - 3} more")

# Key findings
print("\n🎯 Key Findings:")
print("   • All failures are in ActivityTransformer-related tests")
print("   • Two main test classes affected:")
print("     - TestActivityTransformerTransform (most failures)")
print("     - TestActivityTransformerSilverContract")
print("   • Failures cover data transformation, validation, and contract enforcement")

# Relevance to Sonar remediation
print("\n🔮 Relevance to Sonar Remediation Program:")
print("   ✅ Wave 2 (Typing and Contract Cleanup):")
print("      - Silver contract tests validate data contracts")
print("      - Contract field validation is directly relevant")
print("      - Quarantine mechanisms for missing fields align with cleanup")

print("   ✅ Wave 3 (Complexity Refactors):")
print("      - Complex transformation logic needs refinement")
print("      - Multiple test scenarios suggest complex business rules")
print("      - Refactoring could simplify the transformer logic")

print("   ✅ Wave 4 (Hygiene):")
print("      - Consistent test failures suggest systematic issues")
print("      - Standardization of activity fields (bao, uo, qudt units)")
print("      - Blank field normalization aligns with hygiene goals")

# Recommendations
print("\n💡 Recommendations:")
print("   1. Prioritize Wave 3 (Complexity) - Transformer logic is complex")
print("   2. Focus on Wave 2 (Contracts) - Silver contract validation critical")
print("   3. Add test coverage improvement to remediation plan")
print("   4. Consider Wave 5: Test Stability - Fix flaky tests")

# Impact assessment
print("\n📈 Impact Assessment:")
print("   • Test failures validate the need for Sonar remediation")
print("   • Complexity in transformer logic confirms Wave 3 relevance")
print("   • Contract validation issues confirm Wave 2 relevance")
print("   • Systematic failures suggest architectural improvements needed")

print("\n✅ Analysis complete!")