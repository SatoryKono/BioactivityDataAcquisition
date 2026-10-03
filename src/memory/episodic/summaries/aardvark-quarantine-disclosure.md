---
id: aardvark-quarantine-disclosure
title: Fix quarantine explorer unauthenticated raw payload disclosure
task_id: aardvark-quarantine-disclosure
created_at: '2026-05-31T00:32:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- git:4893461
summary: Remediated Quarantine Explorer disclosure by keeping compose traffic internal/loopback
  by default and by returning only payload previews from filtered-record detail reads;
  updated docs, Prometheus target, tests, and module coverage hash.
---

# Episodic summary

## Task

- Title: Fix quarantine explorer unauthenticated raw payload disclosure

## Outcome

- Remediated Quarantine Explorer disclosure by keeping compose traffic internal/loopback by default and by returning only payload previews from filtered-record detail reads; updated docs, Prometheus target, tests, and module coverage hash.

## Lessons learned

- Default long-lived local observability backends should stay loopback-only or internal-compose by default when routes do not enforce authentication.
- Filtered quarantine detail APIs should not return raw stored payloads; use `payload_preview` and CLI hints instead.
