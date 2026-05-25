---
id: architecture-refactor-issues-20260525
title: Prepare GitHub issues for architecture refactoring findings
task_id: architecture-refactor-issues-20260525
created_at: '2026-05-25T05:17:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/hotspot-family-baseline.md
- docs/00-project/ai/memory/agent-memory.md
- docs/02-architecture/decisions/ADR-005-composition-layer-separation.md
- .importlinter
summary: 'Created GitHub issues RF-020 through RF-027 for architecture audit findings:
  scripts inventory drift, architecture memory import matrix drift, control-plane
  services decomposition, runtime builder fan-in, PipelineRunner compatibility kwargs,
  repo-wide scan timeout risk, replay/control-plane DDD boundaries, and large observability/storage
  helper modules. Existing open RF issues were checked first to avoid direct duplicates.'
---

# Episodic summary

## Task

- Title: Prepare GitHub issues for architecture refactoring findings

## Outcome

- Created GitHub issues RF-020 through RF-027 for architecture audit findings: scripts inventory drift, architecture memory import matrix drift, control-plane services decomposition, runtime builder fan-in, PipelineRunner compatibility kwargs, repo-wide scan timeout risk, replay/control-plane DDD boundaries, and large observability/storage helper modules. Existing open RF issues were checked first to avoid direct duplicates.

## Lessons learned

- Replace with durable follow-up if needed
