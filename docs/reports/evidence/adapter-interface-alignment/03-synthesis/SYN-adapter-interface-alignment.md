# Synthesis: adapter-interface-alignment

Rebaseline note: the seam alignment pressure points remain current, so this synthesis still describes the active adapter-construction contract tension.

## Executive Summary

- The strongest existing interface contract is the `data_source_creator` seam: it is protocol-typed, covered by composition tests, and already centralizes HTTP helper assembly for bibliographic providers. (EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring, EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface)
- The main alignment risk is `custom_creator`, not `data_source_creator`. `custom_creator` is dynamically typed and can bypass the helper-injection policy that `DataSourceFactory.create()` applies centrally. (EV-adapter-alignment-custom-creator-dynamic-contract, EV-adapter-alignment-custom-creator-bypasses-global-helper-injection)
- `fallback_fetch_service` is part of the real implementation contract for HTTP bibliography adapters, so alignment work must treat helper DI as first-class API surface at the composition boundary. (EV-adapter-alignment-http-adapters-require-fallback-helper)
- Tests already imply the intended direction: callers should provide `settings + pipeline_config + logger (+ optional metrics/filter)`, while composition owns helper synthesis internally. (EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface)
- The OpenAlex regression fix is a valid local proof that inward helper synthesis realigns interface and implementation without expanding caller responsibilities, but it does not yet remove the broader seam inconsistency. (EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers, EV-adapter-alignment-custom-creator-bypasses-global-helper-injection)
- Non-bibliographic creators already show two distinct patterns that should not be collapsed into one vague seam: PubChem keeps `custom_creator` thin by delegating to a composition factory, while `uniprot_idmapping` uses a typed creator to encode a real hybrid input contract. (EV-adapter-alignment-pubchem-custom-creator-delegates-to-composition-factory, EV-adapter-alignment-uniprot-idmapping-creator-encodes-hybrid-input-contract)
- Composite runtime bootstrap is materially more explicit than provider adapter creation: it already uses a narrow plan-based public facade and a typed support-service bundle, which makes it the strongest local reference pattern for seam normalization. (EV-adapter-alignment-composite-bootstrap-uses-plan-based-public-facade, EV-adapter-alignment-composite-support-bundle-centralizes-runner-collaborators)

## Key Insights

### Insight 1: The public caller-facing creator surface is intentionally small and should stay that way

- Observation: `DataSourceCreatorProtocol` is explicit about the provider-bound creation contract, and composition tests assert that factory callers pass only settings, pipeline config, logger, and optional filter/metrics context. (EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface, EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring)
- Implication: Interface/implementation alignment should be achieved by moving helper synthesis inward, not by teaching more callers to construct `fallback_fetch_service`, `adapter_metrics`, or request collectors manually.
- Confidence: 0.89
- Evidence:
  - EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface
  - EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring

### Insight 2: Helper DI is not incidental wiring; it is part of the adapter implementation contract

- Observation: OpenAlex, PubMed, UniProt, and Semantic Scholar all require `fallback_fetch_service` at construction time or model it as mandatory state in the adapter class. (EV-adapter-alignment-http-adapters-require-fallback-helper)
- Implication: Any refactor that focuses only on constructor signatures like `mailto` or `email` but leaves helper dependencies implicit will still preserve alignment debt. The helper bundle needs a canonical composition contract.
- Confidence: 0.95
- Evidence:
  - EV-adapter-alignment-http-adapters-require-fallback-helper

### Insight 3: The main seam inconsistency is between two adapter-construction paths, not between providers

- Observation: `create_provider_adapter()` forwards kwargs directly to `custom_creator`, while `DataSourceFactory.create()` injects the standard helper bundle before construction. That means the same provider model has two materially different creation semantics. (EV-adapter-alignment-custom-creator-bypasses-global-helper-injection)
- Implication: The next refactoring target should be seam normalization. Without one canonical boundary for helper assembly, provider-specific creators will continue to rediscover the same dependency requirements through regressions.
- Confidence: 0.93
- Evidence:
  - EV-adapter-alignment-custom-creator-bypasses-global-helper-injection

### Insight 4: `custom_creator` is under-specified relative to the complexity it carries

- Observation: `custom_creator` is declared as `Callable[..., DataSourcePort]`, while `data_source_creator` has a concrete protocol and better caller-shape expectations. (EV-adapter-alignment-custom-creator-dynamic-contract)
- Implication: This seam currently relies on convention instead of an explicit interface. It is the likeliest place for drift between composition intent and adapter implementation details, especially when helper dependencies evolve.
- Confidence: 0.86
- Evidence:
  - EV-adapter-alignment-custom-creator-dynamic-contract

### Insight 5: The OpenAlex fix is evidence of a viable remediation pattern, but only at local scope

- Observation: The OpenAlex settings-based custom creator now synthesizes helper defaults internally and proves `fallback_fetch_service` presence via unit test coverage. (EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers)
- Implication: This validates one safe short-term pattern: preserve the small outward interface and absorb helper synthesis inside composition-owned creators. The remaining work is to generalize that pattern so it is enforced by a shared seam, not repeated by hand.
- Confidence: 0.89
- Evidence:
  - EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers
  - EV-adapter-alignment-custom-creator-bypasses-global-helper-injection

## Contradictions and Resolutions

### Contradiction 1: Minimal public creator interface vs mandatory hidden helper dependencies

- Evidence:
  - EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface
  - EV-adapter-alignment-http-adapters-require-fallback-helper
- Tension: Tests and protocols say callers should interact with a small provider-bound interface, while adapter implementations require a substantial helper bundle.
- Resolution: Resolved conceptually. These claims are not actually incompatible if helper synthesis is owned by composition and kept behind the creator boundary.
- Recommendation: Preserve the small caller-facing interface and formalize helper assembly as a composition concern.

### Contradiction 2: One provider registry model vs two different adapter-construction semantics

- Evidence:
  - EV-adapter-alignment-custom-creator-bypasses-global-helper-injection
  - EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring
- Tension: The registry presents a unified provider model, but `custom_creator` and `data_source_creator` operate with different levels of strictness and centralization.
- Resolution: Unresolved.
- Recommendation: Requires explicit architecture decision on the single canonical boundary for helper synthesis.

### Contradiction 3: Local creator fixes vs systemic seam normalization

- Evidence:
  - EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers
  - EV-adapter-alignment-custom-creator-dynamic-contract
- Tension: The OpenAlex fix proves a local repair pattern, but the underlying seam remains dynamically typed and inconsistent.
- Resolution: Partially resolved. The local regression is fixed; the systemic contract gap remains.
- Recommendation: Treat local fixes as interim stabilization, not as the final alignment strategy.

## Gaps and Uncertainties

- No explicit typed protocol currently describes the kwargs contract for `custom_creator`, including mandatory helper collaborators and credential-resolution responsibilities.
- This synthesis now covers bibliographic HTTP creators, non-bibliographic provider creators, and composite bootstrap/support seams, but it still does not trace every direct registry call site or every phase-level composite runner builder.
- The evidence shows multiple valid composition-owned helper assembly points (`DataSourceFactory`, `_create_http_data_source`, provider-specific custom creators), but it does not by itself determine which one should become the sole canonical boundary.

## Recommended Decisions

- **DEC-ADAPT-001:** Choose the canonical helper-synthesis boundary for adapter construction.

  - Options:
    - Normalize on `DataSourceFactory.create()` as the single adapter-construction seam.
    - Normalize on provider-specific composition creators and reduce `DataSourceFactory` to a thinner facade.

- **DEC-ADAPT-002:** Formalize the `custom_creator` contract.

  - Options:
    - Replace `Callable[..., DataSourcePort]` with a typed protocol.
    - Keep the callable seam but define a shared helper-bundle object or kwargs contract that every custom creator must accept.

- **DEC-ADAPT-003:** Define the mandatory helper bundle for HTTP adapters as an explicit composition concept.

  - Minimum likely members:
    - `error_handler`
    - `adapter_metrics`
    - `request_collector`
    - `fallback_fetch_service`

- **DEC-ADAPT-004:** Decide whether local creator fixes are acceptable as the main remediation strategy or only as temporary stabilization before seam consolidation.

## Decision Readiness

- Evidence analyzed: 10 objects
- Key insights: 5
- Contradictions: 3
  - Resolved: 1
  - Partially resolved: 1
  - Pending: 1

## Top Insights

1. The safest outward-facing interface is already present in `data_source_creator`; the system should preserve that small surface rather than expand caller responsibilities. (EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface, EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring)
1. `fallback_fetch_service` and its helper peers are part of the real adapter contract, not incidental wiring. (EV-adapter-alignment-http-adapters-require-fallback-helper)
1. The root seam problem is the dual construction model around `custom_creator`, not provider-specific behavior by itself. (EV-adapter-alignment-custom-creator-bypasses-global-helper-injection, EV-adapter-alignment-custom-creator-dynamic-contract)
