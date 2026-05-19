---
id: codex-repro-audit-main-20260519
title: Audit pipeline reproducibility on main
task_id: codex-repro-audit-main-20260519
created_at: '2026-05-19T03:43:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- git:503d48a8782663c0d6a239dc4af1491dbe98615a
summary: 'Audited reproducibility on current main baseline. Strong immutable control-plane
  exists around run manifest, ledger, effective-config artifacts, execution fingerprint,
  and lineage metadata. Exact replay is bounded to snapshot-backed and certified historical
  boundaries rather than guaranteed for any arbitrary run occurrence. Critical finding:
  checkpoint metadata enrichment drops normalization profile anchors required by strict
  checkpoint compatibility, creating identity drift risk for resume/replay. Secondary
  findings: ordinary resume uses mutable pipeline checkpoint pointer rather than occurrence-pinned
  checkpoint selection; config_hash vs resolved_config_hash semantics remain blurred
  in manifest construction; bronze live snapshot metadata mixes content identity with
  filesystem-derived captured_at evidence.'
---

# Episodic summary

## Task

- Title: Audit pipeline reproducibility on main

## Outcome

- Audited reproducibility on current main baseline. Strong immutable control-plane exists around run manifest, ledger, effective-config artifacts, execution fingerprint, and lineage metadata. Exact replay is bounded to snapshot-backed and certified historical boundaries rather than guaranteed for any arbitrary run occurrence. Critical finding: checkpoint metadata enrichment drops normalization profile anchors required by strict checkpoint compatibility, creating identity drift risk for resume/replay. Secondary findings: ordinary resume uses mutable pipeline checkpoint pointer rather than occurrence-pinned checkpoint selection; config_hash vs resolved_config_hash semantics remain blurred in manifest construction; bronze live snapshot metadata mixes content identity with filesystem-derived captured_at evidence.

## Lessons learned

- Replace with durable follow-up if needed
