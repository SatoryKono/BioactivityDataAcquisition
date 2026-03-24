# BioETL Source Map

`src/bioetl/` is organized around the project's five runtime layers.

## Layer Map

| Layer | Purpose | Start Here |
| --- | --- | --- |
| `domain/` | Pure business semantics, types, ports, validation, and model vocabulary | [`domain/README.md`](domain/README.md) |
| `application/` | Use-case orchestration, pipeline services, runtime coordination | [`application/README.md`](application/README.md) |
| `infrastructure/` | Concrete adapters, storage, config loading, observability implementations | [`infrastructure/README.md`](infrastructure/README.md) |
| `composition/` | Dependency injection, wiring, runtime assembly, provider registration | [`composition/README.md`](composition/README.md) |
| `interfaces/` | CLI, HTTP, and external-facing invocation seams | [`interfaces/README.md`](interfaces/README.md) |

## Reading Order

1. Start with `interfaces/` if you need the command or server entrypoint.
2. Move to `composition/` to see how dependencies are wired.
3. Read `application/` for orchestration and service behavior.
4. Read `domain/` for the semantic model and policy rules.
5. Inspect `infrastructure/` only when you need a concrete adapter or storage detail.

## Placement Rules

- Put pure business rules and reusable semantic types in `domain/`.
- Put orchestration and use-case flow in `application/`.
- Put concrete I/O and framework-facing code in `infrastructure/`.
- Put factories and assembly logic only in `composition/`.
- Put user-facing or protocol-facing entrypoints in `interfaces/`.

## Structural Guidance

The current five-layer split is the accepted repository baseline. Prefer
family-level cleanup and better navigation over repo-wide package moves unless
deeper evidence shows a specific hotspot.
