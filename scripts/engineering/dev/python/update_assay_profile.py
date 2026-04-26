#!/usr/bin/env python3
"""Update assay profile to use cross-pipeline case normalization."""

import sys

# Read the file
with open("src/bioetl/domain/normalization/profiles/chembl_assay.py", "r") as f:
    content = f.read()

# Add the helper function before the profile definition
helper_function = '''def create_case_normalizer(strategy: str = "uppercase"):
    """Create a case normalizer function for profile use.

    Args:
        strategy: Case strategy ("uppercase", "lowercase", or "preserve")

    Returns:
        Normalizer function suitable for profile special_rules
    """
    def normalizer(value):
        return normalize_cross_pipeline_case(value, strategy)

    return normalizer

'''

# Find the position to insert the helper function (before CHEMBL_ASSAY_PROFILE)
profile_start = content.find("CHEMBL_ASSAY_PROFILE = build_standard_profile(")

# Insert the helper function
updated_content = content[:profile_start] + helper_function + content[profile_start:]

# Now replace the case_fields with special_rules in the profile
# Find the case_fields section
case_fields_start = updated_content.find(
    '    case_fields={\n        "assay_type": ASSAY_TYPES,'
)
case_fields_end = updated_content.find('    },\n    unit_fields={"standard_units"},')

# Replace case_fields with special_rules
special_rules_section = """    special_rules={
        **_SPECIAL_RULE_COMPONENTS,
        "assay_type": (
            create_case_normalizer("uppercase"),
            "Normalize assay_type to uppercase for consistency.",
        ),
        "relationship_type": (
            create_case_normalizer("uppercase"),
            "Normalize relationship_type to uppercase for consistency.",
        ),
        "assay_category": (
            create_case_normalizer("uppercase"),
            "Normalize assay_category to uppercase for consistency.",
        ),
        "assay_test_type": (
            create_case_normalizer("uppercase"),
            "Normalize assay_test_type to uppercase for consistency.",
        ),
        "assay_group": (
            create_case_normalizer("uppercase"),
            "Normalize assay_group to uppercase for consistency.",
        ),
    },"""

# Replace the section
updated_content = updated_content.replace(
    updated_content[
        case_fields_start : case_fields_end
        + len('    },\n    unit_fields={"standard_units"},')
    ],
    special_rules_section,
)

# Write the updated content
with open("src/bioetl/domain/normalization/profiles/chembl_assay.py", "w") as f:
    f.write(updated_content)

print("✅ Assay profile updated to use cross-pipeline case normalization")
