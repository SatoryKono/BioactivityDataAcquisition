______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-019: Observability Port Enforcement

**Date:** 2025-12-26
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-006 (Logger/Metrics Ports), ADR-017 (Observability Architecture)

## Context

Following the adoption of `LoggerPort` abstraction (ADR-006), there was still direct usage of `structlog` in the `interfaces` layer:

1. `src/bioetl/interfaces/cli/main.py` (historically `interfaces/cli.py`) imported `structlog.BoundLogger` for type hints
1. `src/bioetl/interfaces/orchestration/signals.py` imported and used `structlog` directly

This violated the principle that all layers should use ports, not concrete implementations.

## Decision

We have chosen to:

1. **Enforce `LoggerPort` usage in all layers** including `interfaces`
1. **Remove all direct `structlog` imports** from `application` and `interfaces` layers
1. **Pass logger via Dependency Injection** to signal handlers
1. **Enforce via architecture tests** with zero exemptions

## Justification

### 1. Layer Independence

The `interfaces` layer should be infrastructure-agnostic:

```
┌──────────────────────────────────────────────────┐
│                   interfaces                      │
│  cli/main.py (historical shim: cli.py), signals.py│
│  Uses: LoggerPort (not structlog)                │
└───────────────────────┬──────────────────────────┘
                        │ depends on
                        ▼
┌──────────────────────────────────────────────────┐
│                   composition                     │
│  bootstrap.py (creates structlog adapter)        │
└───────────────────────┬──────────────────────────┘
                        │ creates
                        ▼
┌──────────────────────────────────────────────────┐
│                 infrastructure                    │
│  StructlogAdapter implements LoggerPort          │
└──────────────────────────────────────────────────┘
```

### 2. Testability

Signal handlers can now be tested without mocking `structlog`:

```python
# Before: hard to test, requires structlog mock
import structlog

log = structlog.get_logger()


# After: easy to test with any LoggerPort implementation
def setup_shutdown_handlers(
    shutdown_signal: ShutdownSignal,
    logger: LoggerPort | None = None,  # Injectable
) -> None: ...
```

### 3. Consistency with ADR-006

ADR-006 established that all logging should go through `LoggerPort`. This ADR extends that principle to:

| Layer          | Before               | After                |
| -------------- | -------------------- | -------------------- |
| domain         | ❌ No logging        | ❌ No logging        |
| application    | ✅ LoggerPort        | ✅ LoggerPort        |
| composition    | ✅ Creates adapters  | ✅ Creates adapters  |
| infrastructure | ✅ structlog allowed | ✅ structlog allowed |
| **interfaces** | ❌ structlog direct  | ✅ LoggerPort        |

## Implementation Details

### 1. CLI Changes (`interfaces/cli/main.py`)

```python
# Before
if TYPE_CHECKING:
    import structlog  # ← VIOLATION


def _get_runner_logger(runner: PipelineRunner) -> structlog.BoundLogger | None: ...


# After
if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort  # ← CORRECT


def _get_runner_logger(runner: PipelineRunner) -> LoggerPort | None: ...
```

### 2. Signal Handler Changes (`signals.py`)

```python
# Before
import structlog


def setup_shutdown_handlers(shutdown_signal: ShutdownSignal) -> None:
    log = structlog.get_logger()
    log.warning("Received signal...")


# After
from bioetl.domain.ports import LoggerPort


def setup_shutdown_handlers(
    shutdown_signal: ShutdownSignal,
    logger: LoggerPort | None = None,  # Optional for backward compat
) -> None:
    if logger is not None:
        logger.warning("Received signal...")
```

### 3. Architecture Test Enforcement

```python
# tests/architecture/test_no_structlog_in_application_interfaces.py

# All exemptions removed
EXEMPTED_FILES: set[str] = set()  # Empty - zero tolerance

def test_no_structlog_import_in_application_interfaces(...):
    """Verify no direct structlog imports in application/interfaces layers."""
    ...
```

## Allowed Patterns

### ✅ Allowed

```python
# In interfaces layer
from bioetl.domain.ports import LoggerPort


def my_function(logger: LoggerPort) -> None:
    logger.info("Message")


# In infrastructure layer (adapters only)
import structlog


class StructlogAdapter:
    def __init__(self):
        self._logger = structlog.get_logger()
```

### ❌ Forbidden

```python
# In interfaces layer
import structlog  # FORBIDDEN

# In application layer
from structlog import BoundLogger  # FORBIDDEN
```

## Consequences

### Positive

1. **Clean architecture**: All layers respect port abstractions
1. **Testability**: Signal handlers can be unit tested
1. **Flexibility**: Logger implementation can be swapped without touching interfaces
1. **Enforcement**: Architecture tests prevent regression

### Negative

1. **Minor breaking change**: Functions accepting logger now have optional parameter
1. **Migration effort**: Required updates to tests

## Verification

Run architecture tests to verify compliance:

```bash
pytest tests/architecture/test_no_structlog_in_application_interfaces.py -v
```

Expected output:

```
test_no_structlog_import_in_application_interfaces PASSED
```

## References

- Commit `68ab51b`: Implementation of this ADR
- ADR-006: LoggerPort definition
- ADR-017: Observability architecture overview
- RULES.md §11: Anti-Patterns (structlog in application/interfaces)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                    |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-019-observability-port-enforcement.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                  |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                            |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`        |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
