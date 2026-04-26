# Synthesis: enforcement-guardrails

## Executive Summary

- The current architecture baseline is green on enforcement, not only on documentation: the generated dependency map reports `0` layer-policy violations, and all sampled architecture guardrail suites passed locally during evidence collection. (EV-enforcement-dependency-map-shows-zero-layer-violations, EV-enforcement-layer-dependency-suite-passes-baseline, EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- Architectural enforcement is layered rather than monolithic. The repository combines generated graph artifacts, import-direction tests, bootstrap/composition boundary tests, and DI/logging/interface hardening tests. (EV-enforcement-layer-dependency-suite-passes-baseline, EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- The strongest guardrails are currently around object-graph assembly and boundary hygiene: composition-root isolation, no inline construction, no direct structlog in application/interfaces, and no helper construction inside provider adapters. (EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- The main unresolved policy tension is not whether enforcement exists, but whether the stricter practical rule for `interfaces` should fully replace the broader matrix allowance recorded in ADR-005. (EV-enforcement-import-matrix-is-docs-as-code)

## Key Insights

### Insight 1: The architecture is actively enforceable, not just descriptively documented

- Observation: The generated dependency map is current and reports zero layer-policy violations, while the targeted architecture test suites also pass on the active baseline. (EV-enforcement-dependency-map-shows-zero-layer-violations, EV-enforcement-layer-dependency-suite-passes-baseline, EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- Implication: Architecture conversations can start from a trustworthy green baseline rather than from speculative documentation drift. This makes future regressions easier to interpret as actual new drift.
- Confidence: 0.96
- Evidence:
  - EV-enforcement-dependency-map-shows-zero-layer-violations
  - EV-enforcement-layer-dependency-suite-passes-baseline
  - EV-enforcement-bootstrap-and-composition-boundaries-pass
  - EV-enforcement-interface-and-adapter-di-guards-pass

### Insight 2: BioETL enforces architecture through multiple orthogonal controls

- Observation: The evidence spans graph-level checks, layer dependency tests, bootstrap/composition boundary tests, and interface/adapter-side DI hardening tests. (EV-enforcement-layer-dependency-suite-passes-baseline, EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- Implication: The project is less vulnerable to a single blind spot than a repo that only has import-linter or only has naming rules. If one guard misses something, another guard may still catch it from a different angle.
- Confidence: 0.94
- Evidence:
  - EV-enforcement-layer-dependency-suite-passes-baseline
  - EV-enforcement-bootstrap-and-composition-boundaries-pass
  - EV-enforcement-interface-and-adapter-di-guards-pass

### Insight 3: The enforcement emphasis is strongest around assembly seams and dependency hygiene

- Observation: The passing suites heavily target composition-root boundaries, runtime bootstrap isolation, inline construction bans, logging abstraction rules, and adapter helper injection. (EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
- Implication: The current architecture program is especially focused on preventing silent erosion of DI and assembly boundaries. That is consistent with a system whose main structural risk is not illegal imports alone, but assembly leakage across layers.
- Confidence: 0.95
- Evidence:
  - EV-enforcement-bootstrap-and-composition-boundaries-pass
  - EV-enforcement-interface-and-adapter-di-guards-pass

### Insight 4: The import matrix is already “docs-as-code,” but one part of it still needs a sharper project stance

- Observation: The import matrix is documented in active instructions and ADRs and backed by tests, yet the strongest practical rule around interfaces appears narrower than the broad matrix allowance. (EV-enforcement-import-matrix-is-docs-as-code, EV-enforcement-interface-and-adapter-di-guards-pass)
- Implication: The repository already has the machinery for architecture governance; what it needs next is policy clarification, not entirely new enforcement infrastructure.
- Confidence: 0.91
- Evidence:
  - EV-enforcement-import-matrix-is-docs-as-code
  - EV-enforcement-interface-and-adapter-di-guards-pass

## Contradictions and Resolutions

### Contradiction 1: ADR-level matrix breadth vs stricter practical interface policy

- Evidence:
  - EV-enforcement-import-matrix-is-docs-as-code
  - EV-enforcement-interface-and-adapter-di-guards-pass
- Tension: The documented matrix allows more outer-layer flexibility than the stricter practical guidance encoded in current interface-focused tests.
- Resolution: Unresolved. The codebase is green either way today, but the policy language still leaves room for inconsistent interpretation.
- Recommendation: Choose one explicit rule and encode exceptions separately if needed.

### Contradiction 2: Zero layer-policy violations vs many targeted architecture guards

- Evidence:
  - EV-enforcement-dependency-map-shows-zero-layer-violations
  - EV-enforcement-layer-dependency-suite-passes-baseline
  - EV-enforcement-bootstrap-and-composition-boundaries-pass
- Tension: At first glance, a zero-violation dependency map could make the larger guardrail set look redundant.
- Resolution: Resolved conceptually. The guardrails do not duplicate each other; they protect different failure modes such as runtime assembly leakage, adapter-side inline construction, and logging boundary erosion.
- Recommendation: Keep the layered guardrail model even when the import graph is green.

## Gaps and Uncertainties

- This synthesis does not yet measure the speed or maintenance cost of the architecture guardrail suite itself.
- It does not yet identify whether any important architecture rules remain documented but only weakly enforced.
- It does not yet consolidate the multiple architecture signals into a single conformance dashboard or report artifact.

## Recommended Decisions

- **DEC-ENFORCE-001:** Decide whether the stricter practical rule for `interfaces` should become the explicit canonical import policy.
- **DEC-ENFORCE-002:** Decide whether to keep architecture guardrails distributed across many focused tests or to add a consolidated architecture conformance report.
- **DEC-ENFORCE-003:** Identify any remaining architecture rules that are currently documentation-first and should gain executable enforcement.

## Top Insights

1. The project’s architecture is already executable governance, not just architecture prose. (EV-enforcement-dependency-map-shows-zero-layer-violations, EV-enforcement-layer-dependency-suite-passes-baseline, EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
1. The strongest enforcement emphasis is around DI and assembly seams, which matches the project’s real structural risk profile. (EV-enforcement-bootstrap-and-composition-boundaries-pass, EV-enforcement-interface-and-adapter-di-guards-pass)
1. The main remaining enforcement problem is policy clarity, not policy absence. (EV-enforcement-import-matrix-is-docs-as-code)
