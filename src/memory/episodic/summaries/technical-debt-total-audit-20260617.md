---
id: technical-debt-total-audit-20260617
title: Technical debt and governance audit
task_id: technical-debt-total-audit-20260617
created_at: '2026-06-17T18:15:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Completed read-only technical debt and governance audit against GitHub main
  snapshot 4a15f47273852f9df96c49b0294cb69a4dbd5c90. Key findings: architecture-quality-scorecard
  integral_score 7.98 with no-growth debt policy, but selected live gates fail on
  main: private import guard for manifest diagnostics importing replay private constants,
  stale runtime SCC acceptance for manifest/inspection_service, regression metrics
  for ruff I001 and architecture skip_count, and test-governance/domain-invariant
  closeout artifact drift. Compatibility transition debt is zero, retained public
  entrypoint burden is 13, dead-code inventory has zero untriaged candidates but 10
  retained zero-import candidates. Contracts, VCR, bronze fixture gaps, and observability
  cardinality artifacts are currently governed/green by committed reports.'
---

# Episodic summary

## Task

- Title: Technical debt and governance audit

## Outcome

- Completed read-only technical debt and governance audit against GitHub main snapshot 4a15f47273852f9df96c49b0294cb69a4dbd5c90. Key findings: architecture-quality-scorecard integral_score 7.98 with no-growth debt policy, but selected live gates fail on main: private import guard for manifest diagnostics importing replay private constants, stale runtime SCC acceptance for manifest/inspection_service, regression metrics for ruff I001 and architecture skip_count, and test-governance/domain-invariant closeout artifact drift. Compatibility transition debt is zero, retained public entrypoint burden is 13, dead-code inventory has zero untriaged candidates but 10 retained zero-import candidates. Contracts, VCR, bronze fixture gaps, and observability cardinality artifacts are currently governed/green by committed reports.

## Lessons learned

- Replace with durable follow-up if needed
