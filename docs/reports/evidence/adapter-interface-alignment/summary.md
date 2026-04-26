# Сбор evidence завершён: adapter-interface-alignment

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: the current adapter-construction state still matches the same seam-alignment pressure points, so the pack remains a current baseline for decision work.

**Создано объектов evidence:** 10
**Gate Статус:** PASSED

## Сводка evidence

| ID                                                                             | Claim Summary                                                                                                         | Confidence |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-adapter-alignment-custom-creator-dynamic-contract                           | `custom_creator` is dynamically typed, while `data_source_creator` is protocol-typed.                                 | 0.86       |
| EV-adapter-alignment-custom-creator-bypasses-global-helper-injection           | Custom creator path and `DataSourceFactory.create()` use different helper injection semantics.                        | 0.93       |
| EV-adapter-alignment-biblio-data-source-creators-centralize-helper-wiring      | Bibliographic data-source creators already share a strong centralized composition contract.                           | 0.90       |
| EV-adapter-alignment-http-adapters-require-fallback-helper                     | HTTP bibliography adapters treat `fallback_fetch_service` as mandatory collaborator.                                  | 0.95       |
| EV-adapter-alignment-openalex-custom-creator-synthesizes-default-helpers       | OpenAlex custom creator now aligns with adapter requirements by building helper defaults internally.                  | 0.89       |
| EV-adapter-alignment-tests-preserve-minimal-provider-bound-surface             | Tests preserve a small caller-facing creator surface and implicitly require internal helper assembly.                 | 0.88       |
| EV-adapter-alignment-pubchem-custom-creator-delegates-to-composition-factory   | PubChem keeps its registry-level custom creator thin and centralizes runtime assembly inside the composition factory. | 0.90       |
| EV-adapter-alignment-uniprot-idmapping-creator-encodes-hybrid-input-contract   | UniProt ID mapping uses the typed data-source seam to assemble a hybrid HTTP + local-input contract.                  | 0.91       |
| EV-adapter-alignment-composite-bootstrap-uses-plan-based-public-facade         | Composite runtime creation already exposes a stable plan-based facade instead of a dynamic creator seam.              | 0.93       |
| EV-adapter-alignment-composite-support-bundle-centralizes-runner-collaborators | Composite runtime support services are assembled as an explicit typed bundle rather than through loose kwargs.        | 0.91       |

## Ключевые выводы

- The cleanest existing contract is the `data_source_creator` seam, not the `custom_creator` seam.
- Helper DI is a real part of adapter implementation contracts, especially `fallback_fetch_service`; it cannot be treated as optional incidental wiring.
- Non-bibliographic creators already split into two useful patterns: thin delegation to a composition factory (`pubchem`) and specialized typed creators for hybrid contracts (`uniprot_idmapping`).
- Composite runtime creation is materially more explicit than provider adapter creation: it already uses a narrow public facade plus a typed support-service bundle.
- Alignment work should move toward centralized helper synthesis in composition, because tests already assume callers should not assemble helper bundles manually.

## Отмеченные противоречия

- `ProviderConfig` presents one provider-registration model, but its two creation seams (`custom_creator` vs `data_source_creator`) have materially different strictness and discoverability.
- `DataSourceFactory.create()` injects helper bundles centrally, while direct custom-creator delegation in `create_provider_adapter()` leaves equivalent alignment burden to each provider-specific creator.
- Composite bootstrap already preserves a stable facade and typed bundles, but provider adapter construction still relies on dynamic callable contracts for part of the same composition problem.

## Оставшиеся пробелы

- No single explicit protocol currently describes the kwargs contract for `custom_creator`.
- Helper synthesis still exists in multiple places (`DataSourceFactory`, `_create_http_data_source`, provider-specific custom creators, provider-specific factories) instead of one canonical adapter-construction boundary.
- No unifying decision yet explains when a provider should use a thin custom wrapper, a typed `data_source_creator`, or a composite-style explicit bundle/facade.
- Composite evidence now covers bootstrap and support-service assembly, but it does not yet trace down into phase-level runner factories or non-provider data adapters outside the registry/bootstrap families.
