______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# MCP Neo4j Memory - Archived Implementation Snapshot

> Scope note: this page documents historical auxiliary tooling only. It is not
> BioETL runtime deployment guidance and does not change ADR-010 Local-Only
> policy.

> Historical note: the repository no longer contains the previously documented
> `.ai/mcp/neo4j-memory/` package. This page is therefore an archive snapshot,
> not an executable implementation guide.

## Purpose

This page answers two narrow questions:

1. What kind of Neo4j/MCP integration had been documented historically?
1. Which current documents should operators read instead?

## Historical Capability Envelope

The archived implementation narrative described:

- a dedicated MCP package for Neo4j-oriented tooling
- profile-based Neo4j memory configuration
- health and usage inspection helpers
- local containerized startup notes
- optional Kubernetes-oriented deployment references

These items are preserved as historical intent only.

## Current Docs To Use

- [Neo4j Memory Configuration Guide](neo4j-memory-setup.md)
- [Deployment & Tooling Extras](README.md)
- [BioETL Kubernetes Deployment Guide](deployment-guide.md)
- [BioETL Kubernetes Manifests - Summary](k8s-summary.md)

## Archive Policy

Detailed procedures, commands, and package-layout explanations should live only
in current operator-facing documents. This archive page should remain compact so
it does not become a second drifting source of truth.
