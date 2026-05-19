---
id: contract-registry-yaml-fix-20260518
title: "\u041F\u043E\u0447\u0438\u043D\u043A\u0430 YAML registry \u0434\u043B\u044F\
  \ neo4j memory snapshot"
task_id: contract-registry-yaml-fix-20260518
created_at: '2026-05-18T18:29:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/base/contract_registry.yaml
summary: Fixed malformed chembl.target normalization_profile_hash entry in configs/base/contract_registry.yaml,
  restored canonical profile hash, validated YAML parsing, and confirmed contract
  registry coverage test passes. Snapshot invariant pytest no longer fails in YAML
  parsing but still times out deeper in build_snapshot.
---

# Episodic summary

## Task

- Title: Починка YAML registry для neo4j memory snapshot

## Outcome

- Fixed malformed chembl.target normalization_profile_hash entry in configs/base/contract_registry.yaml, restored canonical profile hash, validated YAML parsing, and confirmed contract registry coverage test passes. Snapshot invariant pytest no longer fails in YAML parsing but still times out deeper in build_snapshot.

## Lessons learned

- Replace with durable follow-up if needed
