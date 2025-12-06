# 0002 Di Container Strategy

## Status
Accepted

## Context
Pipeline orchestration relies on a consistent way to wire contracts to their implementations. The current `application.container` module builds the DI graph for loggers, clients, validators, and pipeline services, and supports overrides for tests or alternative transports.

## Decision
We standardize on a lightweight dependency injection container that constructs services lazily and exposes explicit registration functions. The container composes adapters, post-transformers, and policies using domain contracts, and allows environment-specific overrides through configuration hooks.

## Consequences
- Service construction remains deterministic and testable because dependencies are registered centrally.
- New implementations can be introduced without modifying callers; only container wiring requires updates.
- Observability and configuration defaults can be injected uniformly across pipelines via shared providers.
