# Clients Architecture

- **Domain contracts:** `src/bioetl/domain/clients/...` define ports for request builders, parsers, paginators, and API clients.
- **Infrastructure adapters:** `src/bioetl/infrastructure/clients/...` — concrete `*Impl` classes that use `UnifiedAPIClient` for HTTP with configured timeouts and rate limiting.
- **Application wiring:** Providers register default factories so pipelines can resolve ChEMBL clients and services without manual setup.
