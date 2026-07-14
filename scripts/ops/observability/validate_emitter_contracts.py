#!/usr/bin/env python3
"""
Static analysis for BioETL emitter-bypass proof.
Addresses OBS-004: Emitter-Bypass Proof Gap
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Literal
from collections import defaultdict

# Configuration
DEFAULT_SOURCE_DIR = Path("src/bioetl")
DEFAULT_OUTPUT_DIR = Path("reports/observability/emitter-audit")
DEFAULT_PATTERNS_FILE = Path("scripts/ops/observability/emitter-bypass-patterns.json")

@dataclass
class EmitterViolation:
    """Single emitter contract violation."""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    code_snippet: str
    severity: Literal["error", "warning", "info"]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(tz=UTC).isoformat()

@dataclass
class EmitterAuditReport:
    """Complete emitter audit report."""
    source_dir: str
    timestamp: str
    violations: list[EmitterViolation]
    summary: dict[str, Any]

# Forbidden patterns for emitter bypass
FORBIDDEN_PATTERNS = {
    "direct_prometheus_import": {
        "pattern": r"from prometheus_client import|import prometheus_client",
        "description": "Direct Prometheus client import - use canonical emitter contracts",
        "severity": "error"
    },
    "direct_statsd_import": {
        "pattern": r"from statsd import|import statsd",
        "description": "Direct StatsD import - use canonical emitter contracts",
        "severity": "error"
    },
    "direct_logging_import": {
        "pattern": r"from logging import|import logging",
        "description": "Direct logging import - use UnifiedLogger from observability layer",
        "severity": "warning"
    },
    "print_statement": {
        "pattern": r"\bprint\s*\(",
        "description": "Print statement - use structured logging via UnifiedLogger",
        "severity": "warning"
    },
    "direct_http_post": {
        "pattern": r"requests\.post|httpx\.post",
        "description": "Direct HTTP POST for metrics - use canonical emitter contracts",
        "severity": "error"
    },
    "prometheus_counter_direct": {
        "pattern": r"Counter\(|Gauge\(|Histogram\(|Summary\(",
        "description": "Direct Prometheus metric creation - use canonical emitter contracts",
        "severity": "error"
    }
}

# Allowed import patterns
ALLOWED_IMPORTS = {
    "bioetl.observability",
    "bioetl.infrastructure.logging",
    "bioetl.interfaces.logging"
}

class EmitterAnalyzer(ast.NodeVisitor):
    """AST analyzer for emitter contract violations."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[EmitterViolation] = []
        self.imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Check regular imports."""
        for alias in node.names:
            self.imports.add(alias.name)
            self._check_forbidden_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from imports."""
        module = node.module or ""
        self.imports.add(module)
        self._check_forbidden_import(module, node.lineno)

        for alias in node.names:
            full_import = f"{module}.{alias.name}" if module else alias.name
            self._check_forbidden_import(full_import, node.lineno)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for forbidden patterns."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self._check_forbidden_call(func_name, node.lineno)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                func_name = f"{node.func.value.id}.{node.func.attr}"
                self._check_forbidden_call(func_name, node.lineno)

        self.generic_visit(node)

    def _check_forbidden_import(self, import_name: str, line_no: int) -> None:
        """Check if import is forbidden."""
        for pattern_name, pattern_config in FORBIDDEN_PATTERNS.items():
            if "import" in pattern_name:
                if re.search(pattern_config["pattern"], import_name):
                    self.violations.append(EmitterViolation(
                        file_path=self.file_path,
                        line_number=line_no,
                        violation_type=pattern_name,
                        description=pattern_config["description"],
                        code_snippet=import_name,
                        severity=pattern_config["severity"]
                    ))

    def _check_forbidden_call(self, func_name: str, line_no: int) -> None:
        """Check if function call is forbidden."""
        for pattern_name, pattern_config in FORBIDDEN_PATTERNS.items():
            if "import" not in pattern_name:
                if re.search(pattern_config["pattern"], func_name):
                    self.violations.append(EmitterViolation(
                        file_path=self.file_path,
                        line_number=line_no,
                        violation_type=pattern_name,
                        description=pattern_config["description"],
                        code_snippet=func_name,
                        severity=pattern_config["severity"]
                    ))

def analyze_file(file_path: Path) -> list[EmitterViolation]:
    """Analyze a single Python file for emitter violations."""
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        analyzer = EmitterAnalyzer(str(file_path))
        analyzer.visit(tree)
        violations = analyzer.violations
    except SyntaxError as e:
        violations.append(EmitterViolation(
            file_path=str(file_path),
            line_number=e.lineno or 0,
            violation_type="syntax_error",
            description=f"Syntax error in file: {e.msg}",
            code_snippet="",
            severity="error"
        ))
    except Exception as e:
        violations.append(EmitterViolation(
            file_path=str(file_path),
            line_number=0,
            violation_type="analysis_error",
            description=f"Analysis error: {e}",
            code_snippet="",
            severity="error"
        ))

    return violations

def analyze_directory(source_dir: Path) -> list[EmitterViolation]:
    """Analyze all Python files in directory."""
    all_violations = []

    for py_file in sorted(source_dir.rglob("*.py")):
        violations = analyze_file(py_file)
        all_violations.extend(violations)

    return all_violations

def generate_summary(violations: list[EmitterViolation]) -> dict[str, Any]:
    """Generate summary statistics."""
    total = len(violations)
    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")
    info = sum(1 for v in violations if v.severity == "info")

    # Group by violation type
    by_type = defaultdict(int)
    for v in violations:
        by_type[v.violation_type] += 1

    # Group by file
    by_file = defaultdict(int)
    for v in violations:
        by_file[v.file_path] += 1

    return {
        "total_violations": total,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "by_type": dict(by_type),
        "by_file": dict(by_file),
        "files_with_violations": len(by_file)
    }

def run_emitter_audit(source_dir: Path) -> EmitterAuditReport:
    """Run complete emitter contract audit."""
    violations = analyze_directory(source_dir)
    summary = generate_summary(violations)

    return EmitterAuditReport(
        source_dir=str(source_dir),
        timestamp=datetime.now(tz=UTC).isoformat(),
        violations=violations,
        summary=summary
    )

def main():
    parser = argparse.ArgumentParser(
        description="Static analysis for BioETL emitter-bypass proof (OBS-004)"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Source directory to analyze"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for audit report"
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run audit
    print(f"Starting emitter contract audit...")
    print(f"Source directory: {args.source_dir}")
    print()

    report = run_emitter_audit(args.source_dir)

    # Print results
    print("Audit Results:")
    print("=" * 60)
    print(f"Total violations: {report.summary['total_violations']}")
    print(f"Errors: {report.summary['errors']}")
    print(f"Warnings: {report.summary['warnings']}")
    print(f"Files with violations: {report.summary['files_with_violations']}")
    print()

    if report.summary['by_type']:
        print("Violations by type:")
        print("=" * 60)
        for vtype, count in sorted(report.summary['by_type'].items()):
            print(f"  {vtype}: {count}")
        print()

    if report.violations:
        print("Detailed violations:")
        print("=" * 60)
        for violation in report.violations[:20]:  # Show first 20
            print(f"  [{violation.severity.upper()}] {violation.file_path}:{violation.line_number}")
            print(f"    Type: {violation.violation_type}")
            print(f"    Description: {violation.description}")
            print(f"    Code: {violation.code_snippet}")
            print()

        if len(report.violations) > 20:
            print(f"  ... and {len(report.violations) - 20} more violations")
    else:
        print("No violations found - emitter contracts are compliant!")

    # Save report
    report_path = args.output_dir / f"emitter-audit-report-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    print(f"\nReport saved to: {report_path}")

    # Exit with appropriate code
    if report.summary["errors"] > 0:
        sys.exit(1)
    elif report.summary["warnings"] > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
