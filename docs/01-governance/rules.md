# Governance Rules

*Reference: [RULES.md](../RULES.md)*

This section contains the governance rules for the BioETL project.

## Summary

The project follows a strict set of rules to ensure code quality, maintainability, and reliability.

- **Architecture**: Hexagonal Architecture (Ports & Adapters).
- **Data**: Medallion Architecture (Bronze -> Silver -> Gold).
- **Code Style**: Python 3.11+, Type Hints, Ruff linter.
- **Testing**: >80% coverage, Unit + Integration + E2E.
- **Documentation**: Markdown, Mermaid diagrams, ADRs.

## Key Policies

1.  **No Circular Dependencies**: Domain layer must not import from Infrastructure or Application.
2.  **Dependency Injection**: All dependencies must be injected via constructors.
3.  **No Hardcoded Secrets**: Use environment variables.
4.  **Graceful Shutdown**: Handle SIGTERM/SIGINT correctly.
5.  **Observability**: Structured logging, Prometheus metrics, Tracing.

For the full set of rules, please refer to the root [RULES.md](../RULES.md) file.
