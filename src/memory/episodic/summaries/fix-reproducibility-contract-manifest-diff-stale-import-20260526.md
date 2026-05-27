---
id: fix-reproducibility-contract-manifest-diff-stale-import-20260526
title: Fix reproducibility contract manifest diff stale import
task_id: fix-reproducibility-contract-manifest-diff-stale-import-20260526
created_at: '2026-05-26T03:14:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_reproducibility_contract_manifest_diff.py
summary: Removed star-import dependence from the split reproducibility manifest-diff
  shard and made its helper/type dependencies explicit; Windows pytest now collects
  and passes the five local manifest-diff tests.
---

# Episodic summary

## Task

- Title: Fix reproducibility contract manifest diff stale import

## Outcome

- Removed star-import dependence from the split reproducibility manifest-diff shard and made its helper/type dependencies explicit; Windows pytest now collects and passes the five local manifest-diff tests.

## Lessons learned

- Split test shards should explicitly import their helper/type dependencies;
  `import *` from a canonical suite can both collect unrelated tests and hide
  stale-symbol drift until Windows/PyCharm import collection.
