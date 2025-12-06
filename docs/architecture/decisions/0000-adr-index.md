# 0000 Adr Index

| ID | Title | Status | Summary |
| --- | --- | --- | --- |
| [0001](0001-hexagonal-architecture.md) | Hexagonal Architecture | Accepted | Adopt ports-and-adapters layering to isolate domain from infrastructure and keep application orchestration thin. |
| [0002](0002-di-container-strategy.md) | Di Container Strategy | Accepted | Use a composable dependency injection container in `application.container` to wire services and override providers per environment. |
| [0003](0003-provider-registry-via-config.md) | Provider Registry Via Config | Accepted | Drive provider registration through declarative YAML config with canonical IDs and validation. |
| [0004](0004-pipeline-hooks-for-observability.md) | Pipeline Hooks For Observability | Accepted | Provide structured lifecycle hooks in pipeline runners for logging, metrics, and trace propagation. |
