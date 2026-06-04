______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

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
# Запуск pipeline
python -m bioetl run <pipeline-name>

# Запуск с конфигурацией
python -m bioetl run <pipeline-name> --config <config-file>
```

Для детальной информации о командной интерфейсе см. [CLI Reference](../../04-reference/cli.md).

### Supported Runbooks

Для поддерживаемых operational procedures используйте основной раздел operations:

- [Operations README](../README.md)
- [Runbooks Index](../runbooks/index.md)
- [ADR-010 Local-Only Deployment](../../02-architecture/decisions/ADR-010-local-only-deployment.md)

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
