#!/usr/bin/env python3
"""Check root policy mismatches."""

from pathlib import Path
from scripts.ops.support.repo import cleanup_repository

ROOT = Path('.')
review_evidence = cleanup_repository.collect_root_review_evidence(ROOT)
mismatches = cleanup_repository.collect_root_policy_mismatches(ROOT)
report = cleanup_repository.build_root_review_evidence_report(
    ROOT, mismatches=mismatches, review_evidence=review_evidence
)

print('ROOT_POLICY_MISMATCH:', report['summary']['ROOT_POLICY_MISMATCH'])
print('Mismatches:')
for m in mismatches:
    print(f"  {m.path}: {m.reason if hasattr(m, 'reason') else 'unknown'}")
