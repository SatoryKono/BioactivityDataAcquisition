#!/usr/bin/env python3
"""check_doc_drift.py - Detect documentation drift between code and docs.

Verifies that key entities referenced in architecture documentation still
exist in the codebase.  Catches common drift scenarios:

  1. Port protocols renamed/removed but docs still reference old names
  2. Class names changed but architecture docs not updated
  3. Module paths moved but docs still point to old locations
  4. Provider/entity lists changed but reference docs are stale
  5. Factory/registry changes not reflected in composition docs

Usage:
    python scripts/check_doc_drift.py              # Full drift check
    python scripts/check_doc_drift.py --ports       # Only port drift
    python scripts/check_doc_drift.py --classes     # Only class drift
    python scripts/check_doc_drift.py --modules     # Only module path drift
    python scripts/check_doc_drift.py --json        # Machine-readable JSON output

Exit code: 0 = no drift, 1 = drift detected

References:
    - docs/02-architecture/ (layer documentation)
    - docs/00-project/glossary.md (ubiquitous language)
    - ADR-040 (diagram governance)
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src" / "bioetl"
DOCS_DIR = PROJECT_ROOT / "docs"


@dataclass
class DriftIssue:
    """A single documentation drift finding."""

    category: str
    severity: str  # ERROR, WARNING
    doc_file: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Serialize to dictionary."""
        return {
            "category": self.category,
            "severity": self.severity,
            "doc_file": self.doc_file,
            "detail": self.detail,
        }


@dataclass
class DriftReport:
    """Aggregated drift detection results."""

    issues: list[DriftIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of ERROR-severity issues."""
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        """Count of WARNING-severity issues."""
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def add(
        self,
        category: str,
        severity: str,
        doc_file: str,
        detail: str,
    ) -> None:
        """Append a drift issue to the report."""
        self.issues.append(DriftIssue(category, severity, doc_file, detail))

    def to_dict(self) -> dict[str, object]:
        """Serialize the full report."""
        return {
            "status": "FAIL" if self.error_count else "PASS",
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_classes(directory: Path) -> set[str]:
    """Collect all class names defined under *directory*."""
    classes: set[str] = set()
    for py in directory.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
    return classes


def _collect_modules(directory: Path) -> set[str]:
    """Collect dotted module paths under *directory* relative to src/."""
    modules: set[str] = set()
    src_root = directory
    while src_root.name != "src" and src_root != src_root.parent:
        src_root = src_root.parent
    for py in directory.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(src_root).with_suffix("")
        dotted = ".".join(rel.parts)
        modules.add(dotted)
    return modules


def _extract_backtick_refs(text: str) -> list[str]:
    """Extract all backtick-quoted references from markdown text."""
    return re.findall(r"`([^`]+)`", text)


def _read_doc(path: Path) -> str:
    """Read a documentation file, return empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Check: Port protocols
# ---------------------------------------------------------------------------

def check_ports(report: DriftReport) -> None:
    """Verify port classes referenced in domain-layer docs exist in code."""
    ports_dir = SRC_DIR / "domain" / "ports"
    if not ports_dir.exists():
        report.add(
            "ports", "ERROR", "src/bioetl/domain/ports/",
            "Ports directory does not exist",
        )
        return

    code_classes = _collect_classes(ports_dir)

    # Check domain layer doc
    doc_path = DOCS_DIR / "02-architecture" / "01-domain-layer.md"
    doc_text = _read_doc(doc_path)
    if not doc_text:
        report.add(
            "ports", "WARNING", str(doc_path.relative_to(PROJECT_ROOT)),
            "Domain layer doc not found — cannot verify port references",
        )
        return

    # Extract Port references
    refs = _extract_backtick_refs(doc_text)
    port_refs = {r for r in refs if r.endswith("Port") and r[0].isupper()}

    for port_name in sorted(port_refs):
        if port_name not in code_classes:
            report.add(
                "ports", "ERROR",
                str(doc_path.relative_to(PROJECT_ROOT)),
                f"Port `{port_name}` referenced in docs but not found in domain/ports/",
            )

    # Also check the ports __init__ facade (ARCH-008)
    init_file = ports_dir / "__init__.py"
    if init_file.exists():
        init_text = init_file.read_text(encoding="utf-8")
        for port_name in sorted(port_refs):
            if port_name in code_classes and port_name not in init_text:
                report.add(
                    "ports", "WARNING",
                    "src/bioetl/domain/ports/__init__.py",
                    f"Port `{port_name}` exists but not re-exported in ports facade",
                )


# ---------------------------------------------------------------------------
# Check: Key architecture classes
# ---------------------------------------------------------------------------

def check_classes(report: DriftReport) -> None:
    """Verify key classes referenced in architecture docs exist."""
    all_classes = _collect_classes(SRC_DIR)

    # Map doc files to expected class name patterns.
    # Names here are the *canonical code names* — checked against actual AST.
    doc_checks: list[tuple[Path, list[str]]] = [
        (
            DOCS_DIR / "02-architecture" / "02-application-layer.md",
            [
                "BasePipeline", "BaseTransformer", "RecordProcessor",
                "BatchExecutor", "PipelineRunner", "PipelineService",
                "LockCoordinator", "PreflightService", "BatchMetricsRecorderService",
                "FilteredDataSource", "CompositePipelineRunner",
                "EnrichmentCoordinatorService",
            ],
        ),
        (
            DOCS_DIR / "02-architecture" / "03-infrastructure-layer.md",
            [
                "BronzeWriter", "SilverWriter", "GoldWriter",
                "BaseHttpAdapter", "UnifiedHTTPClient",
                "TokenBucket", "CircuitBreaker", "MemoryLock",
            ],
        ),
        (
            DOCS_DIR / "02-architecture" / "05-composition-layer.md",
            [
                "GenericPipelineFactory",
            ],
        ),
    ]

    for doc_path, expected_classes in doc_checks:
        if not doc_path.exists():
            report.add(
                "classes", "WARNING",
                str(doc_path.relative_to(PROJECT_ROOT)),
                "Architecture doc not found — cannot verify class references",
            )
            continue

        doc_text = _read_doc(doc_path)
        doc_refs = set(_extract_backtick_refs(doc_text))

        for cls_name in expected_classes:
            if cls_name not in all_classes:
                report.add(
                    "classes", "ERROR",
                    str(doc_path.relative_to(PROJECT_ROOT)),
                    f"Class `{cls_name}` expected from docs but not found in codebase",
                )
            elif cls_name not in doc_refs:
                # Class exists but not mentioned — possible doc gap
                report.add(
                    "classes", "WARNING",
                    str(doc_path.relative_to(PROJECT_ROOT)),
                    f"Class `{cls_name}` exists in code but not referenced in doc",
                )


# ---------------------------------------------------------------------------
# Check: Module paths referenced in docs
# ---------------------------------------------------------------------------

def check_modules(report: DriftReport) -> None:
    """Verify module paths referenced in architecture docs resolve."""
    all_modules = _collect_modules(SRC_DIR)

    # Check all architecture docs for bioetl.* module path references
    arch_dir = DOCS_DIR / "02-architecture"
    if not arch_dir.exists():
        return

    module_pattern = re.compile(r"`(bioetl\.[a-z_.]+)`")

    for md_file in sorted(arch_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        for match in module_pattern.finditer(text):
            mod_path = match.group(1)
            # Check if any module starts with this path (could be a package)
            if not any(m == mod_path or m.startswith(mod_path + ".") for m in all_modules):
                report.add(
                    "modules", "ERROR",
                    str(md_file.relative_to(PROJECT_ROOT)),
                    f"Module path `{mod_path}` referenced but not found in src/",
                )


# ---------------------------------------------------------------------------
# Check: Provider registry
# ---------------------------------------------------------------------------

def check_providers(report: DriftReport) -> None:
    """Verify documented providers match actual adapter directories."""
    adapters_dir = SRC_DIR / "infrastructure" / "adapters"
    if not adapters_dir.exists():
        return

    # Utility sub-packages that are NOT data providers
    _NON_PROVIDER_DIRS = frozenset({
        "common", "decorators", "http", "input", "__pycache__",
    })

    actual_providers = {
        d.name
        for d in adapters_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and d.name not in _NON_PROVIDER_DIRS
    }

    # Check provider reference docs
    providers_doc = DOCS_DIR / "04-reference" / "providers"
    if not providers_doc.exists():
        return

    readme = providers_doc / "README.md"
    if not readme.exists():
        return

    doc_text = readme.read_text(encoding="utf-8")

    for provider in sorted(actual_providers):
        if provider not in doc_text and provider.replace("_", "-") not in doc_text:
            report.add(
                "providers", "WARNING",
                "docs/04-reference/providers/README.md",
                f"Provider `{provider}` has adapter but not referenced in provider docs",
            )


# ---------------------------------------------------------------------------
# Check: Glossary terms
# ---------------------------------------------------------------------------

def check_glossary(report: DriftReport) -> None:
    """Verify glossary class/module references still exist."""
    glossary_path = DOCS_DIR / "00-project" / "glossary.md"
    if not glossary_path.exists():
        return

    all_classes = _collect_classes(SRC_DIR)
    text = glossary_path.read_text(encoding="utf-8")

    # Extract class-like references from glossary, but only from the
    # "Canonical Term" / "Description" columns — skip the
    # "Deprecated / Avoid" column (the last content column in glossary tables).
    class_refs: list[str] = []
    for line in text.splitlines():
        if "|" in line:
            cols = line.split("|")
            # Table rows: ['', col1, col2, ..., colN, '']
            # Strip the last content column (Avoid/Deprecated) and trailing empty
            if len(cols) > 4:  # at least 3 content columns
                canonical_part = "|".join(cols[:-2])
            else:
                canonical_part = line
        else:
            canonical_part = line
        class_refs.extend(
            re.findall(
                r"`([A-Z][a-zA-Z]+(?:Port|Factory|Service|Writer|Reader|Adapter|Client))`",
                canonical_part,
            )
        )

    for cls_name in sorted(set(class_refs)):
        if cls_name not in all_classes:
            report.add(
                "glossary", "WARNING",
                "docs/00-project/glossary.md",
                f"Glossary references `{cls_name}` which no longer exists in codebase",
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_report(report: DriftReport) -> None:
    """Print human-readable drift report."""
    print("Documentation Drift Report")
    print("=" * 60)

    if not report.issues:
        print("No drift detected. Documentation is in sync with code.")
        return

    by_category: dict[str, list[DriftIssue]] = {}
    for issue in report.issues:
        by_category.setdefault(issue.category, []).append(issue)

    for category in sorted(by_category):
        issues = by_category[category]
        print(f"\n[{category.upper()}] ({len(issues)} issues)")
        for issue in issues:
            marker = "ERROR" if issue.severity == "ERROR" else "WARN "
            print(f"  {marker}  {issue.doc_file}")
            print(f"         {issue.detail}")

    print()
    print(
        f"Summary: {report.error_count} errors, "
        f"{report.warning_count} warnings"
    )


def main() -> int:
    """Run documentation drift detection."""
    parser = argparse.ArgumentParser(
        description="Detect documentation drift in BioETL",
    )
    parser.add_argument("--ports", action="store_true", help="Check port drift only")
    parser.add_argument("--classes", action="store_true", help="Check class drift only")
    parser.add_argument("--modules", action="store_true", help="Check module path drift only")
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args()

    report = DriftReport()

    run_all = not (args.ports or args.classes or args.modules)

    if run_all or args.ports:
        check_ports(report)
    if run_all or args.classes:
        check_classes(report)
    if run_all or args.modules:
        check_modules(report)
    if run_all:
        check_providers(report)
        check_glossary(report)

    if args.json_output:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        print()
    else:
        print_report(report)

    return 1 if report.error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
