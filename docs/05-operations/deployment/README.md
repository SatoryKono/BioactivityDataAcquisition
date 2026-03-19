# Deployment & Tooling Extras

> **Status:** Extended / non-default operations material.
>
> This subtree is intentionally separated from the main operations runbooks.
> It contains:
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

Use the main operations section for supported runbooks:

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
- [MCP Neo4j Memory Configuration - Setup Summary](mcp-neo4j-memory-summary.md)
- [MCP Neo4j Memory - Complete Setup Summary](mcp-neo4j-memory-final-summary.md)

These pages describe optional Neo4j/MCP tooling and do not redefine BioETL's
runtime deployment architecture.
