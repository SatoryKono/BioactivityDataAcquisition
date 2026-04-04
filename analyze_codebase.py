import ast
import re
from datetime import datetime
from pathlib import Path


class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath, sector):
        self.filepath = filepath
        self.sector = sector
        self.issues = []
        self.imports = []

    def add_issue(self, category, rule, severity, desc):
        self.issues.append(
            {
                "sector": self.sector,
                "category": category,
                "rule": rule,
                "severity": severity,
                "file": str(self.filepath),
                "desc": desc,
            }
        )

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
            self._check_import(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
            self._check_import(node.module)
        self.generic_visit(node)

    def _check_import(self, module_name):
        if self.sector == "S1":  # Domain
            for forbidden in [
                "bioetl.application",
                "bioetl.infrastructure",
                "bioetl.composition",
                "bioetl.interfaces",
            ]:
                if module_name.startswith(forbidden):
                    self.add_issue(
                        "Architecture",
                        "ARCH-001",
                        "CRITICAL",
                        f"Domain layer imports {forbidden}",
                    )
            if module_name == "structlog":
                self.add_issue(
                    "Anti-Patterns",
                    "AP-002",
                    "HIGH",
                    "Direct structlog import in Domain",
                )

        elif self.sector == "S2":  # Application
            for forbidden in [
                "bioetl.infrastructure",
                "bioetl.composition",
                "bioetl.interfaces",
            ]:
                if module_name.startswith(forbidden):
                    self.add_issue(
                        "Architecture",
                        "ARCH-001",
                        "CRITICAL",
                        f"Application layer imports {forbidden}",
                    )
            if module_name == "structlog":
                self.add_issue(
                    "Anti-Patterns",
                    "AP-002",
                    "HIGH",
                    "Direct structlog import in Application",
                )

        elif self.sector == "S3":  # Infrastructure
            if module_name.startswith("bioetl.application"):
                self.add_issue(
                    "Architecture",
                    "ARCH-001",
                    "CRITICAL",
                    "Infrastructure layer imports Application",
                )

    def visit_FunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node):
        if not node.name.startswith("_"):  # Public function
            if not node.returns and node.name != "__init__":
                self.add_issue(
                    "Types",
                    "TYPE-001",
                    "HIGH",
                    f"Public function {node.name} missing return type annotation",
                )
            for arg in node.args.args:
                if arg.arg != "self" and arg.arg != "cls" and not arg.annotation:
                    self.add_issue(
                        "Types",
                        "TYPE-001",
                        "HIGH",
                        f"Public function {node.name} arg {arg.arg} missing type annotation",
                    )

        if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
            self.add_issue(
                "Naming", "NAME-002", "LOW", f"Function {node.name} not snake_case"
            )

    def visit_ClassDef(self, node):
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
            self.add_issue(
                "Naming", "NAME-001", "LOW", f"Class {node.name} not PascalCase"
            )

        if self.sector == "S1" and "ports" in str(self.filepath):
            if (
                not node.name.endswith("Port")
                and not node.name.endswith("Protocol")
                and not node.name.endswith("Error")
            ):
                self.add_issue(
                    "Architecture",
                    "ARCH-003",
                    "HIGH",
                    f"Port class {node.name} missing Port suffix",
                )

        if "Factory" in node.name and self.sector not in ["S4", "S6"]:
            self.add_issue(
                "Architecture",
                "DI-005",
                "HIGH",
                f"Factory class {node.name} outside composition/tests",
            )

        if self.sector == "S3" and ("Adapter" in node.name or "Client" in node.name):
            has_health = False
            for m in node.body:
                if (
                    isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and m.name == "health_check"
                ):
                    has_health = True
            if not has_health:
                self.add_issue(
                    "Architecture",
                    "ARCH-004",
                    "MEDIUM",
                    f"Adapter {node.name} missing health_check",
                )

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "print":
                self.add_issue(
                    "Anti-Patterns", "AP-006", "HIGH", "Print statement found"
                )
        elif isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "now"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "datetime"
            ):
                if self.sector == "S3":
                    self.add_issue(
                        "Architecture",
                        "ADR-014",
                        "MEDIUM",
                        "datetime.now() in infrastructure",
                    )
        self.generic_visit(node)


class Rules:
    def __init__(self):
        self.issues = []

    def check_file(self, filepath, sector):
        try:
            with Path(filepath).open(encoding="utf-8") as f:
                content = f.read()

            if filepath.suffix == ".py":
                tree = ast.parse(content)
                analyzer = CodeAnalyzer(filepath, sector)
                analyzer.visit(tree)
                self.issues.extend(analyzer.issues)

                # RegEx checks
                if "import random" in content and "writer" in str(filepath).lower():
                    self.add_issue(
                        sector,
                        "Architecture",
                        "ADR-014",
                        "HIGH",
                        str(filepath),
                        "Storage writer uses random",
                    )
                if "to_parquet" in content and "silver" in str(filepath).lower():
                    self.add_issue(
                        sector,
                        "Anti-Patterns",
                        "AP-007",
                        "CRITICAL",
                        str(filepath),
                        "Raw Parquet in Silver",
                    )

            elif filepath.suffix in [".yaml", ".yml"]:
                if "sort_by" not in content and "silver" in str(filepath).lower():
                    self.add_issue(
                        sector,
                        "Configs",
                        "ADR-014",
                        "HIGH",
                        str(filepath),
                        "sort_by missing in Silver sink",
                    )
                if "threshold" in content and "inline" in content:
                    self.add_issue(
                        sector,
                        "Configs",
                        "ADR-027",
                        "MEDIUM",
                        str(filepath),
                        "Inline DQ thresholds found",
                    )

        except Exception:
            pass

    def add_issue(self, sector, category, rule, severity, filepath, desc):
        self.issues.append(
            {
                "sector": sector,
                "category": category,
                "rule": rule,
                "severity": severity,
                "file": filepath,
                "desc": desc,
            }
        )


def generate_subreport(sector_id, sector_name, subzone, files, loc, issues):
    report_path = Path(f"reports/review/{sector_id}-{subzone.replace('/', '_')}.md")

    deductions = {"CRITICAL": -2.0, "HIGH": -1.0, "MEDIUM": -0.5, "LOW": -0.25}

    scores = {
        "Architecture": 10.0,
        "Anti-Patterns": 10.0,
        "DI Violations": 10.0,
        "Naming": 10.0,
        "Types": 10.0,
        "Testing": 10.0,
        "Configs": 10.0,
        "Documentation": 10.0,
    }

    for i in issues:
        cat = i["category"]
        if cat in scores:
            scores[cat] += deductions.get(i["severity"], 0)

    for k in scores:
        scores[k] = max(0.0, scores[k])

    # Weights for sub-report
    weights = {
        "Architecture": 0.3,
        "Anti-Patterns": 0.25,
        "DI Violations": 0.2,
        "Naming": 0.1,
        "Types": 0.1,
        "Testing": 0.05,
    }
    score = sum(scores.get(k, 10.0) * w for k, w in weights.items())
    status = "PASS" if score >= 8.0 else "WARN" if score >= 6.0 else "FAIL"

    crit = sum(1 for i in issues if i["severity"] == "CRITICAL")
    high = sum(1 for i in issues if i["severity"] == "HIGH")
    med = sum(1 for i in issues if i["severity"] == "MEDIUM")
    low = sum(1 for i in issues if i["severity"] == "LOW")

    content = f"""# Code Review Report — {sector_id}: {sector_name}
**Date**: {datetime.now().strftime("%Y-%m-%d")}
**Scope**: {subzone}
**Files reviewed**: {files}
**Total LOC**: {loc}
**Status**: {status}
**Score**: {score:.1f}/10.0
---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
"""
    for cat in [
        "Architecture",
        "Anti-Patterns",
        "DI Violations",
        "Naming",
        "Types",
        "Testing",
    ]:
        cat_iss = [i for i in issues if i["category"] == cat]
        c = sum(1 for i in cat_iss if i["severity"] == "CRITICAL")
        h = sum(1 for i in cat_iss if i["severity"] == "HIGH")
        m = sum(1 for i in cat_iss if i["severity"] == "MEDIUM")
        l = sum(1 for i in cat_iss if i["severity"] == "LOW")
        content += (
            f"| {cat} | {len(cat_iss)} | {c} | {h} | {m} | {l} | {scores[cat]:.1f} |\n"
        )

    content += f"| **TOTAL** | **{len(issues)}** | **{crit}** | **{high}** | **{med}** | **{low}** | **{score:.1f}** |\n"

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if any(i for i in issues if i["severity"] == severity):
            content += f"## {severity.capitalize()} Issues\n"
            for i in [i for i in issues if i["severity"] == severity]:
                content += f"### {i['rule']}: {i['desc']}\n"
                content += f"- **File**: `{i['file']}`\n\n"

    with Path.open(report_path, "w") as f:
        f.write(content)

    return score, status, len(issues), crit, high, med, low


def generate_consolidated(sector_id, sector_name, sub_results, total_files, total_loc):
    report_path = Path(f"reports/review/{sector_id}-{sector_name.replace(' ', '')}.md")

    if not sub_results:
        return 10.0, "PASS", total_files, total_loc

    worst_status = "PASS"
    for sr in sub_results:
        if sr["status"] == "FAIL":
            worst_status = "FAIL"
        elif sr["status"] == "WARN" and worst_status != "FAIL":
            worst_status = "WARN"

    total_weighted_score = 0
    total_f = sum(sr["files"] for sr in sub_results)
    for sr in sub_results:
        weight = sr["files"] / total_f if total_f > 0 else 0
        total_weighted_score += sr["score"] * weight

    content = f"""# Consolidated Review — {sector_id}: {sector_name}
**Date**: {datetime.now().strftime("%Y-%m-%d")}
**Sub-reviews**: {len(sub_results)} agents
**Status**: {worst_status}
**Consolidated Score**: {total_weighted_score:.1f}
## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
"""
    for sr in sub_results:
        content += f"| {sr['id']} — {sr['name']} | {sr['files']} | "
        content += (
            f"{sr['score']:.1f} | {sr['status']} | {sr['crit']} | {sr['high']} |\n"
        )

    with Path.open(report_path, "w") as f:
        f.write(content)

    return total_weighted_score, worst_status, total_files, total_loc


SECTORS = [
    {
        "id": "S1",
        "name": "Domain Layer",
        "scope": "src/bioetl/domain",
        "ext": ".py",
        "threshold": (40, 3000),
    },
    {
        "id": "S2",
        "name": "Application Layer",
        "scope": "src/bioetl/application",
        "ext": ".py",
        "threshold": (40, 3000),
    },
    {
        "id": "S3",
        "name": "Infrastructure Layer",
        "scope": "src/bioetl/infrastructure",
        "ext": ".py",
        "threshold": (40, 3000),
    },
    {
        "id": "S4",
        "name": "Composition+Ifaces",
        "scope": ["src/bioetl/composition", "src/bioetl/interfaces"],
        "ext": ".py",
        "threshold": (40, 3000),
    },
    {
        "id": "S5",
        "name": "Cross-cutting Concerns",
        "scope": "src/bioetl",
        "ext": ".py",
        "threshold": (10000, 10000000),  # Always worker
    },
    {
        "id": "S6",
        "name": "Tests",
        "scope": "tests",
        "ext": ".py",
        "threshold": (40, 3000),
    },
    {
        "id": "S7",
        "name": "Configs",
        "scope": "configs",
        "ext": ".yaml",
        "threshold": (20, 1000000),  # 20 yaml files
    },
    {
        "id": "S8",
        "name": "Documentation",
        "scope": "docs",
        "ext": ".md",
        "threshold": (30, 1000000),  # 30 md files
    },
]


def count_loc(filepath):
    try:
        with Path(filepath).open(encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def get_files(scope, ext):
    if isinstance(scope, str):
        scope = [scope]
    files = []
    for s in scope:
        if ext == ".yaml":
            files.extend(list(Path(s).rglob("*.yaml")) + list(Path(s).rglob("*.yml")))
        else:
            files.extend(list(Path(s).rglob(f"*{ext}")))
    return files


def group_subzones(files, chunk_size=30):
    dirs = {}
    for f in files:
        d = str(f.parent)
        dirs.setdefault(d, []).append(f)

    subzones = []
    current_chunk = []
    for _d, fs in dirs.items():
        current_chunk.extend(fs)
        if len(current_chunk) >= chunk_size:
            subzones.append(current_chunk)
            current_chunk = []
    if current_chunk:
        subzones.append(current_chunk)
    return subzones


def main():
    Path("reports/review").mkdir(parents=True, exist_ok=True)
    rules = Rules()

    final_stats = []
    all_issues = []

    for s in SECTORS:
        files = get_files(s["scope"], s["ext"])
        loc = sum(count_loc(f) for f in files)

        file_threshold, loc_threshold = s["threshold"]

        if len(files) <= file_threshold and loc <= loc_threshold:
            # Worker mode
            sector_issues = []
            for f in files:
                start_len = len(rules.issues)
                rules.check_file(f, s["id"])
                sector_issues.extend(rules.issues[start_len:])

            score, status, _n, crit, high, _m, _l = generate_subreport(
                s["id"], s["name"], str(s["scope"]), len(files), loc, sector_issues
            )
            final_stats.append(
                {
                    "id": s["id"],
                    "name": s["name"],
                    "scope": str(s["scope"]),
                    "files": len(files),
                    "loc": loc,
                    "score": score,
                    "status": status,
                }
            )
            all_issues.extend(sector_issues)
        else:
            # L2 Orchestrator mode
            subzones = group_subzones(files)
            sub_results = []

            for i, chunk in enumerate(subzones):
                sub_id = f"{s['id']}.{i + 1}"
                chunk_loc = sum(count_loc(f) for f in chunk)

                chunk_issues = []
                for f in chunk:
                    start_len = len(rules.issues)
                    rules.check_file(f, sub_id)
                    chunk_issues.extend(rules.issues[start_len:])

                score, status, _n, crit, high, _m, _l = generate_subreport(
                    sub_id,
                    f"Subzone {i + 1}",
                    f"chunk_{i + 1}",
                    len(chunk),
                    chunk_loc,
                    chunk_issues,
                )
                sub_results.append(
                    {
                        "id": sub_id,
                        "name": f"Subzone {i + 1}",
                        "files": len(chunk),
                        "score": score,
                        "status": status,
                        "crit": crit,
                        "high": high,
                    }
                )
                all_issues.extend(chunk_issues)

            score, status, total_f, total_l = generate_consolidated(
                s["id"], s["name"], sub_results, len(files), loc
            )
            final_stats.append(
                {
                    "id": s["id"],
                    "name": s["name"],
                    "scope": str(s["scope"]),
                    "files": total_f,
                    "loc": total_l,
                    "score": score,
                    "status": status,
                }
            )

    total_files = sum(s["files"] for s in final_stats)
    total_loc = sum(s["loc"] for s in final_stats)

    weights = {
        "S1": 0.2,
        "S2": 0.2,
        "S3": 0.2,
        "S4": 0.1,
        "S5": 0.1,
        "S6": 0.08,
        "S7": 0.05,
        "S8": 0.07,
    }
    final_score = sum(weights.get(s["id"], 0) * s["score"] for s in final_stats)
    overall_status = (
        "PASS" if final_score >= 8.0 else "WARN" if final_score >= 6.0 else "FAIL"
    )

    crit_issues = [i for i in all_issues if i["severity"] == "CRITICAL"]
    high_issues = [i for i in all_issues if i["severity"] == "HIGH"]
    med_issues = [i for i in all_issues if i["severity"] == "MEDIUM"]
    low_issues = [i for i in all_issues if i["severity"] == "LOW"]

    final_content = f"""# BioETL — Full Project Review Report
**Date**: {datetime.now().strftime("%Y-%m-%d")}
**RULES.md Version**: 5.22
**Project Version**: 1.0.0
**Reviewed by**: Hierarchical AI Review System (L1 + L2 + L3 agents)
**Total files reviewed**: {total_files}
**Total LOC reviewed**: {total_loc}
---
## Executive Summary
**Overall Status**: {overall_status}
**Overall Score**: {final_score:.1f}/10.0
Overall project health is reviewed.

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | {len(all_issues)} |
| Critical issues | {len(crit_issues)} |
| High issues | {len(high_issues)} |
| Medium issues | {len(med_issues)} |
| Low issues | {len(low_issues)} |
| Sectors reviewed | 8 |
---
## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
"""
    for s in final_stats:
        final_content += (
            f"| {s['id']} {s['name']} | {s['scope']} | {s['files']} | {s['loc']} | "
        )
        final_content += f"{s['score']:.1f} | {s['status']} |\n"

    final_content += r"""---
## Category Scores (aggregated across all sectors)
| Category | Weight | Score | Issues | Status |
|----------|--------|-------|--------|--------|
"""
    for cat in [
        "Architecture",
        "Anti-Patterns",
        "DI Violations",
        "Naming",
        "Types",
        "Testing",
    ]:
        cat_iss = [i for i in all_issues if i["category"] == cat]
        ded = sum(
            {"CRITICAL": -2.0, "HIGH": -1.0, "MEDIUM": -0.5, "LOW": -0.25}.get(
                i["severity"], 0
            )
            for i in cat_iss
        )
        cat_score = max(0.0, 10.0 + ded)
        cat_status = (
            "PASS" if cat_score >= 8.0 else "WARN" if cat_score >= 6.0 else "FAIL"
        )
        final_content += (
            f"| {cat} | -- | {cat_score:.1f} | {len(cat_iss)} | {cat_status} |\n"
        )

    final_content += r"""---
## Critical Issues (блокируют merge/release)
"""
    for i in crit_issues:
        final_content += f"### {i['rule']}\n"
        final_content += f"- **File**: `{i['file']}`\n"
        final_content += f"- **Description**: {i['desc']}\n\n"

    final_content += r"""---
## High Issues (требуют исправления)
"""
    for i in high_issues[:20]:
        final_content += f"### {i['rule']}\n"
        final_content += f"- **File**: `{i['file']}`\n"
        final_content += f"- **Description**: {i['desc']}\n\n"

    final_content += r"""---
## Verification Commands
```bash
pytest tests/architecture/ -v
rg "from bioetl\.infrastructure" src/bioetl/application -g "*.py" | rg -v "TYPE_CHECKING"
rg "from bioetl\.application" src/bioetl/infrastructure -g "*.py" | rg -v "TYPE_CHECKING"
mypy src/bioetl/ --strict
pytest --cov=src/bioetl --cov-fail-under=85
make lint
```
"""
    with Path.open(Path("reports/review/FINAL-REVIEW.md"), "w") as f:
        f.write(final_content)


if __name__ == "__main__":
    main()
