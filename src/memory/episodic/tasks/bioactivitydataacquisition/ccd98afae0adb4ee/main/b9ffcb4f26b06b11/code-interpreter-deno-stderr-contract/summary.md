---
record_id: code-interpreter-deno-stderr-contract
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 46d28194903253b6a18e2343778e252b2865b120
branch: main
worktree_id: ccd98afae0adb4ee
task_id: code-interpreter-deno-stderr-contract
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T06:44:55.865249+00:00'
source_refs:
- scripts/ai/mcp/mcp_code_interpreter_wrapper.ps1
- tests/unit/repo_backed/scripts/ai/mcp/test_mcp_wrapper_contracts.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 9b5b2ede3cb8b897771b258294e70a22865584de4f772b5933d29584f5457344
id: code-interpreter-deno-stderr-contract
title: Fix PowerShell Deno fallback stderr
ttl_days: 14
confidence: episodic
summary: Replaced PowerShell Write-Error records in the code-interpreter wrapper with
  direct Console.Error lines so required fallback diagnostics remain contiguous and
  stable regardless of host formatting width. All three Windows code-interpreter wrapper
  tests passed; repeated Windows stress invocation was blocked by transient WSL UtilBindVsockAnyPort
  failure.
---

# Episodic summary

## Task

- Title: Fix PowerShell Deno fallback stderr

## Outcome

- Replaced PowerShell Write-Error records in the code-interpreter wrapper with direct Console.Error lines so required fallback diagnostics remain contiguous and stable regardless of host formatting width. All three Windows code-interpreter wrapper tests passed; repeated Windows stress invocation was blocked by transient WSL UtilBindVsockAnyPort failure.

## Lessons learned

- Replace with durable follow-up if needed
