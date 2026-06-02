---
id: fix-architecture-failures-20260602
title: Fix architecture and drift failures
task_id: fix-architecture-failures-20260602
created_at: '2026-06-02T11:52:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Resolved remaining architecture/drift failures by splitting organism taxonomy
  lookup out of organism_classification_constants to clear the domain LOC limit, routing
  composite support builders through composite_support_service_bundles, moving domain
  behavior imports onto bioetl.domain.value_objects and bioetl.domain.ports facades,
  trimming application/core/base.py back under the hotspot growth threshold, allowlisting
  thin unmeasured hotspot-family modules in debt_scorecard coverage thresholds, regenerating
  dependency-map/module-coverage/test-governance/VCR artifacts, and revalidating the
  targeted architecture failure set including cross-layer edge and governance drift
  guards.
---

# Episodic summary

## Task

- Title: Fix architecture and drift failures

## Outcome

- Resolved remaining architecture/drift failures by splitting organism taxonomy lookup out of organism_classification_constants to clear the domain LOC limit, routing composite support builders through composite_support_service_bundles, moving domain behavior imports onto bioetl.domain.value_objects and bioetl.domain.ports facades, trimming application/core/base.py back under the hotspot growth threshold, allowlisting thin unmeasured hotspot-family modules in debt_scorecard coverage thresholds, regenerating dependency-map/module-coverage/test-governance/VCR artifacts, and revalidating the targeted architecture failure set including cross-layer edge and governance drift guards.

## Lessons learned

- Replace with durable follow-up if needed
