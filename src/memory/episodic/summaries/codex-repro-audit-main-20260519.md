---
id: codex-repro-audit-main-20260519
title: Audit reproducibility architecture on main after closure wave
task_id: codex-repro-audit-main-20260519
created_at: '2026-05-19T04:58:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Re-audited reproducibility architecture on main at 288c5c0 after closure
  of #4261-#4264. Confirmed checkpoint enrichment now carries normalization profile
  and snapshot anchors; Bronze live snapshots no longer use filesystem mtime as replay
  evidence; workflow resume supports manifest_id/run_id selectors excluded from semantic
  execution fingerprint. Remaining architectural gap: contract still does not claim
  universal exact reproducibility for every historical run, and ordinary pipeline
  checkpoint resume still loads mutable latest checkpoint pointer by pipeline name.'
---

# Episodic summary

## Task

- Title: Audit reproducibility architecture on main after closure wave

## Outcome

- Re-audited reproducibility architecture on main at 288c5c0 after closure of #4261-#4264. Confirmed checkpoint enrichment now carries normalization profile and snapshot anchors; Bronze live snapshots no longer use filesystem mtime as replay evidence; workflow resume supports manifest_id/run_id selectors excluded from semantic execution fingerprint. Remaining architectural gap: contract still does not claim universal exact reproducibility for every historical run, and ordinary pipeline checkpoint resume still loads mutable latest checkpoint pointer by pipeline name.

## Lessons learned

- Replace with durable follow-up if needed
