# Synthesis: architecture-patterns

## Executive Summary

- The project’s architecture style is explicit rather than inferred: active docs repeatedly identify BioETL as Hexagonal / Ports & Adapters and pair that with a Medallion data-flow model. (EV-patterns-hexagonal-ports-and-adapters-is-explicit, EV-patterns-medallion-bronze-silver-gold-flow)
- The domain layer is not just a folder but a modeled DDD core, with ports, aggregates, value objects, entities, and schemas named as first-class primitives. (EV-patterns-domain-driven-design-primitives)
- Dependency Injection is one of the strongest operational patterns in the codebase: constructor injection and composition-root assembly are not only documented, but also guarded by architecture tests. (EV-patterns-dependency-injection-lives-in-composition)
- Registry and factory seams make the architecture extensible in practice, especially for pipeline/provider assembly, but they also create a need for a clearer public assembly hierarchy so developers know which seam is canonical at which level. (EV-patterns-registry-and-factory-assembly-seams, EV-patterns-dependency-injection-lives-in-composition)

## Key Insights

### Insight 1: BioETL uses two architectural axes at once, and they are complementary

- Observation: The repository describes itself as both Hexagonal Architecture and Medallion Architecture. Hexagonal explains dependency direction and ports/adapters; Medallion explains the data lifecycle from Bronze to Silver to Gold. (EV-patterns-hexagonal-ports-and-adapters-is-explicit, EV-patterns-medallion-bronze-silver-gold-flow)
- Implication: Architecture discussions should avoid collapsing these into one thing. A change can be structurally sound in the hexagonal sense and still violate Medallion expectations, or vice versa.
- Confidence: 0.97
- Evidence:
  - EV-patterns-hexagonal-ports-and-adapters-is-explicit
  - EV-patterns-medallion-bronze-silver-gold-flow

### Insight 2: DDD is a concrete modeling choice, not a branding label

- Observation: The domain layer is explicitly described through DDD primitives such as ports, aggregates, value objects, entities, and schemas. (EV-patterns-domain-driven-design-primitives)
- Implication: New domain-facing work should preserve that modeling vocabulary. If new features bypass these concepts and push business logic into orchestration or infrastructure-only helpers, the project will lose one of its main architecture advantages: a readable, concept-centric core.
- Confidence: 0.94
- Evidence:
  - EV-patterns-domain-driven-design-primitives

### Insight 3: Dependency Injection is the pattern that makes the rest of the architecture executable

- Observation: Constructor injection, composition-root assembly, and no-inline-construction guardrails are all aligned around the same pattern: creation is separated from use. (EV-patterns-dependency-injection-lives-in-composition)
- Implication: DI is not a secondary implementation detail here. It is the mechanical pattern that keeps the hexagonal and layer model intact under change. If DI weakens, the layer model will likely weaken with it.
- Confidence: 0.97
- Evidence:
  - EV-patterns-dependency-injection-lives-in-composition

### Insight 4: Registry/factory seams are the project’s scale mechanism for extensibility

- Observation: The project documents `PipelineRegistry`, `ProviderRegistry`, and `DataSourceFactory` as canonical composition-layer surfaces for assembly and provider extension. (EV-patterns-registry-and-factory-assembly-seams)
- Implication: These seams are likely the right place to absorb future provider growth and assembly variation. The trade-off is that the project needs sharper guidance on which surface is public at which layer of abstraction, otherwise “canonical” starts to mean several different things.
- Confidence: 0.91
- Evidence:
  - EV-patterns-registry-and-factory-assembly-seams

## Contradictions and Resolutions

### Contradiction 1: Multiple “canonical” composition seams can make the public assembly story feel broader than intended

- Evidence:
  - EV-patterns-registry-and-factory-assembly-seams
  - EV-patterns-dependency-injection-lives-in-composition
- Tension: The project wants one clear composition-root story, but it also exposes registries, factories, entrypoints, and bootstrap APIs that may all look canonical from different perspectives.
- Resolution: Partially resolved. The current docs distinguish their roles, but the hierarchy between “public runtime seam” and “lower-level assembly seam” is still easier to infer than to state.
- Recommendation: Define an explicit assembly ladder: entrypoints for callers, registries/factories for composition internals and advanced extension cases.

### Contradiction 2: There is no strong contradiction between Hexagonal, Medallion, DDD, and DI, but there is a coordination burden

- Evidence:
  - EV-patterns-hexagonal-ports-and-adapters-is-explicit
  - EV-patterns-medallion-bronze-silver-gold-flow
  - EV-patterns-domain-driven-design-primitives
  - EV-patterns-dependency-injection-lives-in-composition
- Tension: The project uses several architecture patterns simultaneously, which increases expressive power but also raises the coordination cost for contributors.
- Resolution: Resolved conceptually. These patterns reinforce one another, but only if onboarding and review practices keep their boundaries understandable.
- Recommendation: Keep cross-pattern onboarding material current so contributors understand which pattern answers which question.

## Gaps and Uncertainties

- This synthesis does not yet map which architectural pattern is most dominant in each major subsystem or provider path.
- It does not yet quantify where compatibility facades blur the ideal registry/factory surface hierarchy.
- It does not yet tell us which DDD primitives are mandatory for new work versus optional depending on feature scope.

## Recommended Decisions

- **DEC-PATTERN-001:** Define the canonical assembly ladder across `entrypoints`, bootstrap APIs, registries, and factories.
- **DEC-PATTERN-002:** Decide which DDD primitives are required for new domain work and which are situational.
- **DEC-PATTERN-003:** Decide whether Medallion conformance should have its own explicit architecture checklist alongside layer and DI checks.

## Top Insights

1. The architecture is best understood as Hexagonal structure plus Medallion data flow, with DDD and DI supplying the implementation discipline inside that frame. (EV-patterns-hexagonal-ports-and-adapters-is-explicit, EV-patterns-medallion-bronze-silver-gold-flow, EV-patterns-domain-driven-design-primitives, EV-patterns-dependency-injection-lives-in-composition)
1. Dependency Injection is the operational keystone that keeps the larger architecture patterns practical rather than aspirational. (EV-patterns-dependency-injection-lives-in-composition)
1. Registry/factory seams are the project’s main extensibility mechanism, but they would benefit from a clearer statement of surface hierarchy. (EV-patterns-registry-and-factory-assembly-seams)
