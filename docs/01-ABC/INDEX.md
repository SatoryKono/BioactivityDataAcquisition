# ABC Index
<!-- generated -->

- `NormalizationServiceABC` — `bioetl.domain.transform.contracts.NormalizationServiceABC`
  - Normalization service contract for DataFrame/record pipelines. Default factory: `bioetl.infrastructure.transform.factories.default_normalization_service`. Implementations: `NormalizationServiceImpl`, `ChemblNormalizationService`.
- `HashServiceABC` — `bioetl.domain.transform.contracts.HashServiceABC`
  - Facade for deterministic hash columns; default factory: `bioetl.infrastructure.transform.factories.default_hash_service`. Implementation: `bioetl.infrastructure.transform.impl.hash_service_impl.HashServiceImpl`.
- `ProviderRegistryABC` — `bioetl.domain.provider_registry.ProviderRegistryABC`
  - Read port for provider definitions consumed by orchestrator and containers.
- `MutableProviderRegistryABC` — `bioetl.domain.provider_registry.MutableProviderRegistryABC`
  - Registry with mutation helpers for loading providers from configs and tests.
- `ProviderRegistryLoaderABC` — `bioetl.domain.provider_registry.ProviderRegistryLoaderABC`
  - Loader port for provider registries used by `PipelineOrchestrator` background execution. Default factory: `bioetl.infrastructure.clients.provider_registry_loader.default_provider_registry_loader`. Implementation: `ProviderRegistryLoader`.
- `PipelineContainerABC` — `bioetl.application.pipelines.contracts.PipelineContainerABC`
  - Dependency container port for orchestrating pipeline assembly (logger, validation, output writer, extractor, normalization, hash, hooks, error policy).
