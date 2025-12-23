# ADR-003: Why Redis for Distributed Locking?

*   **Status**: ~~Accepted~~ **Superseded by ADR-010**
*   **Date**: 2025-05-20 (Implicitly from RULES.md v3.0)
*   **Superseded By**: [ADR-010: Local-Only Deployment](ADR-010-local-only-deployment.md)
*   **Context**: The system needs a mechanism to ensure that only one instance of a given pipeline (e.g., `chembl_activity`) can run at a time, especially during resource-intensive operations like backfills. This prevents race conditions, data corruption, and redundant API calls.

> **Note**: This ADR has been superseded. The project now uses local-only deployment
> with in-memory locking (MemoryLock). See ADR-010 for details.

## The Decision

We have chosen **Redis** as the backend for our distributed locking mechanism. The implementation uses the `SETNX` (SET if Not eXists) command combined with a TTL (Time To Live) and a heartbeat mechanism.

This decision is codified in Section 3.3 of `RULES.md`.

## Justification

Several options were considered for distributed locking, including database locks and Zookeeper. Redis was chosen for the following reasons:

1.  **Performance**: Redis is an in-memory data store, making lock acquisition and release operations extremely fast (sub-millisecond). This is critical to avoid adding significant overhead to pipeline startup times.

2.  **Atomic Operations**: The `SETNX` command is atomic. This guarantees that even if multiple pipeline instances try to acquire the same lock simultaneously, only one will succeed.

3.  **Built-in TTL (Time To Live)**: Redis allows setting an expiration time on a key. This is a crucial safety feature that prevents indefinite deadlocks. If a worker crashes without releasing its lock, the lock will automatically expire after the TTL, allowing other workers to proceed.

4.  **Simplicity of Implementation**: The logic for acquiring a lock is a single, simple command. The heartbeat mechanism (periodically updating the TTL) is also straightforward to implement. This simplicity reduces the risk of bugs in a critical part of the system.

5.  **Lightweight and Widely Available**: Redis is a lightweight dependency and is available as a managed service on all major cloud platforms. It is also easy to run locally via Docker for development.

## Alternatives Considered

*   **Database Locks (e.g., Postgres)**: Using table-level or row-level locks in a relational database is a valid approach. However, it puts additional load on the analytical database, can be slower, and requires more careful transaction management to avoid long-lived locks.
*   **Zookeeper**: Zookeeper is the gold standard for distributed coordination, but it is a much heavier dependency, more complex to operate, and is generally overkill for a simple distributed mutex requirement.

## Consequences

*   **New Dependency**: The project now has a hard dependency on a running Redis instance for all pipeline executions. This is managed via Docker Compose for local development.
*   **Single Point of Failure**: If the Redis server goes down, no pipelines can start. This risk is mitigated by using a managed, high-availability Redis instance in production.
*   **Clock Drift**: The TTL mechanism relies on a reasonably consistent sense of time between Redis and the workers. Severe clock drift could theoretically cause issues, but this is rare in modern cloud environments.
