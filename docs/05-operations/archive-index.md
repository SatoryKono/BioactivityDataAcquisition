______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: Informational
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-02'

______________________________________________________________________

# Operations Archive Index

## Trigger

- Use this page when a document is still worth keeping as historical evidence but
  should no longer appear as current operator guidance.

## Purpose

- Centralize archive-only operational material in one published location.
- Distinguish current operator guidance from historical release and verification
  evidence.

## Current Scope

### Historical verification and release evidence

- [Historical Release Checklist (v5.9)](release-checklist.md)
- [Docker Helper Credential History Audit](verification/docker-helper-credential-history-audit.md)
- [Endpoint Validation Checklist](verification/endpoint-validation-checklist.md)
- [VCR Provider Rebalancing](verification/vcr-provider-rebalancing.md)
- [VCR Test Tasks](verification/vcr-test-tasks.md)

### Historical / auxiliary deployment notes

- [Deployment & Tooling Extras](deployment/README.md)
- [MCP Neo4j Memory Summary](deployment/mcp-neo4j-memory-summary.md)
- [MCP Neo4j Memory Final Summary](deployment/mcp-neo4j-memory-final-summary.md)

## Archive Rules

- Archive pages MAY be used as examples, evidence, or migration context.
- Archive pages MUST NOT be treated as the current default operator workflow
  unless a current published page explicitly says so.
- When an archived page is still linked from a current guide, that link should
  explain why the page remains historically relevant.

## Canonical Current Guidance

- For current operator workflows, start with:
  - [Operations Documentation](README.md)
  - [Operations Runbooks](runbooks/index.md)
  - [Monitoring Guide](01-monitoring-guide.md)
  - [VACUUM Retention](vacuum-retention.md)
