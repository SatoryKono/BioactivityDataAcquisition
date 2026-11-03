# Decorators Package

This package contains `RetryingDataSourceDecorator`, `CircuitBreakerDataSourceDecorator`, and `wrap_with_resilience`.

These are **intentionally optional** resilience wrappers. In BioETL, resilience is primarily handled within the default HTTP composition layer (`UnifiedHTTPClient` / `HttpClientFactory`) via core components like `CircuitBreakerGuard` and `retry_config`.

These decorator implementations exist for specialized or non-HTTP usage (e.g. database connections, external gRPC clients, specialized testing scenarios) and decoupling, allowing alternative architectures to inject resilience policies without modifying the underlying adapters.

Currently, there are no default production HTTP call sites for these decorators outside of `src/bioetl/infrastructure/adapters/decorators/`. This is by design. They should not be removed as dead code, but are preserved for extensible custom resilience mappings.
