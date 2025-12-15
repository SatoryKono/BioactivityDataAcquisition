# Changelog

All notable changes to the BioETL project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Documentation audit report (`docs/00-project_rules/AUDIT-REPORT.md`)
- Missing directory structure for full RULES.md compliance
- Pipeline review checklist template (`docs/templates/pipeline-review-checklist.md`)
- Diagramming policy (`docs/01-architecture/diagrams/00-diagramming-policy.md`)
- Project navigator (`docs/00-map.md`)
- This CHANGELOG.md file

### Fixed
- Quick Reference table section numbers in `docs/00-project_rules/00-rules-summary.md`
- Path references in `docs/01-architecture/05-physical-layout.md`

---

## [5.0.0] - 2025-12-15

### RULES.md v5.0 - Production Ready

#### Added
- **Governance**: RFC 2119 requirement levels (MUST/SHOULD/MAY)
- **Entity ID vs Content Hash**: Clear distinction and documentation
- **Bronze Lifecycle**: Format versioning policy (`/v1/`, `/v2/`)
- **Hard Limits**: 50,000 partitions max, UUID/Hash/Free-text keys prohibited
- **Threat Model Scope**: Security focus areas defined
- **Log Schema**: Mandatory fields specification (§3.2.1)
- **Provider Health Matrix**: Health check endpoints for all providers
- **Circuit Breaker Half-Open**: Observability metrics added
- **Backfill Lock Timeouts**: `--wait-for-lock TIMEOUT_SEC` option
- **Generic Health Probes**: For providers without dedicated endpoints
- **Field Deprecation Workflow**: 14-day dual-write period (App E.3)

#### Changed
- Circuit Breaker recovery now includes `trips_total` metric
- Backfill lock enforcement with configurable wait mode
- Provider health monitoring with three-state system (Healthy/Degraded/Unhealthy)

---

## [4.6.0] - 2025-12-15

### RULES.md v4.6 - Governance & Stability

#### Added
- RFC 2119 keyword definitions
- Entity ID vs Content Hash clarification
- Bronze Lifecycle documentation
- Hard Limits for partitioning
- Threat Model Scope section
- Log Schema specification
- Provider Health Matrix
- Circuit Breaker details
- Backfill Locking mechanism
- Deprecation workflows

---

## [4.5.0] - 2025-05-20

### RULES.md v4.5 - Final Polish & Governance

#### Added
- Medallion Architecture paths
- DQ threshold levels
- Observability requirements
- Fencing Tokens for locks
- Security IAM principles

---

## [4.4.0] - 2025-05-20

### RULES.md v4.4 - Resilience & Operations

#### Added
- Circuit Breaker pattern
- DR Runbooks
- Quarantine Operations
- Environment Isolation
- Salt Rotation strategy

---

## [4.3.0] - 2025-05-20

### RULES.md v4.3 - Security & DR

#### Added
- Salted Hashes for PII
- RPO/RTO definitions
- Heartbeat-based Locks
- Environments specification
- Delta Lake Infrastructure

---

## [4.2.0] - 2025-05-20

### RULES.md v4.2 - Delta Lake Strategy

#### Added
- Delta Lake as primary Silver/Gold format
- Unified Quarantine Schema
- Threshold adjustments

#### Deprecated
- Raw Parquet in Silver layer (use Delta Lake)

---

## [4.0.0] - 2025-05-20

### RULES.md v4.0 - Data Contracts

#### Added
- Data Contracts (§7.1)
- Partitioning Strategy (§2.5)
- NULL Policy (§2.6)
- Recovery Playbook (App C)

---

## [3.0.0] - 2025-05-20

### RULES.md v3.0 - Lineage & Concurrency

#### Added
- Data Lineage (§2.3)
- Backfill/Replay (§2.4)
- Concurrency controls (§3.3)
- Graceful Shutdown (§5.3)
- Developer Experience (§8)

---

## [2.0.0] - 2025-05-20

### RULES.md v2.0 - Error Classification

#### Added
- Error classification (Critical/Recoverable/DQ)
- Medallion Architecture
- Rate limiting requirements
- Russian translation

---

## [1.0.0] - 2025-04-01

### RULES.md v1.0 - Initial Release

#### Added
- Initial project rules draft
- Basic architecture guidelines
- Core data flow patterns

---

## Migration Notes

### Migrating to v5.0

1. **Update all documentation** to reference RULES.md v5.0
2. **Review RFC 2119 compliance**: Ensure MUST/SHOULD/MAY are used correctly
3. **Add Log Schema fields**: `ts`, `level`, `run_id`, `pipeline`, `stage`
4. **Configure Provider Health**: Implement three-state monitoring
5. **Update Circuit Breaker**: Add `circuit_breaker_state` and `trips_total` metrics

### Breaking Changes in v5.0

- Log Schema now has mandatory fields (§3.2.1)
- Backfill locks require explicit `:exclusive` suffix
- Provider Health monitoring is now required

---

## Links

- [RULES.md](RULES.md) - Current project rules
- [docs/00-map.md](docs/00-map.md) - Documentation navigator
- [GitHub Releases](https://github.com/SatoryKono/BioactivityDataAcquisition/releases)
