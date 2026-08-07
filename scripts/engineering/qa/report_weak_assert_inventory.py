#!/usr/bin/env python3
"""Advisory inventory of test_* without direct Assert/raises (#8330)."""
from __future__ import annotations
import argparse, ast, json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path
DEFAULT_JSON = Path("reports/quality/weak-assert-inventory.json")
DEFAULT_MD = Path("reports/quality/weak-assert-inventory.md")

def _is_test_function(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')

def _calls_raises(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == 'raises':
            return True
        if isinstance(func, ast.Attribute) and func.attr == 'raises':
            return True
    return False

def _has_assert(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, (ast.Assert, ast.Raise)):
            return True
    return _calls_raises(node)

def _owner_bucket(rel: str) -> str:
    parts = rel.split('/')
    if len(parts) >= 3 and parts[0] == 'tests':
        return '/'.join(parts[:3])
    return parts[0] if parts else 'unknown'

def scan_tree(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in sorted(root.rglob('test_*.py')):
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in tree.body:
            candidates: list[ast.AST] = []
            if _is_test_function(node):
                candidates.append(node)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if _is_test_function(item):
                        candidates.append(item)
            for fn in candidates:
                assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                if _has_assert(fn):
                    continue
                findings.append({'path': rel, 'name': fn.name, 'lineno': fn.lineno, 'owner_bucket': _owner_bucket(rel)})
    return findings

def build_report(findings: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket = Counter(item['owner_bucket'] for item in findings)
    unit = [item for item in findings if item['path'].startswith('tests/unit/')]
    return {
        'schema_version': 'weak-assert-inventory-v1',
        'linked_issue': '#8330',
        'generated_at_utc': datetime.now(UTC).isoformat(),
        'policy': {'mode': 'advisory', 'blocking_gate': False,
            'false_positive_note': 'Architecture/governance tests often assert via helpers.'},
        'summary': {
            'total_without_direct_assert': len(findings),
            'unit_without_direct_assert': len(unit),
            'top_owner_buckets': [{'bucket': b, 'count': c} for b, c in by_bucket.most_common(25)],
        },
        'priority_review_paths': ['tests/unit/application/core', 'tests/unit/scripts'],
        'findings_sample': findings[:200],
        'findings_total': len(findings),
    }

def render_md(report: dict[str, Any]) -> str:
    s = report['summary']
    lines = [
        '# Weak-assert advisory inventory',
        '',
        'Generated: ' + report['generated_at_utc'] + ' (' + report['linked_issue'] + ')',
        '',
        'Mode: **advisory only** — not a merge gate.',
        '',
        '- Total without direct assert/raises: **' + str(s['total_without_direct_assert']) + '**',
        '- Under tests/unit: **' + str(s['unit_without_direct_assert']) + '**',
        '',
        '## Top owner buckets',
        '',
        '| Bucket | Count |',
        '| --- | ---: |',
    ]
    for row in s['top_owner_buckets'][:15]:
        lines.append('| `' + row['bucket'] + '` | ' + str(row['count']) + ' |')
    lines += ['', '## Priority review', '',
              'Focus triage on tests/unit/application/core and tests/unit/scripts.',
              'No mass-delete without review.', '']
    return chr(10).join(lines) + chr(10)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests-root', default='tests')
    parser.add_argument('--json-out', type=Path, default=DEFAULT_JSON)
    parser.add_argument('--md-out', type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    findings = scan_tree((REPO_ROOT / args.tests_root).resolve())
    report = build_report(findings)
    json_out = resolve_output_path(args.json_out, root=REPO_ROOT)
    md_out = resolve_output_path(args.md_out, root=REPO_ROOT)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    md_out.write_text(render_md(report), encoding='utf-8')
    print('Wrote', json_out)
    print('Wrote', md_out)
    print('summary total=', report['summary']['total_without_direct_assert'], 'unit=', report['summary']['unit_without_direct_assert'])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
