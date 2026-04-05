import ast
import os
import glob
from pathlib import Path
from datetime import datetime

sectors_config = [
    {"id": "S1", "name": "Domain Layer", "scope": ["src/bioetl/domain/"], "weight": 0.20},
    {"id": "S2", "name": "Application Layer", "scope": ["src/bioetl/application/"], "weight": 0.20},
    {"id": "S3", "name": "Infrastructure Layer", "scope": ["src/bioetl/infrastructure/"], "weight": 0.20},
    {"id": "S4", "name": "Composition+Interfaces", "scope": ["src/bioetl/composition/", "src/bioetl/interfaces/"], "weight": 0.10},
    {"id": "S5", "name": "Cross-cutting Concerns", "scope": ["src/bioetl/"], "weight": 0.10},
    {"id": "S6", "name": "Tests", "scope": ["tests/"], "weight": 0.08},
    {"id": "S7", "name": "Configs", "scope": ["configs/"], "weight": 0.05},
    {"id": "S8", "name": "Documentation", "scope": ["docs/"], "weight": 0.07},
]

class Analyzer(ast.NodeVisitor):
    def __init__(self, filepath, sector_id):
        self.filepath = filepath
        self.sector_id = sector_id
        self.issues = []

    def add_issue(self, cat, rule, sev, desc, line):
        self.issues.append({
            'category': cat,
            'rule': rule,
            'severity': sev,
            'description': desc,
            'line': line,
            'file': self.filepath
        })

    def visit_Import(self, node):
        for alias in node.names:
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._check_import(node.module, node.lineno)
        self.generic_visit(node)

    def _check_import(self, module, line):
        if not module or module == "TYPE_CHECKING" or "TYPE_CHECKING" in module:
            return

        if "structlog" in module and self.sector_id not in ("S3", "S6"):
            self.add_issue("Anti-Patterns", "AP-002", "HIGH", "Direct structlog import outside infrastructure", line)

        if module.startswith("bioetl."):
            parts = module.split('.')
            if len(parts) > 1:
                layer = parts[1]
                if self.sector_id == "S1" and layer in ["application", "infrastructure", "composition", "interfaces"]:
                    self.add_issue("Architecture", "ARCH-001", "CRITICAL", f"Domain layer imports {layer}", line)
                if self.sector_id == "S2" and layer in ["infrastructure", "composition", "interfaces"]:
                    self.add_issue("Architecture", "ARCH-001", "CRITICAL", f"Application layer imports {layer}", line)
                if self.sector_id == "S3" and layer in ["application", "composition", "interfaces"]:
                    self.add_issue("Architecture", "ARCH-001", "CRITICAL", f"Infrastructure layer imports {layer}", line)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "print":
                self.add_issue("Anti-Patterns", "AP-006", "MEDIUM", "Print statement found", node.lineno)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == "now" and getattr(node.func.value, "id", "") == "datetime" and self.sector_id == "S3":
                self.add_issue("Architecture", "ARCH-007", "HIGH", "datetime.now() in infrastructure", node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if not node.name.startswith("_"):
            if not node.returns:
                self.add_issue("Types", "TYPE-001", "LOW", f"Missing return type for {node.name}", node.lineno)
            if not getattr(node, "args", None) or not all(arg.annotation for arg in node.args.args if arg.arg != "self" and arg.arg != "cls"):
                self.add_issue("Types", "TYPE-002", "LOW", f"Missing parameter types for {node.name}", node.lineno)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        name = node.name
        if "Client" in name or "Port" in name or "Service" in name or "Factory" in name:
            if "Factory" in name and self.sector_id not in ["S4", "S6"]:
                self.add_issue("Architecture", "ARCH-005", "HIGH", "Factory outside composition", node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id.isupper() and any(kw in target.id for kw in ["SECRET", "PASSWORD", "TOKEN", "KEY"]):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if len(node.value.value) > 4:  # Avoid false positives for very short strings
                            self.add_issue("Anti-Patterns", "AP-005", "CRITICAL", "Hardcoded secret detected", node.lineno)
        self.generic_visit(node)

def check_yaml(filepath, sector_id):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if "inline_dq:" in line or "inline_thresholds:" in line:
                    issues.append({
                        'category': 'Architecture',
                        'rule': 'ADR-027',
                        'severity': 'MEDIUM',
                        'description': 'Inline DQ threshold detected in YAML',
                        'line': i+1,
                        'file': filepath
                    })
    except Exception:
        pass
    return issues

def check_md(filepath, sector_id):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            has_status = "Status:" in content
            has_decision = "Decision:" in content
            if "decisions" in filepath and (not has_status or not has_decision):
                issues.append({
                    'category': 'Architecture',
                    'rule': 'ADR-COMPLETENESS',
                    'severity': 'LOW',
                    'description': 'ADR missing status or decision',
                    'line': 1,
                    'file': filepath
                })
    except Exception:
        pass
    return issues

def count_loc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
    except Exception:
        return 0

def analyze_sector(sector):
    is_python = sector['id'] not in ['S7', 'S8']
    ext = '.py' if is_python else (('.yaml', '.yml') if sector['id'] == 'S7' else '.md')
    files = []
    for scope in sector['scope']:
        base_path = Path(scope)
        if not base_path.exists(): continue
        if isinstance(ext, tuple):
            for e in ext:
                files.extend([str(p) for p in base_path.rglob(f"*{e}")])
        else:
            files.extend([str(p) for p in base_path.rglob(f"*{ext}")])

    excluded = ['.venv', '.mypy_cache', '__pycache__', '.ruff_cache', '.pytest_cache', '.hypothesis']
    filtered_files = [f for f in set(files) if not any(excl in f for excl in excluded)]
    
    total_loc = 0
    issues = []
    for f in filtered_files:
        total_loc += count_loc(f)
        if f.endswith('.py'):
            try:
                content = Path(f).read_text(encoding='utf-8')
                tree = ast.parse(content)
                analyzer = Analyzer(f, sector['id'])
                analyzer.visit(tree)
                issues.extend(analyzer.issues)
            except Exception: pass
        elif f.endswith(('.yaml', '.yml')):
            issues.extend(check_yaml(f, sector['id']))
        elif f.endswith('.md'):
            issues.extend(check_md(f, sector['id']))
    return filtered_files, total_loc, issues

def format_report(sector, files, total_loc, issues):
    cat_deductions = 0
    for i in issues:
        sev = i['severity']
        if sev == 'CRITICAL': cat_deductions += 2.0
        elif sev == 'HIGH': cat_deductions += 1.0
        elif sev == 'MEDIUM': cat_deductions += 0.5
        else: cat_deductions += 0.25
    
    score = max(0.0, 10.0 - (cat_deductions / len(files) if files else 0))
    status = "PASS" if score >= 8.0 else ("WARN" if score >= 6.0 else "FAIL")
    
    report = f"# Code Review Report — {sector['id']}: {sector['name']}\n"
    report += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
    report += f"**Files**: {len(files)} | **LOC**: {total_loc} | **Score**: {score:.1f} | **Status**: {status}\n\n"
    
    crit = [i for i in issues if i['severity'] == 'CRITICAL']
    if crit:
        report += "## Critical Issues\n"
        for i in crit:
            report += f"- {i['rule']} in `{i['file']}:{i['line']}`: {i['description']}\n"
    
    return report, score, status

def main():
    os.makedirs('reports/review', exist_ok=True)
    summary_lines = []
    all_issues = []
    total_weighted_score = 0.0
    
    for sector in sectors_config:
        files, loc, issues = analyze_sector(sector)
        report, score, status = format_report(sector, files, loc, issues)
        Path(f"reports/review/{sector['id']}_{sector['name'].replace(' ', '_')}.md").write_text(report, encoding='utf-8')
        summary_lines.append(f"| {sector['id']} {sector['name']} | {len(files)} | {loc} | {score:.1f} | {status} |")
        total_weighted_score += score * sector['weight']
        all_issues.extend(issues)

    final_report = f"# BioETL — Project Audit Summary\n**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
    final_report += f"**Overall Score**: {total_weighted_score:.1f}/10.0\n\n"
    final_report += "| Sector | Files | LOC | Score | Status |\n|---|---|---|---|---|\n"
    final_report += "\n".join(summary_lines)
    Path("reports/review/SUMMARY.md").write_text(final_report, encoding='utf-8')
    print(f"Audit completed. Overall Score: {total_weighted_score:.1f}")

if __name__ == "__main__":
    main()
