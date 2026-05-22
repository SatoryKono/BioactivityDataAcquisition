---
id: reproducibility-audit-main-20260522
title: Audit reproducibility on main
task_id: reproducibility-audit-main-20260522
created_at: '2026-05-22T14:55:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
- .codex/skills/py-reproducibility-audit/references/reproducibility-audit.md
summary: 'Audited current main reproducibility posture. Exact replay is strong inside
  supported snapshot-backed boundary, but universal historical exact-replay remains
  conditional on authoritative universe closure + durable evidence claims. Found one
  remaining fail-open defect: CLI run-manifest universe-report returns exit_code 0
  even when required universal/durable claims are missing.'
---

# Episodic summary

## Task

- Title: Audit reproducibility on main

## Outcome

- Audited current main reproducibility posture. Exact replay is strong inside supported snapshot-backed boundary, but universal historical exact-replay remains conditional on authoritative universe closure + durable evidence claims. Found one remaining fail-open defect: CLI run-manifest universe-report returns exit_code 0 even when required universal/durable claims are missing.

## Lessons learned

- Replace with durable follow-up if needed
