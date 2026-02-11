# Architecture Audit Report

Date: 2026-02-11
Scope: configuration structure in `src/bioetl/domain/config*`, `src/bioetl/infrastructure/config*`, `src/bioetl/infrastructure/schemas/*config*`, and related composition/application entry points.

## Executive Summary

- Total findings: 4
- Critical (MUST): 2
- Moderate (SHOULD): 2
- Informational (MAY): 0

## Critical Findings

## [MUST] Infrastructure imports Domain configuration models directly (boundary violation)

**Location**:

- `src/bioetl/infrastructure/schemas/pipeline_config.py:26-28`
- `src/bioetl/infrastructure/schemas/base_schemas.py:13-20`
- `src/bioetl/infrastructure/config/_base.py:34-36`
- `src/bioetl/infrastructure/config/filter_config_loader.py:17-18`

**Rule Violated**: Layer import rule — `infrastructure → domain` is forbidden (except `domain.ports`).

**Evidence**:

```python
from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.configs.base import BaseClientConfig, RateLimitConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig
```

```python
from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig
from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
```

**Impact**:

- Infrastructure schema and loader code is tightly coupled to domain internals.
- Domain refactors (e.g., config field renaming) can break YAML/schema parsing layer directly.
- Violates declared hexagonal dependency direction for strict ports-based boundaries.

**Recommendation**:

```python
# in domain/ports/config_dto.py (new)
class PipelineConfigDTO(Protocol): ...


# infrastructure/schemas/* should convert to DTOs only
# composition layer should map DTO -> domain value objects
```

**Verification**:

```bash
rg -n "^from bioetl\.domain\.|^import bioetl\.domain" src/bioetl/infrastructure
```

______________________________________________________________________

## [MUST] Infrastructure config schemas depend on other infrastructure schemas for core DQ primitives (boundary erosion inside config layer)

**Location**: `src/bioetl/infrastructure/schemas/dq_config.py:29-34`

**Rule Violated**: Configuration boundary consistency (single-responsibility schema modules).

**Evidence**:

```python
from bioetl.infrastructure.schemas.pipeline_config import (
    ConditionalValidationConfig,
    CrossFieldValidationConfig,
    DQReportConfig,
    FieldValidationConfig,
)
```

**Impact**:

- `dq_config.py` cannot evolve independently from `pipeline_config.py`.
- Raises change blast radius and increases risk of accidental regression in standalone DQ config parsing.

**Recommendation**:

```python
# move shared validation schema models to
# infrastructure/schemas/dq_primitives.py
# both pipeline_config.py and dq_config.py import from dq_primitives.py
```

**Verification**:

```bash
rg -n "from bioetl\.infrastructure\.schemas\.pipeline_config import" src/bioetl/infrastructure/schemas/dq_config.py
```

## Moderate Findings

## [SHOULD] Dual namespace for domain configuration (`config` vs `configs`) is inconsistent and error-prone

**Location**:

- `src/bioetl/domain/config/__init__.py:1-8`
- `src/bioetl/domain/configs/__init__.py:1-4`
- `src/bioetl/domain/__init__.py:40-54`

**Rule Violated**: Naming consistency (`snake_case` module naming and single canonical API surface).

**Evidence**:

```python
from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
from bioetl.domain.configs import BaseClientConfig, BaseProviderConfig, RateLimitConfig
```

**Impact**:

- Two near-identical names (`config`, `configs`) increase cognitive load.
- New contributors can place new objects into the wrong namespace.
- Raises risk of circular re-export growth in `domain/__init__.py`.

**Recommendation**:

```text
1) Keep `bioetl.domain.config` as canonical package.
2) Move `RateLimitConfig/BaseClientConfig/BaseProviderConfig` under `domain/config/http.py`.
3) Leave `domain/configs` as temporary deprecation shim for 1-2 releases.
```

**Verification**:

```bash
rg -n "domain\.configs|from bioetl\.domain\.configs" src tests
```

______________________________________________________________________

## [SHOULD] DQ default thresholds diverge between core domain and composite schema defaults

**Location**:

- `src/bioetl/domain/config/dq.py:54-55`
- `src/bioetl/infrastructure/schemas/composite_config.py:455-460`

**Rule Violated**: Domain-specific DQ threshold policy consistency (soft 5%, hard 20% as baseline unless justified).

**Evidence**:

```python
# domain default
soft_fail_threshold: float = 0.05
hard_fail_threshold: float = 0.20
```

```python
# composite schema default
soft_fail_threshold: float = Field(default=0.10, ...)
hard_fail_threshold: float = Field(default=0.30, ...)
```

**Impact**:

- Different runtime defaults based on ingestion route can cause inconsistent alerting/fail behavior.
- Incident triage becomes harder because threshold provenance is non-obvious.

**Recommendation**:

```text
Option A: align composite defaults to 0.05/0.20.
Option B: keep 0.10/0.30, but document explicit ADR/rationale and emit startup log with active thresholds.
```

**Verification**:

```bash
rg -n "soft_fail_threshold|hard_fail_threshold" src/bioetl/domain/config/dq.py src/bioetl/infrastructure/schemas/composite_config.py
```

## Positive Observations

- Locking defaults in application config align with ADR-010 local-only model (`lock_ttl=90`, `heartbeat_interval=30`).
- Domain DQ config validates threshold ordering and bounds at object creation time.

## Plan of Remediation

### Phase 1 (P1, 1–2 days): enforce boundaries

1. Introduce config DTO protocols/interfaces at a domain port boundary for configuration transfer.
1. Refactor infrastructure schema `to_domain()` to `to_dto()` and move DTO→Domain mapping into composition layer.
1. Add architecture tests preventing `infrastructure` imports from `bioetl.domain.*` except `bioetl.domain.ports`.

### Phase 2 (P2, 1 day): normalize config namespace

1. Consolidate `domain/configs` into `domain/config`.
1. Add deprecation warnings and import shims.
1. Update docs/examples to canonical imports.

### Phase 3 (P2, 0.5–1 day): DQ threshold policy hardening

1. Decide single baseline defaults for all execution modes.
1. Add explicit config precedence docs (`global → provider → entity → runtime override`).
1. Add startup diagnostics event with effective thresholds and source.

### Phase 4 (P2, 1 day): schema modularization

1. Extract shared DQ primitive schemas from `pipeline_config.py`.
1. Make `dq_config.py` independent from `pipeline_config.py` internals.
1. Add regression tests for both standalone DQ config and pipeline config parsing.

## Verification Log

```bash
python src/tools/scripts/check_architecture.py
python src/tools/scripts/check_application_deps.py
rg -n "^from bioetl\.domain\.|^import bioetl\.domain" src/bioetl/infrastructure src/bioetl/interfaces
rg -n "domain\.configs|from bioetl\.domain\.configs" src tests
rg -n "soft_fail_threshold|hard_fail_threshold" src/bioetl/domain/config/dq.py src/bioetl/infrastructure/schemas/composite_config.py
```
