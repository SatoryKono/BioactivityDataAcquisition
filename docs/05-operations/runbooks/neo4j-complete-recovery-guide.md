______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: Informational
  Last verified: '2026-05-26'

______________________________________________________________________

# Neo4j MCP Backend - Recovery Guide (Duplicate Notice)

> This guide is retained as a compatibility pointer.
>
> **Canonical runbook:** [Neo4j Backend Recovery - Quick Start](neo4j-backend-recovery-quick-start.md)

Use the canonical quick-start page for active operator recovery flow.
Historical deep-dive notes should be tracked via archive routing when needed.

## Trigger

Use this compatibility page only when an older link points to
`neo4j-complete-recovery-guide.md`. Active recovery starts at
[Neo4j Backend Recovery - Quick Start](neo4j-backend-recovery-quick-start.md).

## Impact

This page is not an active recovery procedure. Using it as a standalone runbook
can bypass the current quick-start checks for optional Neo4j/MCP tooling.
BioETL runtime remains Local-Only and does not require Neo4j.

## Preconditions

- The task is about optional project-memory or MCP tooling, not BioETL runtime
  execution.
- Access to the canonical quick-start:
  [neo4j-backend-recovery-quick-start.md](neo4j-backend-recovery-quick-start.md).

## Procedure

1. Open [Neo4j Backend Recovery - Quick Start](neo4j-backend-recovery-quick-start.md).
1. Follow its active recovery steps.
1. Keep any historical deep-dive notes outside this compatibility pointer unless
   a documentation-governance update promotes them explicitly.

## Verification

Verification is complete when the canonical quick-start checks pass or the
operator records the remaining optional-tooling blocker.

## Rollback/Recovery

Recovery is delegated to the canonical quick-start page. This compatibility
pointer has no independent rollback path.

## Post-incident

If current guidance still links here, update the link to
`neo4j-backend-recovery-quick-start.md`.

## Compliance

This page must not redefine BioETL runtime deployment policy. Neo4j/MCP remains
optional auxiliary tooling and does not override ADR-010 Local-Only runtime
requirements.
