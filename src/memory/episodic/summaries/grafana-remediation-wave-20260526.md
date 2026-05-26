---
id: grafana-remediation-wave-20260526
title: grafana remediation wave from audit findings
task_id: grafana-remediation-wave-20260526
created_at: '2026-05-26T04:43:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Implemented the first Grafana remediation wave by removing the exact cross-dashboard
  duplication of ''Monitor: Lineage Refs Missing'' from bioetl-dq-v2 and replacing
  it with a canonical Control Plane handoff note/link. The canonical metric owner
  is now bioetl-control-plane-v1 only. Updated Grafana integration tests for duplicate-query
  governance, range-aware summary panels, and CTA link expectations, and synced dashboard
  guidance docs (design-system, comprehensive requirements, per-dashboard checklist,
  audit checklist, panel-title inventory). Validation passed for targeted Grafana
  test bundles covering surface contracts, metric semantics, CTA links, query governance,
  and metadata/design-system checks.'
---

# Episodic summary

## Task

- Title: grafana remediation wave from audit findings

## Outcome

- Implemented the first Grafana remediation wave by removing the exact cross-dashboard duplication of 'Monitor: Lineage Refs Missing' from bioetl-dq-v2 and replacing it with a canonical Control Plane handoff note/link. The canonical metric owner is now bioetl-control-plane-v1 only. Updated Grafana integration tests for duplicate-query governance, range-aware summary panels, and CTA link expectations, and synced dashboard guidance docs (design-system, comprehensive requirements, per-dashboard checklist, audit checklist, panel-title inventory). Validation passed for targeted Grafana test bundles covering surface contracts, metric semantics, CTA links, query governance, and metadata/design-system checks.

## Lessons learned

- Replace with durable follow-up if needed
