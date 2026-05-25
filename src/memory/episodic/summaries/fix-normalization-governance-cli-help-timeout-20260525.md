---
id: fix-normalization-governance-cli-help-timeout-20260525
title: Fix normalization governance CLI help smoke timeout
task_id: fix-normalization-governance-cli-help-timeout-20260525
created_at: '2026-05-25T17:17:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_normalization_fallback_inventory.py
- tests/helpers/cli_process.py
- tests/unit/scripts/test_normalization_governance_cli_smoke.py
summary: Made report-normalization-fallback-inventory help path avoid heavy matrix
  imports when invoked through the QA router; subprocess CLI smoke helpers now default
  to a bounded timeout so delegated CLI hangs fail locally instead of waiting for
  suite-level pytest-timeout.
---

# Episodic summary

## Task

- Title: Fix normalization governance CLI help smoke timeout

## Outcome

- Made report-normalization-fallback-inventory help path avoid heavy matrix imports when invoked through the QA router; subprocess CLI smoke helpers now default to a bounded timeout so delegated CLI hangs fail locally instead of waiting for suite-level pytest-timeout.

## Lessons learned

- Router-invoked module commands import target modules before argparse handles
  `--help`; keep help paths import-light by moving heavy runtime dependencies
  behind execution-only functions.
