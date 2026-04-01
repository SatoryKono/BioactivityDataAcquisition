______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# MCP Neo4j Memory Configuration - Archived Setup Summary

> Scope note: This document describes auxiliary Neo4j/MCP tooling history. It
> is not BioETL runtime deployment guidance and does not change ADR-010
> Local-Only policy.

> Historical note: older documentation referenced a live
> `.ai/mcp/neo4j-memory/` package. That package is not present in the current
> repository checkout, so this page is kept only as an archival summary.

## Status

Archived reference. This page intentionally avoids restating obsolete runnable
commands or package internals that would drift from the current repository.

## What Was Historically Covered

The older setup narrative documented:

- Docker Compose based Neo4j startup
- environment-driven memory tuning profiles
- a previously documented MCP server package layout
- troubleshooting and quick-start notes for optional Neo4j tooling

Those points remain useful as context, but not as an authoritative setup guide
for the current tree.

## Current Docs To Use

- [Neo4j Memory Configuration Guide](neo4j-memory-setup.md)
- [Deployment & Tooling Extras](README.md)
- [MCP Neo4j Memory - Archived Implementation Snapshot](mcp-neo4j-memory-final-summary.md)

## Archive Boundary

If you need a current procedure, use the living docs above. If you need to
understand why older references mention Neo4j/MCP setup artifacts, this page is
the compact provenance note for that historical documentation wave.
