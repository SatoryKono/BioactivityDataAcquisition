# BioETL Source Code

This tree contains the runtime implementation of BioETL. Use this README as a
code-navigation map, not as a product overview.

## Start Here

Use the following entrypoints when tracing runtime behavior:

| What you are tracing | Start here |
| --- | --- |
| CLI command dispatch | `interfaces/cli/main.py` |
| Health / readiness HTTP surface | `interfaces/http/` |
| Pipeline execution bootstrap | `composition/execution_api.py` |
| Control-plane and inspection services | `composition/control_plane_runtime.py` |
| Runtime assembly / dependency wiring | `composition/` |
| Single-pipeline orchestration | `application/core/` |
| Composite orchestration | `application/composite/` |
| Run-manifest / run-ledger behavior | `application/services/control_plane/` |
| Canonical Medallion write-mode policy | `domain/medallion.py` |
| External adapters and persistence | `infrastructure/` |

## Canonical Ownership

The package is intentionally split by architectural responsibility:

| Package | Owns |
| --- | --- |
| `domain/` | Pure business rules, value objects, policies, and cross-layer contracts |
| `application/` | Use-case orchestration, runners, composite flows, and service-level coordination |
| `infrastructure/` | HTTP/filesystem/Delta/control-plane adapter implementations |
| `composition/` | Dependency injection, runtime assembly, and sanctioned public bootstrap seams |
| `interfaces/` | CLI, HTTP, and orchestration-facing boundary adapters |

## Reading Order

1. Start with `interfaces/` when the question begins from an operator surface.
2. Move into `composition/` to see which services and adapters are assembled.
3. Follow into `application/` for runtime orchestration and control-plane logic.
4. Drop into `domain/` for invariants, enums, and stable policy definitions.
5. Inspect `infrastructure/` only when the behavior depends on a concrete adapter or storage backend.

## Local Package Maps

These package READMEs carry the next level of detail:

- `application/README.md`
- `composition/README.md`
- `interfaces/README.md`

When those maps and the published docs diverge, treat the published contract and
CLI docs as the operator-facing source of truth, and treat these package maps as
code-navigation aids.
