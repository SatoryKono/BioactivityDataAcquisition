#!/usr/bin/env python3
"""
Documentation Governance Check Script

Implements comprehensive documentation governance checks for BioETL project.
Validates documentation against the governance framework and quality standards.
"""

import os
import sys
import json
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import subprocess
from datetime import datetime


@dataclass
class GovernanceCheckResult:
    """Result of a governance check."""
    
    passed: bool
    checks_run: int
    checks_passed: int
    checks_failed: int
    warnings: List[str]
    errors: List[str]
    
    def get_score(self) -> float:
        """Calculate governance score (0-100)."""
        return (self.checks_passed / self.checks_run * 100) if self.checks_run > 0 else 100.0
    
    def get_grade(self) -> str:
        """Get letter grade based on score."""
        score = self.get_score()
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class DocumentationGovernanceChecker:
    """Main class for documentation governance checking."""
    
    def __init__(self):
        self.docs_dir = Path("docs")
        self.configs_dir = Path("configs")
        self.scripts_dir = Path("scripts")
        self.audit_timestamp = datetime.now().isoformat()
        
        # Governance rules configuration
        self.governance_rules = {
            "documentation_parity": {
                "threshold": 95.0,
                "critical_threshold": 85.0,
                "weight": 0.3
            },
            "terminology_consistency": {
                "threshold": 98.0,
                "weight": 0.2
            },
            "link_validity": {
                "threshold": 99.0,
                "weight": 0.2
            },
            "metadata_completeness": {
                "threshold": 95.0,
                "weight": 0.15
            },
            "structure_compliance": {
                "threshold": 98.0,
                "weight": 0.15
            }
        }
    
    def check_documentation_parity(self) -> Tuple[bool, List[str], List[str]]:
        """Check documentation parity with code and configuration."""
        
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Check if docs_parity_check.py exists and is executable
        parity_script = self.scripts_dir / "docs_parity_check.py"
        if not parity_script.exists():
            checks_failed.append("docs_parity_check.py script not found")
            return (False, warnings, checks_failed)
        
        try:
            # Run the parity check script
            subprocess.run(
                ["python3", str(parity_script)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse the JSON report
            report_file = self.docs_dir / "reports" / "docs-parity-report.json"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    report = json.load(f)
                
                parity_percentage = report["metrics"]["parity_percentage"]
                status = report["status"]
                
                if status == "pass":
                    checks_passed.append(f"Documentation parity check passed ({parity_percentage:.1f}%)")
                    return (True, warnings, checks_passed)
                elif status == "warning":
                    warnings.append(f"Documentation parity warning ({parity_percentage:.1f}%)")
                    return (True, warnings, checks_passed)
                else:
                    checks_failed.append(f"Documentation parity check failed ({parity_percentage:.1f}%)")
                    return (False, warnings, checks_failed)
            else:
                checks_failed.append("Parity report not generated")
                return (False, warnings, checks_failed)
                
        except Exception as e:
            checks_failed.append(f"Error running parity check: {e}")
            return (False, warnings, checks_failed)
    
    def check_terminology_consistency(self) -> Tuple[bool, List[str], List[str]]:
        """Check terminology consistency across documentation."""
        
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Define canonical terminology
        canonical_terms = {
            "document": "publication",
            "documents": "publications",
            "document similarity": "publication similarity",
            "document term": "publication term"
        }
        
        # Check API documentation for legacy terminology
        api_docs = [
            self.docs_dir / "04-reference" / "api" / "application.md",
            self.docs_dir / "04-reference" / "api" / "domain.md",
            self.docs_dir / "04-reference" / "api" / "composition.md"
        ]
        
        legacy_term_found = False
        
        for doc_file in api_docs:
            if doc_file.exists():
                content = doc_file.read_text()
                for legacy_term, canonical_term in canonical_terms.items():
                    if legacy_term in content.lower():
                        checks_failed.append(f"Legacy term '{legacy_term}' found in {doc_file}")
                        legacy_term_found = True
        
        if not legacy_term_found:
            checks_passed.append("No legacy terminology found in API documentation")
        
        return (not legacy_term_found, warnings, checks_passed if not legacy_term_found else checks_failed)
    
    def check_link_validity(self) -> Tuple[bool, List[str], List[str]]:
        """Check for broken links in documentation."""
        
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Check if link checking script exists
        link_check_script = self.scripts_dir / "check_doc_links.py"
        if link_check_script.exists():
            checks_passed.append("Link checking script available")
        else:
            warnings.append("Link checking script not found")
        
        # Check for common broken link patterns
        doc_files = list(self.docs_dir.rglob("*.md"))
        broken_links_found = False
        
        for doc_file in doc_files:
            content = doc_file.read_text()
            
            # Check for common broken link patterns
            if "<link-or-path>" in content:
                checks_failed.append(f"Placeholder link found in {doc_file}")
                broken_links_found = True
            
            # Check for HTTP links (should be HTTPS)
            if re.findall(r'http://(?!localhost|127\.0\.0\.1)', content):
                warnings.append(f"HTTP link found in {doc_file}")
        
        if not broken_links_found:
            checks_passed.append("No obvious broken links found")
        
        return (not broken_links_found, warnings, checks_passed if not broken_links_found else checks_failed)
    
    def check_metadata_completeness(self) -> Tuple[bool, List[str], List[str]]:
        """Check documentation metadata completeness."""
        
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Check key documentation files for required metadata
        required_docs = [
            self.docs_dir / "00-project" / "DOCUMENTATION_GOVERNANCE.md",
            self.docs_dir / "04-reference" / "contracts" / "README.md",
            self.docs_dir / "02-architecture" / "decisions" / "ADR-045-dq-contract-system.md"
        ]
        
        missing_metadata = False
        
        for doc_file in required_docs:
            if doc_file.exists():
                content = doc_file.read_text()
                
                # Check for basic metadata
                if not content.startswith("# "):
                    checks_failed.append(f"Missing title in {doc_file}")
                    missing_metadata = True
                
                # Check for last updated information
                if "Last Updated" not in content and "last updated" not in content.lower():
                    warnings.append(f"Missing last updated info in {doc_file}")
            else:
                checks_failed.append(f"Required documentation file missing: {doc_file}")
                missing_metadata = True
        
        if not missing_metadata:
            checks_passed.append("Required documentation metadata present")
        
        return (not missing_metadata, warnings, checks_passed if not missing_metadata else checks_failed)
    
    def check_structure_compliance(self) -> Tuple[bool, List[str], List[str]]:
        """Check documentation structure compliance."""
        
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Check that key directories exist
        required_dirs = [
            self.docs_dir / "00-project",
            self.docs_dir / "01-requirements",
            self.docs_dir / "02-architecture",
            self.docs_dir / "03-guides",
            self.docs_dir / "04-reference",
            self.docs_dir / "05-operations"
        ]
        
        structure_compliant = True
        
        for req_dir in required_dirs:
            if not req_dir.exists():
                checks_failed.append(f"Required directory missing: {req_dir}")
                structure_compliant = False
        
        # Check for ADR registry
        adr_registry = self.docs_dir / "02-architecture" / "adr-registry"
        if not adr_registry.exists():
            warnings.append("ADR registry directory not found")
        else:
            checks_passed.append("ADR registry structure present")
        
        # Check for contracts registry
        contracts_registry = self.docs_dir / "04-reference" / "contracts" / "README.md"
        if not contracts_registry.exists():
            checks_failed.append("Contracts registry missing")
            structure_compliant = False
        else:
            checks_passed.append("Contracts registry structure present")
        
        return (structure_compliant, warnings, checks_passed if structure_compliant else checks_failed)
    
    def run_all_checks(self) -> GovernanceCheckResult:
        """Run all governance checks and return combined result."""
        
        all_checks_passed = []
        all_checks_failed = []
        all_warnings = []
        
        # Run each check
        checks = [
            ("Documentation Parity", self.check_documentation_parity),
            ("Terminology Consistency", self.check_terminology_consistency),
            ("Link Validity", self.check_link_validity),
            ("Metadata Completeness", self.check_metadata_completeness),
            ("Structure Compliance", self.check_structure_compliance)
        ]
        
        for check_name, check_func in checks:
            print(f"🔍 Running {check_name} check...")
            passed, warnings, results = check_func()
            
            if passed:
                all_checks_passed.extend(results)
            else:
                all_checks_failed.extend(results)
            
            all_warnings.extend(warnings)
        
        total_checks = len(all_checks_passed) + len(all_checks_failed)
        
        return GovernanceCheckResult(
            passed=len(all_checks_failed) == 0,
            checks_run=total_checks,
            checks_passed=len(all_checks_passed),
            checks_failed=len(all_checks_failed),
            warnings=all_warnings,
            errors=all_checks_failed
        )
    
    def generate_report(self, result: GovernanceCheckResult) -> str:
        """Generate governance check report."""
        
        report = []
        report.append("# 📋 Documentation Governance Check Report")
        report.append("")
        report.append(f"**Generated**: {self.audit_timestamp}")
        report.append(f"**Overall Score**: {result.get_score():.1f}/100 ({result.get_grade()})")
        report.append("")
        
        # Add status badge
        if result.passed:
            report.append("🟢 **Status: PASS - Governance requirements met**")
        else:
            report.append("🔴 **Status: FAIL - Governance issues detected**")
        
        report.append("")
        report.append("## 📊 Check Results")
        report.append("")
        report.append("| Check Category | Status | Details |")
        report.append("|----------------|--------|---------|")
        
        # Individual check results would go here
        # For now, show summary
        report.append(f"| Overall | {'PASS' if result.passed else 'FAIL'} | {result.checks_passed}/{result.checks_run} checks passed |")
        
        report.append("")
        
        # Add warnings section
        if result.warnings:
            report.append("## ⚠️  Warnings")
            report.append("")
            for warning in result.warnings:
                report.append(f"- {warning}")
            report.append("")
        
        # Add errors section
        if result.errors:
            report.append("## ❌ Errors")
            report.append("")
            for error in result.errors:
                report.append(f"- {error}")
            report.append("")
        
        # Add recommendations
        report.append("## 🎯 Recommendations")
        report.append("")
        
        if result.passed:
            report.append("- ✅ Continue maintaining documentation governance")
            report.append("- 🔄 Run checks regularly to prevent drift")
            report.append("- 📊 Monitor governance metrics over time")
        else:
            report.append("- 🔴 Address critical governance issues immediately")
            report.append("- 🟡 Review warnings for potential improvements")
            report.append("- 📋 Implement automated governance checks in CI/CD")
            report.append("- 📈 Track progress on governance improvements")
        
        report.append("")
        report.append("## 📋 Governance Metrics")
        report.append("")
        report.append("| Metric | Target | Actual | Status |")
        report.append("|--------|--------|--------|--------|")
        
        # Calculate weighted score
        weighted_score = result.get_score()
        
        for rule_name, rule_config in self.governance_rules.items():
            # This would be more accurate with individual rule results
            # For now, show overall status
            status = "✅ PASS" if weighted_score >= rule_config["threshold"] else "❌ FAIL"
            report.append(f"| {rule_name.replace('_', ' ').title()} | {rule_config['threshold']}% | {weighted_score:.1f}% | {status} |")
        
        return "\n".join(report)
    
    def generate_json_report(self, result: GovernanceCheckResult) -> Dict:
        """Generate JSON report for CI/CD integration."""
        
        return {
            "timestamp": self.audit_timestamp,
            "governance_score": result.get_score(),
            "governance_grade": result.get_grade(),
            "status": "pass" if result.passed else "fail",
            "metrics": {
                "checks_run": result.checks_run,
                "checks_passed": result.checks_passed,
                "checks_failed": result.checks_failed,
                "warning_count": len(result.warnings),
                "error_count": len(result.errors)
            },
            "warnings": result.warnings,
            "errors": result.errors,
            "governance_rules": self.governance_rules
        }


def main():
    """Main entry point."""
    
    print("🚀 Running Documentation Governance Checks")
    print("=" * 50)
    
    checker = DocumentationGovernanceChecker()
    result = checker.run_all_checks()
    
    # Generate reports
    markdown_report = checker.generate_report(result)
    json_report = checker.generate_json_report(result)
    
    # Output markdown report
    print(markdown_report)
    
    # Write JSON report
    reports_dir = checker.docs_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = reports_dir / "governance_check_report.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2)
    
    print(f"\n📊 JSON report written to: {json_file}")
    
    # Exit with appropriate code
    if result.passed:
        print("\n✅ Governance checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Governance checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
