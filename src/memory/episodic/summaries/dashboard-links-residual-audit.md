---
id: dashboard-links-residual-audit
title: Audit residual dashboard links and CTA issues
task_id: dashboard-links-residual-audit
created_at: '2026-05-11T14:03:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Audited shipped dashboard navigation and panel-level CTA links against current
  navigation contract. Confirmed nav bus is aligned after Control Plane fix. Remaining
  contract/hygiene backlog is concentrated in panel dataLinks that omit explicit includeVars=false,
  especially required CTA surfaces in Overview, DQ, and Workflow; identified a validation
  gap because current tests do not consistently enforce includeVars on options.dataLinks.
---

# Episodic summary

## Task

- Title: Audit residual dashboard links and CTA issues

## Outcome

- Audited shipped dashboard navigation and panel-level CTA links against current navigation contract. Confirmed nav bus is aligned after Control Plane fix. Remaining contract/hygiene backlog is concentrated in panel dataLinks that omit explicit includeVars=false, especially required CTA surfaces in Overview, DQ, and Workflow; identified a validation gap because current tests do not consistently enforce includeVars on options.dataLinks.

## Lessons learned

- Replace with durable follow-up if needed
