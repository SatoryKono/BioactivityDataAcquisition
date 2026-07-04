______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# Deployment & Tooling Extras

> **Status:** Extended / non-default operations material.
>
> This subtree is intentionally separated from the main operations runbooks.
> It contains:
>
> - experimental runtime deployment material that does **not** define the
>   supported ADR-010 operating model;
> - auxiliary tooling setup notes that may use Docker or external services but
>   do **not** change BioETL runtime policy.

Do **not** use this subtree as the default operator path. For supported
day-to-day runtime operation, start from [Operations README](../README.md) and
the runbooks linked there.

## Scope Boundary

BioETL's supported runtime profile remains:

- Local-Only single-instance execution
- filesystem-backed checkpoints and storage
- in-memory locking
- no Kubernetes, Redis, or Docker-based runtime orchestration in the standard
  development/operations path

### Supported Bootstrap Path

Этот subtree не дублирует поддерживаемый bootstrap. Для локальной установки и
первого запуска используйте только основные entrypoints:

- [Quick Start](../../../README.md#quick-start) в корневом `README.md`
- [Running Pipelines](../../03-guides/running-pipelines.md)
- [CLI Reference](../../04-reference/cli.md)

Поддерживаемый bootstrap path на текущей ветке:

- `uv sync --extra dev --extra tests --extra tracing`
- `uv run python -m scripts.ops setup-plugins`
- для mixed Windows + WSL: `scripts/engineering/dev/setup_env_windows.ps1` или
  `scripts/engineering/dev/setup_env_wsl.sh`

Прямой ad-hoc путь `uv sync` + ручная активация окружения здесь намеренно не
нормируется второй раз, чтобы этот experimental subtree не расходился с
основным README и guide'ом запуска.

### Supported Runbooks

Для поддерживаемых operational procedures используйте основной раздел operations:

- [Operations README](../README.md)
- [Runbooks Index](../runbooks/index.md)
- [ADR-010 Local-Only Deployment](../../02-architecture/decisions/ADR-010-local-only-deployment.md)

Repo-only drafts, experimental notes, and historical setup material may
reference this subtree, but they do not override the supported Local-Only
runtime posture.

## Contents

### Experimental Runtime Deployment

- [Kubernetes Deployment Guide](deployment-guide.md)
- [Kubernetes Manifests Summary](k8s-summary.md)

These pages are retained as advanced experimental material only. They are
outside normal support, release, and incident procedures.

### Auxiliary Tooling Setup

- [Neo4j Memory Configuration Guide](neo4j-memory-setup.md)
- [MCP Neo4j Memory Configuration - Setup Summary](mcp-neo4j-memory-summary.md) — archived setup note

These pages describe optional Neo4j/MCP tooling and do not redefine BioETL's
runtime deployment architecture.

The longer implementation snapshot remains available as a historical backlink
target at `mcp-neo4j-memory-final-summary.md`, but it is intentionally omitted
from the primary reading path.
