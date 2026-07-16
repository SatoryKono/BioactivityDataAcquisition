# BioETL Requirements

> Синхронизировано с RULES.md v6.1

## Requirements Catalog

This document catalogs testable requirements for the BioETL project.

## Requirements by Category

### Architecture Requirements
- ADR-001: Delta Lake vs Parquet storage format
- ADR-002: Medallion Architecture
- ADR-010: Local-Only Deployment
- ADR-014: Deterministic Writes and Retries
- ADR-050: Silver Structural and Gold Semantic Filter Boundary

### Data Quality Requirements
- ADR-018: Gold Strict Validation
- ADR-027: DQ Rules Externalization
- ADR-045: Data Quality Contract System

### Observability Requirements
- ADR-006: Logger and Metrics Ports
- ADR-017: Observability Architecture
- ADR-019: Observability Port Enforcement

### Resilience Requirements
- ADR-007: Circuit Breaker Implementation
- ADR-016: Error Handling Strategy

### Configuration Requirements
- ADR-025: Pipeline Config Unification
- ADR-028: Filter Rules Externalization
- ADR-038: Enum Values Externalization
- ADR-039: Unified Entity Config Format

## Version History

- v6.1: Initial requirements catalog aligned with RULES.md v6.1
