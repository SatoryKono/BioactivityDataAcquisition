# Cross Synthesis: architecture-foundations

Rebaseline note: this synthesis still matches the active repo baseline, and
`RF-011` re-confirmed the green enforcement model through a fresh full verify
pass plus regenerated dependency and compatibility artifacts.

## Executive Summary

- The collected evidence supports a coherent three-level view of the architecture: a stable **layer model**, an explicit **pattern model**, and a green **enforcement model**. ([SYN-layers-and-boundaries.md](SYN-layers-and-boundaries.md), [SYN-architecture-patterns.md](SYN-architecture-patterns.md), [SYN-enforcement-guardrails.md](SYN-enforcement-guardrails.md))
- The architectural center of gravity is `composition`: it is the practical hinge between the five-layer structure, the DI pattern, and the most important guardrails that keep the rest of the system clean. (EV-layers-composition-is-separate-di-root, EV-patterns-dependency-injection-lives-in-composition, EV-enforcement-bootstrap-and-composition-boundaries-pass)
- BioETL’s strongest current state is that its architecture is both explicit and enforceable: Hexagonal + Medallion + DDD + DI are not only documented, but also reflected in a zero-violation dependency map, passing architecture suites, and a freshly refreshed verify baseline. (EV-patterns-hexagonal-ports-and-adapters-is-explicit, EV-patterns-medallion-bronze-silver-gold-flow, EV-patterns-domain-driven-design-primitives, EV-enforcement-dependency-map-shows-zero-layer-violations)
- The main unresolved theme across pillars is not a broken baseline, but a policy-clarity gap around outer-layer seams, especially how strict the project really wants to be about interface-to-infrastructure coupling and which composition surfaces are the canonical public entrypoints. (EV-layers-interfaces-are-driving-adapters, EV-patterns-registry-and-factory-assembly-seams, EV-enforcement-import-matrix-is-docs-as-code)

## Integrated Insights

### Insight 1: The architecture is currently coherent across structure, pattern, and enforcement

- Observation: The five-layer model, the named architectural patterns, and the active guardrail suites all point in the same direction instead of telling different stories. (EV-layers-domain-pure-business-logic-no-io, EV-patterns-hexagonal-ports-and-adapters-is-explicit, EV-enforcement-layer-dependency-suite-passes-baseline)
- Implication: This is a good decision point for architecture work because the baseline is readable and green. Future changes can be judged against a relatively stable architecture narrative rather than against fragmented evidence.
- Confidence: 0.95
- Evidence:
  - EV-layers-domain-pure-business-logic-no-io
  - EV-patterns-hexagonal-ports-and-adapters-is-explicit
  - EV-enforcement-layer-dependency-suite-passes-baseline

### Insight 2: `composition` is the unifying seam of the whole architecture

- Observation: Composition is simultaneously the separate DI root, the place where registry/factory assembly is normalized, and the area protected by some of the most specific architecture guardrails. (EV-layers-composition-is-separate-di-root, EV-patterns-registry-and-factory-assembly-seams, EV-enforcement-bootstrap-and-composition-boundaries-pass)
- Implication: If the team wants to preserve the architecture under growth, the next clarity investments should focus on composition public seams, internal seams, and caller guidance.
- Confidence: 0.95
- Evidence:
  - EV-layers-composition-is-separate-di-root
  - EV-patterns-registry-and-factory-assembly-seams
  - EV-enforcement-bootstrap-and-composition-boundaries-pass

### Insight 3: The baseline is strong enough that the next problems are mostly second-order problems

- Observation: The dependency map is green, the major architecture test slices pass, and the core patterns are explicit. The remaining tensions are mostly about interpretation, seam hierarchy, and review consistency rather than obvious breakage. (EV-enforcement-dependency-map-shows-zero-layer-violations, EV-enforcement-interface-and-adapter-di-guards-pass, EV-patterns-dependency-injection-lives-in-composition)
- Implication: The next architecture phase should focus on reducing ambiguity and making canonical paths easier to follow, rather than on emergency boundary repair.
- Confidence: 0.93
- Evidence:
  - EV-enforcement-dependency-map-shows-zero-layer-violations
  - EV-enforcement-interface-and-adapter-di-guards-pass
  - EV-patterns-dependency-injection-lives-in-composition

## Cross-Pillar Contradictions

### Tension 1: Outer-layer flexibility vs outer-layer discipline

- Evidence:
  - EV-layers-interfaces-are-driving-adapters
  - EV-enforcement-import-matrix-is-docs-as-code
- Resolution: Still unresolved across pillars. The architecture is green, but the policy language is broader than the strongest practical guidance.
- Recommendation: Treat this as the next explicit architecture decision rather than leaving it as reviewer intuition.

### Tension 2: Multiple composition surfaces vs desire for one obvious public seam

- Evidence:
  - EV-layers-composition-is-separate-di-root
  - EV-patterns-registry-and-factory-assembly-seams
  - EV-patterns-dependency-injection-lives-in-composition
- Resolution: Partially resolved. The current docs distinguish several surfaces, but the hierarchy between “entrypoint,” “assembly API,” and “extension seam” is still easier to infer than to teach.
- Recommendation: Define a canonical surface ladder and point different caller types at the right seam.

## Recommended Decisions

- **DEC-ARCH-FOUND-001:** Clarify the true policy for `interfaces -> infrastructure`: allowed in principle, discouraged in practice, or exception-only.
- **DEC-ARCH-FOUND-002:** Define the canonical composition surface hierarchy: entrypoints, bootstrap APIs, registries, factories, and which audiences should use each one.
- **DEC-ARCH-FOUND-003:** Decide whether to publish a consolidated architecture conformance report that combines layer, pattern, and guardrail signals into one review artifact.
