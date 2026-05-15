---
id: neo4j-audit-fallback-20260514
title: Fix Neo4j audit connection defaults
task_id: neo4j-audit-fallback-20260514
created_at: '2026-05-14T18:20:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Aligned resolve_neo4j_connection audit mode with documented audit-instance
  defaults: use neo4j/audit_secure_password and port 7475 when audit-specific env
  vars are absent, without falling back to default MCP credentials.'
---

# Episodic summary

## Task

- Title: Fix Neo4j audit connection defaults

## Outcome

- Aligned resolve_neo4j_connection audit mode with documented audit-instance defaults: use neo4j/audit_secure_password and port 7475 when audit-specific env vars are absent, without falling back to default MCP credentials.

## Lessons learned

- Replace with durable follow-up if needed
