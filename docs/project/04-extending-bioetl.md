# 04 Extending Bioetl

This guide provides step-by-step recipes for adding new providers, pipelines, and services without modifying core code. Follow the naming and placement rules in `docs/00-styleguide` to stay compliant.

## Adding a new provider via configs and registries

1. **Define the ABC** in `src/bioetl/domain/clients/<provider>/contracts.py` using the three-layer pattern demonstrated by `ChemblDataClientABC` in `src/bioetl/domain/clients/chembl/contracts.py`. Keep the docstring structured and list the public interface.
2. **Create a default factory** in `src/bioetl/infrastructure/clients/<provider>/factories.py` that exposes `default_<provider>_<entity>()`, mirroring `src/bioetl/infrastructure/clients/chembl/factories.py`.
3. **Implement the client** under `src/bioetl/infrastructure/clients/<provider>/impl/` with classes suffixed `Impl`. Reuse the ABC methods as in the Chembl HTTP implementations.
4. **Register the ABC and default** in `src/bioetl/infrastructure/clients/base/abc_registry.yaml`, and map the default to the concrete Impl in `src/bioetl/infrastructure/clients/base/abc_impls.yaml`. Keep keys in `lower_snake_case`.
5. **Expose the provider** through `src/bioetl/infrastructure/clients/provider_registry_loader.py` or the relevant registry loader so the dependency injection container can resolve it from configs.

## Wiring pipeline configs for the provider

1. Add provider-level configs under `configs/providers/<provider>.yaml` if needed for secrets, rate limits, or base URLs, following the Chembl entries.
2. Define pipeline configs in `configs/pipelines/<provider>/<entity>.yaml` with snake_case keys. Reuse the Chembl pipeline configs as templates for stages and schema references.
3. Ensure pipeline modules live in `src/bioetl/pipelines/<provider>/<entity>/<stage>.py` with stage names such as `extract`, `transform`, `validate`, `normalize`, or `write`.
4. Update any pipeline descriptors or docs under `docs/02-pipelines/<provider>/<entity>/` using the `NN-<entity>-<provider>-<topic>.md` naming rule.

## Creating new services or hooks

1. Place reusable services in `src/bioetl/infrastructure` under the appropriate adapter folder (for example, observability, logging, or transform). Keep module names in snake_case and classes in PascalCase.
2. Add middleware or hooks to `src/bioetl/infrastructure/clients/base/middleware.py` or a provider-specific middleware module. Use the Chembl middleware as a reference for request/response interception.
3. Export public symbols via `__all__` where applicable so they become container-resolvable without editing core modules.

## Leveraging DI and container factories

1. Prefer factory functions (for example, `default_cache`, `default_retry_policy`, `default_rate_limiter`) to instantiate dependencies; keep them in the `factories.py` files alongside the domain they serve.
2. Bind implementations through YAML registries rather than editing application code. The DI loader reads `abc_registry.yaml` and `abc_impls.yaml` to compose clients at runtime.
3. When adding provider-specific factories, inject them via configuration rather than patching `run_bioetl.py` or shared modules. Use Chembl factories as a blueprint for how to separate request builders, paginators, and response parsers.
4. Keep new configs deterministic: specify timeouts, retries, and ordering explicitly, and store secrets only via environment variables resolved by the secret provider.

Following these steps keeps extensions compliant with BioETL standards while avoiding core-code modifications.
