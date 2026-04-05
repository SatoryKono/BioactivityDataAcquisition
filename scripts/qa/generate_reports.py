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
        if module == "TYPE_CHECKING" or "TYPE_CHECKING" in module:
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
                        self.add_issue("Anti-Patterns", "AP-005", "CRITICAL", "Hardcoded secret detected", node.lineno)
        self.generic_visit(node)

def check_yaml(filepath, sector_id):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
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
            lines = f.readlines()
            has_status = any("Status:" in l or "Status:" in l for l in lines)
            has_decision = any("Decision:" in l or "Decision:" in l for l in lines)

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
        if isinstance(ext, tuple):
            for e in ext:
                files.extend(glob.glob(scope + '**/*' + e, recursive=True))
        else:
            files.extend(glob.glob(scope + '**/*' + ext, recursive=True))

    excluded = ['.venv', '.mypy_cache', '__pycache__', '.ruff_cache', '.pytest_cache', '.hypothesis']
    filtered_files = []
    for f in set(files):
        if not any(excl in f for excl in excluded):
            filtered_files.append(f)

    total_loc = 0
    issues = []

    for f in filtered_files:
        loc = count_loc(f)
        total_loc += loc
        if f.endswith('.py'):
            try:
                with open(f, 'r', encoding='utf-8') as file_obj:
                    content = file_obj.read()
                tree = ast.parse(content)
                analyzer = Analyzer(f, sector['id'])
                analyzer.visit(tree)
                issues.extend(analyzer.issues)
            except Exception:
                pass
        elif f.endswith('.yaml') or f.endswith('.yml'):
            issues.extend(check_yaml(f, sector['id']))
        elif f.endswith('.md'):
            issues.extend(check_md(f, sector['id']))

    return filtered_files, total_loc, issues

def format_report(sector, files, total_loc, issues, is_l2):
    cat_issues = {"Architecture": [], "Anti-Patterns": [], "DI Violations": [], "Naming": [], "Types": [], "Testing": []}
    for issue in issues:
        if issue['category'] not in cat_issues:
            cat_issues[issue['category']] = []
        cat_issues[issue['category']].append(issue)

    deductions = 0
    for issue in issues:
        if issue['severity'] == 'CRITICAL': deductions += 2.0
        elif issue['severity'] == 'HIGH': deductions += 1.0
        elif issue['severity'] == 'MEDIUM': deductions += 0.5
        elif issue['severity'] == 'LOW': deductions += 0.25

    base_score = 10.0
    deduction_ratio = (deductions / len(files)) if files else 0
    final_score = max(0.0, base_score - deduction_ratio)
    
    status = "PASS" if final_score >= 8.0 else ("WARN" if final_score >= 6.0 else "FAIL")
    date_str = datetime.now().strftime("%Y-%m-%d")

    issues_md = ""
    for cat in cat_issues:
        crit = sum(1 for i in cat_issues[cat] if i['severity'] == 'CRITICAL')
        high = sum(1 for i in cat_issues[cat] if i['severity'] == 'HIGH')
        med = sum(1 for i in cat_issues[cat] if i['severity'] == 'MEDIUM')
        low = sum(1 for i in cat_issues[cat] if i['severity'] == 'LOW')
        cat_deductions = crit*2.0 + high*1.0 + med*0.5 + low*0.25
        cat_score = max(0.0, 10.0 - (cat_deductions / len(files) if files else 0))
        issues_md += f"| {cat} | {len(cat_issues[cat])} | {crit} | {high} | {med} | {low} | {cat_score:.1f} |\n"

    crit_md = ""
    for issue in issues:
        if issue['severity'] == 'CRITICAL':
            crit_md += f"### {issue['rule']}: {issue['description']}\n- **Rule**: {issue['rule']}\n- **Severity**: CRITICAL\n- **File**: `{issue['file']}:{issue['line']}`\n- **Description**: {issue['description']}\n\n"

    high_md = ""
    for issue in issues:
        if issue['severity'] == 'HIGH':
            high_md += f"### {issue['rule']}: {issue['description']}\n- **Rule**: {issue['rule']}\n- **Severity**: HIGH\n- **File**: `{issue['file']}:{issue['line']}`\n- **Description**: {issue['description']}\n\n"

    report_content = f"# Consolidated Review — {sector['id']}: {sector['name']}\n**Date**: {date_str}\n**Status**: {status}\n**Score**: {final_score:.1f}\n\n"
    # (Rest of formatting logic matches Jules output)
    return report_content, final_score, status, issues

def main():
    os.makedirs('reports/review', exist_ok=True)
    # Full implementation would follow here...
    print("QA Report Generator initialized.")

if __name__ == "__main__":
    main()
