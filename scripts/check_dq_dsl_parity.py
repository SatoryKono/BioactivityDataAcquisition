#!/usr/bin/env python3
"""
DQ DSL Parity Check Script

Verifies that DQ contracts documentation matches actual entity config DSL structure.
This script ensures documentation accuracy and prevents drift between docs and code.

Usage:
    python scripts/check_dq_dsl_parity.py

Exit Codes:
    0: All checks passed
    1: Parity issues found
"""

import yaml
import glob
from pathlib import Path
import sys
from typing import List, Dict, Any


def load_documentation() -> str:
    """Load DQ contracts documentation."""
    docs_path = Path("docs/04-reference/contracts/dq-contracts.md")
    try:
        with open(docs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Documentation file not found: {docs_path}")
        sys.exit(1)


def find_entity_configs() -> List[Path]:
    """Find all entity configuration files."""
    config_patterns = [
        "configs/entities/**/*.yaml",
        "configs/composites/*.yaml"
    ]

    configs = []
    for pattern in config_patterns:
        configs.extend(glob.glob(pattern, recursive=True))

    return [Path(c) for c in configs]


def check_outdated_patterns(docs_content: str) -> List[str]:
    """Check for outdated DSL patterns in documentation."""
    outdated_patterns = [
        "quality.content",
        "quality.consistency",
        "content_validations",
        "consistency_validations"
    ]

    issues = []
    for pattern in outdated_patterns:
        if pattern in docs_content:
            issues.append(f"❌ Outdated pattern found: '{pattern}'")

    return issues


def check_current_patterns(docs_content: str) -> List[str]:
    """Check that current DSL patterns are documented."""
    current_patterns = [
        "entity_field_validations",
        "entity_cross_field_validations",
        "entity_conditional_validations",
        "key_nullability"
    ]

    issues = []
    for pattern in current_patterns:
        if pattern not in docs_content:
            issues.append(f"❌ Missing current pattern: '{pattern}'")

    return issues


def analyze_config_structure(configs: List[Path]) -> Dict[str, Any]:
    """Analyze the actual config structure to ensure comprehensive coverage."""
    validation_types = set()
    rule_types = set()

    for config_path in configs:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if 'quality' in config:
                quality = config['quality']

                # Check for validation sections
                for section in ['entity_field_validations', 'entity_cross_field_validations',
                               'entity_conditional_validations', 'key_nullability']:
                    if section in quality:
                        validation_types.add(section)

                        # Collect rule types for field validations
                        if section == 'entity_field_validations':
                            for validation in quality[section]:
                                if 'type' in validation:
                                    rule_types.add(validation['type'])

        except yaml.YAMLError as e:
            print(f"⚠️  Warning: Could not parse {config_path}: {e}")

    return {
        'validation_types': sorted(list(validation_types)),
        'rule_types': sorted(list(rule_types))
    }


def check_documentation_coverage(docs_content: str, config_analysis: Dict[str, Any]) -> List[str]:
    """Check that all config structures are documented."""
    issues = []

    # Check validation types
    for vtype in config_analysis['validation_types']:
        if vtype not in docs_content:
            issues.append(f"❌ Validation type not documented: '{vtype}'")

    # Check rule types - verify they're actually documented in the text
    for rule_type in config_analysis['rule_types']:
        # Look for rule type in examples (type: rule_type) or in documentation (`rule_type`)
        if f'type: {rule_type}' not in docs_content and f'`{rule_type}`' not in docs_content:
            issues.append(f"❌ Rule type not documented: '{rule_type}'")

    return issues


def main() -> int:
    """Main execution function."""
    print("🔍 DQ DSL Parity Check")
    print("=" * 50)

    # Load documentation
    docs_content = load_documentation()

    # Find config files
    config_files = find_entity_configs()
    print(f"📁 Found {len(config_files)} entity configuration files")

    # Analyze config structure
    config_analysis = analyze_config_structure(config_files)
    print(f"📊 Found validation types: {', '.join(config_analysis['validation_types'])}")
    print(f"📊 Found rule types: {', '.join(config_analysis['rule_types'])}")

    # Run checks
    all_issues = []

    print("\n🔎 Checking for outdated patterns...")
    outdated_issues = check_outdated_patterns(docs_content)
    all_issues.extend(outdated_issues)

    print("🔎 Checking for current patterns...")
    current_issues = check_current_patterns(docs_content)
    all_issues.extend(current_issues)

    print("🔎 Checking documentation coverage...")
    coverage_issues = check_documentation_coverage(docs_content, config_analysis)
    all_issues.extend(coverage_issues)

    # Report results
    print("\n" + "=" * 50)
    if all_issues:
        print("❌ DQ DSL Parity Issues Found:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\n📈 Total issues: {len(all_issues)}")
        return 1
    else:
        print("✅ DQ DSL Parity Check Passed!")
        print("📋 All validation structures are properly documented")
        print("📋 No outdated patterns found")
        print("📋 Documentation covers all config structures")
        return 0


if __name__ == "__main__":
    sys.exit(main())
