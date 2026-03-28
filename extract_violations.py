import os
import glob
from pathlib import Path
import json
import ast
import re

sectors = {
    'S1-DomainLayer': {'name': 'Domain Layer', 'patterns': ['src/bioetl/domain/**/*.py']},
    'S2-ApplicationLayer': {'name': 'Application Layer', 'patterns': ['src/bioetl/application/**/*.py']},
    'S3-InfrastructureLayer': {'name': 'Infrastructure Layer', 'patterns': ['src/bioetl/infrastructure/**/*.py']},
    'S4-Composition+Interfaces': {'name': 'Composition + Interfaces', 'patterns': ['src/bioetl/composition/**/*.py', 'src/bioetl/interfaces/**/*.py']},
    'S5-Cross-cuttingConcerns': {'name': 'Cross-cutting Concerns', 'patterns': ['src/bioetl/**/*.py']},
    'S6-Tests': {'name': 'Tests', 'patterns': ['tests/**/*.py']},
    'S7-Configs': {'name': 'Configs', 'patterns': ['configs/**/*.yaml', 'configs/**/*.yml']},
    'S8-Documentation': {'name': 'Documentation', 'patterns': ['docs/**/*.md']}
}

class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath, sector_id):
        self.filepath = filepath
        self.sector_id = sector_id
        self.issues = []

    def visit_Import(self, node):
        self._check_imports(node.names, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._check_imports([ast.alias(name=node.module, asname=None)], node.lineno)
        self.generic_visit(node)

    def _check_imports(self, names, lineno):
        for alias in names:
            module = alias.name
            if self.sector_id == 'S1-DomainLayer':
                if any(bad in module for bad in ['bioetl.infrastructure', 'bioetl.application', 'requests', 'httpx']):
                    self.issues.append({'type': 'CRITICAL', 'rule': 'ARCH-002', 'msg': f'Domain purity violation: imported {module}', 'file': self.filepath, 'line': lineno})
            if self.sector_id in ['S1-DomainLayer', 'S2-ApplicationLayer', 'S4-Composition+Interfaces']:
                if 'structlog' in module:
                    self.issues.append({'type': 'HIGH', 'rule': 'AP-002', 'msg': 'Direct structlog import outside infra', 'file': self.filepath, 'line': lineno})
            if self.sector_id == 'S2-ApplicationLayer':
                if 'bioetl.infrastructure' in module:
                    self.issues.append({'type': 'CRITICAL', 'rule': 'ARCH-001', 'msg': 'Application imported infra', 'file': self.filepath, 'line': lineno})

    def visit_ClassDef(self, node):
        name = node.name
        if self.sector_id == 'S1-DomainLayer' and 'domain/ports' in self.filepath:
            if not name.endswith('Port') and not name.endswith('Exception'):
                self.issues.append({'type': 'MEDIUM', 'rule': 'NAME-001', 'msg': f'Port {name} missing suffix', 'file': self.filepath, 'line': node.lineno})
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.issues.append({'type': 'MEDIUM', 'rule': 'AP-006', 'msg': 'Print statement found', 'file': self.filepath, 'line': node.lineno})
        self.generic_visit(node)

results = {}

for sector_id, info in sectors.items():
    files = []
    for p in info['patterns']:
        files.extend(glob.glob(p, recursive=True))
    files = list(set(files))

    loc = 0
    issues = []

    for f in files:
        if not os.path.isfile(f): continue
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
            lines = content.split('\n')
            loc += len(lines)

            if f.endswith('.py'):
                if not any('from __future__ import annotations' in l for l in lines[:30]):
                    issues.append({'type': 'LOW', 'rule': 'ADR-014', 'msg': 'Missing future annotations', 'file': f, 'line': 1})

                for i, l in enumerate(lines):
                    if re.search(r'password\s*=\s*["\'][^"\']+["\']', l, re.I):
                        issues.append({'type': 'CRITICAL', 'rule': 'AP-005', 'msg': 'Hardcoded password', 'file': f, 'line': i+1})

                try:
                    tree = ast.parse(content)
                    analyzer = ASTAnalyzer(f, sector_id)
                    analyzer.visit(tree)
                    issues.extend(analyzer.issues)
                except Exception:
                    pass
        except Exception:
            pass

    # Sample up to 5 issues per sector to keep context small
    # but aggregate total counts
    type_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for iss in issues:
        type_counts[iss['type']] += 1

    results[sector_id] = {
        'files': len(files),
        'loc': loc,
        'issues_counts': type_counts,
        'sample_issues': issues[:5]
    }

with open('metrics.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Extraction complete.")
