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

### Local Installation

Для локальной установки и разработки используйте [Quick Start](../../../README.md#quick-start) в главном README:

**Требования:**
- Python 3.12 или 3.13
- uv (Python package manager)

**Установка:**
```bash
# Клонирование репозитория
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition

# Установка зависимостей через uv
uv sync

# Активация виртуального окружения
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows
```

**Запуск:**
```bash
# Список доступных pipeline surface
bioetl config list-pipelines

# Канонический запуск pipeline
bioetl run --pipeline chembl_activity

# Module-form entrypoint также поддерживается после активации окружения
python -m bioetl run --pipeline chembl_activity
```

Для детальной информации о командной интерфейсе см. [CLI Reference](../../04-reference/cli.md).

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
