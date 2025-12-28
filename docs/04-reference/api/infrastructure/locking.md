# Locking

Infrastructure for concurrency control and locking.

## Overview

The locking infrastructure ensures that only one pipeline instance can process a specific entity set at a time. It implements the `LockPort` interface.

## Implementations

### MemoryLock

In-memory locking implementation for local development and testing.

::: bioetl.infrastructure.locking.memory_lock.MemoryLock
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - acquire
            - release
            - heartbeat
            - validate_owner
            - aclose

## See Also

- [Domain Ports](../domain/ports.md) - LockPort interface
- [Infrastructure Overview](../infrastructure.md)
