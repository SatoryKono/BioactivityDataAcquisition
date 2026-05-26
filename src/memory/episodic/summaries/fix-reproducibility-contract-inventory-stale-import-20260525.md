---
id: fix-reproducibility-contract-inventory-stale-import-20260525
title: Fix reproducibility contract inventory stale import
task_id: fix-reproducibility-contract-inventory-stale-import-20260525
created_at: '2026-05-25T18:18:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_reproducibility_contract_inventory.py
summary: Repaired the split reproducibility contract inventory test shard by removing
  star-import collection of the canonical suite and explicitly importing only required
  helpers/types; Windows pytest now collects and passes the five local inventory tests.
---

# Episodic summary

## Task

- Title: Fix reproducibility contract inventory stale import

## Outcome

- Repaired the split reproducibility contract inventory test shard by removing star-import collection of the canonical suite and explicitly importing only required helpers/types; Windows pytest now collects and passes the five local inventory tests.

## Lessons learned

- Split test shards should not use `import *` from canonical suites: it can
  collect the entire source suite and still miss underscore-prefixed support
  helpers needed by copied local tests.
