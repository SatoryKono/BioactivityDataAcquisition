# DEC-ADAPT Proposed Decision Draft

Date: 2026-03-20
Status: Proposed
Scope: `adapter-interface-alignment`

This draft converts the current evidence set into a coherent proposed decision package. Nothing here is marked accepted yet. The goal is to make the trade-offs explicit so the next implementation step can be deliberate rather than incremental.

## Decision Package Summary

The proposed package is:

1. Make provider-bound typed creators the canonical runtime-facing construction seam.
1. Retain `custom_creator` only as a typed internal composition seam for thin or specialized adapter factories.
1. Define helper bundles explicitly by adapter family instead of leaving helper requirements in implicit kwargs.
1. Treat local provider fixes as temporary stabilization unless they move a seam toward the canonical target.

These four decisions are intended to be adopted together. Taken separately, they reduce only local regressions; taken together, they remove the main dual-seam inconsistency between provider assembly and composite-style composition.

## DEC-ADAPT-001

**Decision**
Choose provider-bound typed creators as the canonical helper-synthesis boundary for adapter construction, and reduce `DataSourceFactory.create()` to a compatibility facade over that policy.

**Recommended option**
Normalize on provider-specific composition creators and keep `DataSourceFactory` thin.

**Alternatives considered**

- Normalize on `DataSourceFactory.create()` as the single adapter-construction seam.
- Keep both seam families and rely on tests plus local fixes.

**Why this option**

- The strongest existing contract already lives in `data_source_creator`, not in `custom_creator`.
- Tests already encode the smaller provider-bound caller shape.
- Composite bootstrap shows that explicit facade-first composition scales better than a generic kwargs seam.

**Evidence**

- `EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring`
- `EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface`
- `EV-adapter-alignment-custom-creator-bypasses-global-helper-injection`
- `EV-adapter-alignment-composite-bootstrap-uses-plan-based-public-facade`

**Wins**

- Preserves the smallest and clearest caller-facing API.
- Aligns provider assembly with the stronger composite composition style.
- Removes one major source of duplicated helper-injection policy.

**Loses**

- Requires migration work across compatibility seams.
- Makes some generic factory tests and patch points less direct.
- Forces a clearer separation between runtime callers and internal adapter factories.

**Implications**

- New provider runtime entry paths should prefer typed provider-bound creators.
- `DataSourceFactory.create()` should stop being treated as an independent policy owner.
- Refactors should target seam consolidation before broader provider cleanup.

**Primary risks**

- `RISK-adapt-compat-facade-drift`
- `RISK-adapt-dual-seam-extension`

## DEC-ADAPT-002

**Decision**
Formalize the `custom_creator` contract as an explicit composition protocol instead of `Callable[..., DataSourcePort]`.

**Recommended option**
Replace the open-ended callable alias with a typed protocol for internal adapter factories, while keeping provider-specific runtime callers on `data_source_creator`.

**Alternatives considered**

- Keep the callable seam and document expected kwargs informally.
- Eliminate `custom_creator` immediately without a transition layer.

**Why this option**

- The current seam is under-specified relative to the complexity it carries.
- PubChem shows that a thin internal wrapper is viable.
- OpenAlex showed that hidden helper dependencies eventually surface as regressions when the seam is not explicit enough.

**Evidence**

- `EV-adapter-alignment-custom-creator-dynamic-contract`
- `EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers`
- `EV-adapter-alignment-pubchem-custom-creator-delegates-to-composition-factory`

**Wins**

- Makes adapter-construction expectations reviewable and type-checkable.
- Reduces the chance that new providers silently depend on undeclared kwargs.
- Keeps room for specialized composition factories without exposing them as public runtime contracts.

**Loses**

- Requires introducing new protocol or bundle types.
- May force updates in tests that currently rely on dynamic patching behavior.
- Some provider-specific wrappers may need to be rewritten before they become clearer.

**Implications**

- `ProviderConfig.custom_creator` should no longer be typed as `Callable[..., DataSourcePort]`.
- Thin wrapper patterns are still allowed, but only behind the explicit protocol.
- Provider docs and registration guidance should distinguish public typed creators from internal adapter factories.

**Primary risks**

- `RISK-adapt-overfitted-protocol`
- `RISK-adapt-test-patch-breakage`

## DEC-ADAPT-003

**Decision**
Define adapter helper bundles as explicit composition concepts, with family-specific typing instead of one implicit kwargs bag.

**Recommended option**
Introduce a core adapter-support bundle and one or more family extensions, rather than one flat universal helper bag.

**Suggested shape**

- Core bundle:
  - `error_handler`
  - `request_collector`
  - metrics context or adapter metrics handle
- Bibliographic HTTP extension:
  - `fallback_fetch_service`
  - any stricter HTTP-specific metrics collaborator needed by bibliography adapters

**Alternatives considered**

- Keep helper synthesis provider-local and implicit.
- Define one large universal helper bundle for every adapter family.

**Why this option**

- HTTP bibliography adapters clearly share mandatory helper requirements.
- PubChem already shows a different helper profile from bibliography adapters.
- A family-based bundle model matches the evidence better than a single universal constructor shape.

**Evidence**

- `EV-adapter-alignment-http-adapters-require-fallback-helper`
- `EV-adapter-alignment-pubchem-custom-creator-delegates-to-composition-factory`
- `EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers`

**Wins**

- Makes hidden collaborator requirements explicit.
- Supports reuse without flattening genuinely different adapter families into one constructor contract.
- Creates a direct bridge from composition policy to type-level enforcement.

**Loses**

- Adds new abstraction types to composition.
- Requires deciding which collaborators are core versus family-specific.
- Can be over-engineered if applied to adapters that do not share enough behavior.

**Implications**

- Helper synthesis moves from ad hoc kwargs assembly to explicit bundle construction.
- Provider factories should consume typed helper bundles or clearly named bundle fields.
- Future adapter reviews can ask whether a seam uses the right family bundle instead of diffing kwargs by hand.

**Primary risks**

- `RISK-adapt-helper-bundle-fragmentation`
- `RISK-adapt-premature-generalization`

## DEC-ADAPT-004

**Decision**
Treat local creator fixes as temporary stabilization unless they clearly move a seam toward the canonical model.

**Recommended option**
Allow local fixes only when they preserve the small outward interface and reduce divergence from the target contract.

**Alternatives considered**

- Accept local fixes as the main long-term strategy.
- Freeze local fixes and wait for one large seam-normalization refactor.

**Why this option**

- The OpenAlex fix is correct and useful, but it does not solve the systemic seam problem.
- Blocking all local fixes would leave regressions open too long.
- Treating local fixes as final would continue the drift pattern that created the evidence set.

**Evidence**

- `EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers`
- `EV-adapter-alignment-custom-creator-bypasses-global-helper-injection`
- `EV-adapter-alignment-composite-support-bundle-centralizes-runner-collaborators`

**Wins**

- Keeps production paths stable while refactoring is staged.
- Prevents regressions from expanding the caller-facing interface.
- Creates a practical rule for reviewing fixes before the full seam redesign lands.

**Loses**

- Maintainers still need judgment during the transition period.
- Some small fixes may be rejected because they deepen the wrong seam.
- Temporary compatibility code may live longer than planned.

**Implications**

- Every local adapter-construction fix should state which target seam it converges toward.
- Review criteria should reject fixes that add new caller responsibilities for helper synthesis.
- The backlog should distinguish stabilization work from normalization work.

**Primary risks**

- `RISK-adapt-temporary-fix-permanence`
- `RISK-adapt-review-inconsistency`

## Recommended Adoption Order

1. Accept `DEC-ADAPT-001` and `DEC-ADAPT-004` together so the target seam and transition rule are explicit.
1. Accept `DEC-ADAPT-002` next so `custom_creator` stops being an undefined escape hatch.
1. Accept `DEC-ADAPT-003` once the seam owner is fixed, because bundle design depends on where synthesis is meant to live.

## Implementation Consequences If Accepted

1. Introduce typed internal adapter-factory and helper-bundle abstractions in `composition/providers/_models.py` or an adjacent composition-only module.
1. Convert `ProviderConfig.custom_creator` away from `Callable[..., DataSourcePort]`.
1. Refactor `DataSourceFactory.create()` into a compatibility facade that no longer defines unique helper-policy behavior.
1. Keep `uniprot_idmapping` as a typed specialized creator and use it as the reference case for hybrid data-source construction.
1. Use composite runtime bootstrap and `CompositeSupportServices` as the reference pattern for explicit composition seams.
