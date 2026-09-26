#!/usr/bin/env python3
"""
Test script for workflow integration validation.

This script validates that:
1. All workflows exist and are properly formatted
2. Shared validation module is accessible
3. Conditional execution matrix is defined
4. Error handling strategies are in place
"""

import json
from pathlib import Path
from typing import Dict, List


def validate_workflow_structure(workflow_path: Path) -> Dict[str, any]:
    """Validate that a workflow file has the required structure."""
    if not workflow_path.exists():
        return {"valid": False, "error": "File does not exist"}
    
    content = workflow_path.read_text(encoding='utf-8')
    
    # Check for required sections
    required_sections = [
        "## Master Workflow Integration",
        "## Conditional Execution",
        "## Error Handling"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        return {
            "valid": False,
            "error": f"Missing required sections: {', '.join(missing_sections)}"
        }
    
    return {"valid": True}


def validate_shared_validation(shared_path: Path) -> Dict[str, any]:
    """Validate that shared validation module exists and has required content."""
    if not shared_path.exists():
        return {"valid": False, "error": "Shared validation file does not exist"}
    
    content = shared_path.read_text(encoding='utf-8')
    
    # Check for required validation rules
    required_rules = [
        "Architecture validation",
        "Code quality validation",
        "Secrets validation",
        "Technical debt validation"
    ]
    
    missing_rules = []
    for rule in required_rules:
        if rule not in content:
            missing_rules.append(rule)
    
    if missing_rules:
        return {
            "valid": False,
            "error": f"Missing validation rules: {', '.join(missing_rules)}"
        }
    
    return {"valid": True}


def validate_master_workflow(master_path: Path) -> Dict[str, any]:
    """Validate that master workflow has conditional execution matrix."""
    if not master_path.exists():
        return {"valid": False, "error": "Master workflow file does not exist"}
    
    content = master_path.read_text(encoding='utf-8')
    
    # Check for conditional execution matrix
    if "## Conditional Execution Matrix" not in content:
        return {"valid": False, "error": "Missing conditional execution matrix"}
    
    # Check for dependency graph
    if "## Dependency Graph" not in content:
        return {"valid": False, "error": "Missing dependency graph"}
    
    # Check for error handling strategy
    if "## Error Handling" not in content:
        return {"valid": False, "error": "Missing error handling strategy"}
    
    return {"valid": True}


def main():
    """Main validation function."""
    devin_dir = Path(__file__).parent.parent
    workflows_dir = devin_dir / "workflows"
    
    print("🔍 Testing workflow integration...\n")
    
    # Test master workflow
    print("1. Validating master workflow...")
    master_result = validate_master_workflow(workflows_dir / "master.md")
    if master_result["valid"]:
        print("   ✅ Master workflow is valid")
    else:
        print(f"   ❌ Master workflow validation failed: {master_result['error']}")
    
    # Test shared validation
    print("\n2. Validating shared validation module...")
    shared_result = validate_shared_validation(workflows_dir / "shared-validation.md")
    if shared_result["valid"]:
        print("   ✅ Shared validation module is valid")
    else:
        print(f"   ❌ Shared validation validation failed: {shared_result['error']}")
    
    # Test individual workflows
    print("\n3. Validating individual workflows...")
    workflows_to_test = [
        "post-change.md",
        "review.md", 
        "pre-commit.md",
        "qodo-sync.md"
    ]
    
    all_valid = True
    for workflow_name in workflows_to_test:
        workflow_path = workflows_dir / workflow_name
        result = validate_workflow_structure(workflow_path)
        if result["valid"]:
            print(f"   ✅ {workflow_name} is valid")
        else:
            print(f"   ❌ {workflow_name} validation failed: {result['error']}")
            all_valid = False
    
    # Test py-* skills
    print("\n4. Validating py-* skills...")
    skills_dir = devin_dir / "skills"
    py_skills = [
        "py-audit-bot",
        "py-debug-bot",
        "py-config-bot",
        "py-doc-bot",
        "py-plan-bot",
        "py-test-bot"
    ]
    
    for skill_name in py_skills:
        skill_path = skills_dir / skill_name / "SKILL.md"
        if skill_path.exists():
            content = skill_path.read_text(encoding='utf-8')
            if "## Skill vs Agent Usage" in content:
                print(f"   ✅ {skill_name} has usage guidance")
            else:
                print(f"   ⚠️  {skill_name} missing usage guidance")
        else:
            print(f"   ❌ {skill_name} skill file not found")
            all_valid = False
    
    # Test metrics system
    print("\n5. Validating metrics system...")
    metrics_path = devin_dir / "agent-metrics.json"
    if metrics_path.exists():
        with open(metrics_path, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
        
        if "mcp_servers" in metrics and len(metrics["mcp_servers"]) >= 20:
            print(f"   ✅ Metrics system has {len(metrics['mcp_servers'])} MCP servers tracked")
        else:
            print(f"   ⚠️  Metrics system has only {len(metrics.get('mcp_servers', {}))} MCP servers")
    else:
        print("   ❌ Metrics file not found")
        all_valid = False
    
    # Final result
    print("\n" + "="*50)
    if all_valid and master_result["valid"] and shared_result["valid"]:
        print("✅ All workflow integration tests passed!")
        return 0
    else:
        print("❌ Some workflow integration tests failed")
        return 1


if __name__ == "__main__":
    exit(main())