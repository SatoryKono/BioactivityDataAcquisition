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
# Compatibility wrapper

import glob
import sys
from pathlib import Path
from typing import Any

import yaml

VALIDATION_SECTIONS = {
    "entity_field_validations",
    "entity_cross_field_validations",
    "entity_conditional_validations",
    "key_nullability",
}


def load_documentation() -> str:
    """Load DQ contracts documentation."""
    docs_path = Path("docs/04-reference/contracts/dq-contracts.md")
    try:
        with open(docs_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] Documentation file not found: {docs_path}")
        sys.exit(1)


def find_entity_configs() -> list[Path]:
    """Find all entity configuration files."""
    config_patterns = ["configs/entities/**/*.yaml", "configs/composites/*.yaml"]

    configs = []
    for pattern in config_patterns:
        configs.extend(glob.glob(pattern, recursive=True))

    return [Path(c) for c in configs]


def check_outdated_patterns(docs_content: str) -> list[str]:
    """Check for outdated DSL patterns in documentation."""
    outdated_patterns = [
        "quality.content",
        "quality.consistency",
        "content_validations",
        "consistency_validations",
    ]

    issues = []
    for pattern in outdated_patterns:
        if pattern in docs_content:
            issues.append(f"[ERROR] Outdated pattern found: '{pattern}'")

    return issues


def check_current_patterns(docs_content: str) -> list[str]:
    """Check that current DSL patterns are documented."""
    current_patterns = [
        "entity_field_validations",
        "entity_cross_field_validations",
        "entity_conditional_validations",
        "key_nullability",
    ]

    issues = []
    for pattern in current_patterns:
        if pattern not in docs_content:
            issues.append(f"[ERROR] Missing current pattern: '{pattern}'")

    return issues


def _load_docs_and_configs() -> tuple[str, list[Path]]:
    return load_documentation(), find_entity_configs()


def _print_config_analysis(config_analysis: dict[str, Any]) -> None:
    print(
        f"[INFO] Found validation types: {', '.join(config_analysis['validation_types'])}"
    )
    print(f"[INFO] Found rule types: {', '.join(config_analysis['rule_types'])}")


def _collect_parity_issues(
    docs_content: str,
    config_analysis: dict[str, Any],
) -> list[str]:
    issues = []
    issues.extend(check_outdated_patterns(docs_content))
    issues.extend(check_current_patterns(docs_content))
    issues.extend(check_documentation_coverage(docs_content, config_analysis))
    return issues


def _print_parity_report(all_issues: list[str]) -> None:
    print("\n" + "=" * 50)
    if all_issues:
        print("❌ DQ DSL Parity Issues Found:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\n📈 Total issues: {len(all_issues)}")
        return
    print("✅ DQ DSL Parity Check Passed!")
    print("📋 All validation structures are properly documented")
    print("📋 No outdated patterns found")
    print("📋 Documentation covers all config structures")


def _load_inputs() -> tuple[str, list[Path]]:
    return _load_docs_and_configs()


def _analyze_inputs(config_files: list[Path]) -> dict[str, Any]:
    return analyze_config_structure(config_files)


def _check_parity(
    docs_content: str,
    config_analysis: dict[str, Any],
) -> list[str]:
    return _collect_parity_issues(docs_content, config_analysis)


def _report_parity(issues: list[str]) -> None:
    _print_parity_report(issues)


def _collect_field_validation_rule_types(
    validations: list[dict[str, Any]], rule_types: set[str]
) -> None:
    """Collect the field-validation rule types present in a quality block."""
    for validation in validations:
        if "type" in validation:
            rule_types.add(validation["type"])


def _collect_quality_validation_types(
    quality: dict[str, Any],
    validation_types: set[str],
    rule_types: set[str],
) -> None:
    """Collect validation sections and field rule types from a quality block."""
    for section in VALIDATION_SECTIONS.intersection(quality):
        validation_types.add(section)
        if section == "entity_field_validations":
            _collect_field_validation_rule_types(quality[section], rule_types)


def _collect_config_structure(
    config_path: Path,
    validation_types: set[str],
    rule_types: set[str],
) -> None:
    """Process one config file and collect its quality structure."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"⚠️  Warning: Could not parse {config_path}: {e}")
        return

    if isinstance(config, dict) and "quality" in config:
        _collect_quality_validation_types(
            config["quality"],
            validation_types,
            rule_types,
        )


def analyze_config_structure(configs: list[Path]) -> dict[str, Any]:
    """Analyze the actual config structure to ensure comprehensive coverage."""
    validation_types = set()
    rule_types = set()

    for config_path in configs:
        _collect_config_structure(config_path, validation_types, rule_types)

    return {
        "validation_types": sorted(validation_types),
        "rule_types": sorted(rule_types),
    }


def check_documentation_coverage(
    docs_content: str, config_analysis: dict[str, Any]
) -> list[str]:
    """Check that all config structures are documented."""
    issues = [
        f"❌ Validation type not documented: '{vtype}'"
        for vtype in config_analysis["validation_types"]
        if vtype not in docs_content
    ]
    issues.extend(
        f"❌ Rule type not documented: '{rule_type}'"
        for rule_type in config_analysis["rule_types"]
        if f"type: {rule_type}" not in docs_content
        and f"`{rule_type}`" not in docs_content
    )
    return issues


def main() -> int:
    """Main execution function."""
    print("DQ DSL Parity Check")
    print("=" * 50)

    docs_content, config_files = _load_inputs()
    print(f"Found {len(config_files)} entity configuration files")

    config_analysis = _analyze_inputs(config_files)
    _print_config_analysis(config_analysis)
    print("\n🔎 Checking parity...")
    all_issues = _check_parity(docs_content, config_analysis)
    _report_parity(all_issues)
    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main())
