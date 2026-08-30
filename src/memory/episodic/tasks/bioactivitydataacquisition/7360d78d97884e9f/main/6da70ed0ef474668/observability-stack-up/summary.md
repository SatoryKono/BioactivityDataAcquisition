---
record_id: observability-stack-up
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 2de8ba422c50e305468362cd290c7f2b6a1ab760
branch: main
worktree_id: 7360d78d97884e9f
task_id: observability-stack-up
actor:
  runtime: grok
  agent: grok-4.6
  model: grok-4.6
created_at: '2026-08-25T11:35:39.133116+00:00'
source_refs:
- docker-compose.monitoring.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 71e10a57ae9bbe2289d2cc24be57894d6280bee1aff5ed1de78711764233b9df
id: observability-stack-up
title: Check and raise observability stack
ttl_days: 14
confidence: episodic
summary: 'Docker Desktop was down (docker-desktop WSL stopped). Started engine, recreated
  main+monitoring from E:\github\BioactivityDataAcquisition. Grafana dashboard_profile=full,
  ops_http=ready identity_matched, all Prom targets UP including bioetl. Disabled
  hung watchdog registered against BioactivityDataAcquisition2 (ensure-stable stops
  monitoring). Residual: .env BIOETL_RUNTIME_SOURCE_ID conflicts with checkout identity
  (not edited).'
---

# Episodic summary

## Task

- Title: Check and raise observability stack

## Outcome

- Docker Desktop was down (docker-desktop WSL stopped). Started engine, recreated main+monitoring from E:\github\BioactivityDataAcquisition. Grafana dashboard_profile=full, ops_http=ready identity_matched, all Prom targets UP including bioetl. Disabled hung watchdog registered against BioactivityDataAcquisition2 (ensure-stable stops monitoring). Residual: .env BIOETL_RUNTIME_SOURCE_ID conflicts with checkout identity (not edited).

## Lessons learned

- Replace with durable follow-up if needed
