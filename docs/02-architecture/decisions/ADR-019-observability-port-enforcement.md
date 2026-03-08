# ADR-019: Observability Port Enforcement

**Status:** Accepted
**Date:** 2025-12-26
**Decision makers:** @BioETL-Team
**Supersedes:** None
**Related:** ADR-006 (Logger/Metrics Ports), ADR-017 (Observability Architecture)

## Context

Following the adoption of `LoggerPort` abstraction (ADR-006), there was still direct usage of `structlog` in the `interfaces` layer:

1. `src/bioetl/interfaces/cli.py` imported `structlog.BoundLogger` for type hints
2. `src/bioetl/interfaces/orchestration/signals.py` imported and used `structlog` directly

This violated the principle that all layers should use ports, not concrete implementations.

## The Decision

We have chosen to:

1. **Enforce `LoggerPort` usage in all layers** including `interfaces`
2. **Remove all direct `structlog` imports** from `application` and `interfaces` layers
3. **Pass logger via Dependency Injection** to signal handlers
4. **Enforce via architecture tests** with zero exemptions

## Justification

### 1. Layer Independence

The `interfaces` layer should be infrastructure-agnostic:

```
┌──────────────────────────────────────────────────┐
│                   interfaces                      │
│  cli.py, signals.py                              │
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
) -> None:
    ...
```

### 3. Consistency with ADR-006

ADR-006 established that all logging should go through `LoggerPort`. This ADR extends that principle to:

| Layer | Before | After |
|-------|--------|-------|
| domain | ❌ No logging | ❌ No logging |
| application | ✅ LoggerPort | ✅ LoggerPort |
| composition | ✅ Creates adapters | ✅ Creates adapters |
| infrastructure | ✅ structlog allowed | ✅ structlog allowed |
| **interfaces** | ❌ structlog direct | ✅ LoggerPort |

## Implementation Details

### 1. CLI Changes (`cli.py`)

```python
# Before
if TYPE_CHECKING:
    import structlog  # ← VIOLATION

def _get_runner_logger(runner: PipelineRunner) -> structlog.BoundLogger | None:
    ...

# After
if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort  # ← CORRECT

def _get_runner_logger(runner: PipelineRunner) -> LoggerPort | None:
    ...
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
2. **Testability**: Signal handlers can be unit tested
3. **Flexibility**: Logger implementation can be swapped without touching interfaces
4. **Enforcement**: Architecture tests prevent regression

### Negative

1. **Minor breaking change**: Functions accepting logger now have optional parameter
2. **Migration effort**: Required updates to tests

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
