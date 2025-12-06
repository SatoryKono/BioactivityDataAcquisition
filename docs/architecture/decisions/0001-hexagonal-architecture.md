# 0001 Hexagonal Architecture

## Status
Accepted

## Context
BioETL separates domain logic from infrastructure concerns and keeps application orchestration thin. Existing layers (`interfaces`, `application`, `domain`, `infrastructure`) follow ports-and-adapters so that domain contracts remain stable while implementations vary by provider or transport.

## Decision
We adopt hexagonal architecture as the governing structure. All external interactions enter through adapters in `interfaces` and `infrastructure`, while `domain` holds contracts, validation rules, and schemas. The `application` layer composes pipelines and services through these contracts without binding to concrete transports.

## Consequences
- Domain rules stay testable and deterministic because infrastructure-specific concerns are kept at the edges.
- New providers or transports are added by supplying new adapters that satisfy domain contracts without touching orchestration logic.
- Documentation and diagrams will describe components by port/adapter roles to keep architectural drift visible.
