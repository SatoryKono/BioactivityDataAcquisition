# Synthesis: layers-and-boundaries

## Executive Summary

- The repository currently preserves a clear five-layer architecture: `domain`, `application`, `infrastructure`, `composition`, and `interfaces`, each with a distinct responsibility profile rather than a purely organizational folder split. (EV-layers-domain-pure-business-logic-no-io, EV-layers-application-owns-orchestration-and-services, EV-layers-infrastructure-hosts-adapters-storage-observability, EV-layers-composition-is-separate-di-root, EV-layers-interfaces-are-driving-adapters)
- The most important structural distinction is that `composition` remains a separate DI/assembly root rather than being merged into `interfaces`; this is treated as a first-class architectural decision, not a naming accident. (EV-layers-composition-is-separate-di-root)
- The `domain` layer is still the non-negotiable purity boundary, while `application` orchestrates use cases and `infrastructure` implements ports and storage concerns. (EV-layers-domain-pure-business-logic-no-io, EV-layers-application-owns-orchestration-and-services, EV-layers-infrastructure-hosts-adapters-storage-observability)
- `interfaces` is intended to stay thin and driving-adapter-oriented, but the current body of guidance still contains one policy tension: ADR-level import rules tolerate some `interfaces -> infrastructure` access, while current architecture tests and usage guidance prefer routing through application/composition seams. (EV-layers-interfaces-are-driving-adapters, EV-layers-composition-is-separate-di-root)

## Key Insights

### Insight 1: The layer model is responsibility-first, not just directory-first

- Observation: The active docs assign distinct jobs to each top-level layer: domain for pure business rules, application for orchestration, infrastructure for concrete implementations, composition for assembly, and interfaces for user-facing driving adapters. (EV-layers-domain-pure-business-logic-no-io, EV-layers-application-owns-orchestration-and-services, EV-layers-infrastructure-hosts-adapters-storage-observability, EV-layers-composition-is-separate-di-root, EV-layers-interfaces-are-driving-adapters)
- Implication: Structural refactors should be evaluated against responsibility movement, not only against file movement. A module can live in the “right” folder and still violate the architecture if it takes on the wrong responsibility.
- Confidence: 0.95
- Evidence:
  - EV-layers-domain-pure-business-logic-no-io
  - EV-layers-application-owns-orchestration-and-services
  - EV-layers-infrastructure-hosts-adapters-storage-observability
  - EV-layers-composition-is-separate-di-root
  - EV-layers-interfaces-are-driving-adapters

### Insight 2: `composition` is the architectural pressure valve that keeps the rest of the system cleaner

- Observation: ADR-005 and the current repo structure both treat `composition` as the only layer allowed to know enough to assemble the full object graph. (EV-layers-composition-is-separate-di-root)
- Implication: The health of the whole architecture depends on keeping composition explicit and contained. If assembly logic starts leaking into application or interfaces, the architecture will degrade even if folder names remain unchanged.
- Confidence: 0.97
- Evidence:
  - EV-layers-composition-is-separate-di-root

### Insight 3: The inner/outer split is still intact and understandable

- Observation: Domain is still defined as pure business logic and no-I/O; application consumes domain concepts to orchestrate behavior; infrastructure provides adapter, storage, and observability implementations behind domain-level abstractions. (EV-layers-domain-pure-business-logic-no-io, EV-layers-application-owns-orchestration-and-services, EV-layers-infrastructure-hosts-adapters-storage-observability)
- Implication: The current repository still has a readable inward dependency story, which is good news for future decomposition work. Teams can reason about change impact by asking “is this business logic, orchestration, implementation, assembly, or interface?” and usually get a stable answer.
- Confidence: 0.96
- Evidence:
  - EV-layers-domain-pure-business-logic-no-io
  - EV-layers-application-owns-orchestration-and-services
  - EV-layers-infrastructure-hosts-adapters-storage-observability

### Insight 4: The thinnest intended layer is `interfaces`, but its policy boundary is the least settled

- Observation: The current test and guidance posture says interface code should route through application services or composition entrypoints, but ADR-005 also records that some direct `interfaces -> infrastructure` imports are intentionally tolerated. (EV-layers-interfaces-are-driving-adapters, EV-layers-composition-is-separate-di-root)
- Implication: If left implicit, this ambiguity can create inconsistent review outcomes: one reviewer may treat direct infrastructure access as acceptable by matrix, while another may treat it as an architectural smell because the tests discourage it.
- Confidence: 0.89
- Evidence:
  - EV-layers-interfaces-are-driving-adapters
  - EV-layers-composition-is-separate-di-root

## Contradictions and Resolutions

### Contradiction 1: `interfaces -> infrastructure` is technically allowed, but operationally discouraged

- Evidence:
  - EV-layers-interfaces-are-driving-adapters
  - EV-layers-composition-is-separate-di-root
- Tension: ADR-005 preserves an import matrix that allows some interface-to-infrastructure access, but current tests and usage guidance still prefer application/composition routing.
- Resolution: Partially resolved. The current baseline is workable because the preferred practice is clear in tests, but the policy language remains broader than the day-to-day expectation.
- Recommendation: Promote one explicit project stance: either “allowed but exceptional” or “preferred only through application/composition except named carve-outs.”

### Contradiction 2: `composition` is separate from `interfaces`, but both can know a lot about the outer system

- Evidence:
  - EV-layers-composition-is-separate-di-root
  - EV-layers-interfaces-are-driving-adapters
- Tension: Composition is the only layer meant to assemble the full object graph, but interfaces may still import composition and sometimes infrastructure. Without sharper seam language, the outer boundary can start to look blurred.
- Resolution: Resolved conceptually. The distinction is not “who can import outer concerns,” but “who assembles concrete dependencies” versus “who handles user-facing interaction.”
- Recommendation: Preserve and document that distinction through public seam conventions, not just folder names.

## Gaps and Uncertainties

- This synthesis does not yet map every subpackage below the five top-level layers to a stable responsibility taxonomy.
- It does not yet identify where compatibility shims or public re-export modules slightly blur the clean layer narrative.
- It does not yet tell us whether the current five-layer model is equally well understood across all provider-specific areas of the codebase.

## Recommended Decisions

- **DEC-LAYER-001:** Decide whether `interfaces -> infrastructure` should remain broadly allowed or be reframed as an exception-only escape hatch.
- **DEC-LAYER-002:** Define the canonical public seam for outer-layer callers: when should code use application services versus composition entrypoints?
- **DEC-LAYER-003:** Decide whether the project needs a finer-grained subpackage responsibility map under each top-level layer for onboarding and review consistency.

## Top Insights

1. The repo still has a real five-layer architecture, not just a nominal one. (EV-layers-domain-pure-business-logic-no-io, EV-layers-application-owns-orchestration-and-services, EV-layers-infrastructure-hosts-adapters-storage-observability, EV-layers-composition-is-separate-di-root, EV-layers-interfaces-are-driving-adapters)
1. `composition` is the key architectural hinge because it keeps assembly concerns out of application and interfaces. (EV-layers-composition-is-separate-di-root)
1. The only meaningful policy ambiguity in the current layer model is how strict the project truly wants to be about interface-to-infrastructure coupling. (EV-layers-interfaces-are-driving-adapters, EV-layers-composition-is-separate-di-root)
