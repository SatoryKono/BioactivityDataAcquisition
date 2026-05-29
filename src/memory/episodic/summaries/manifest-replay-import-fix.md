---
id: manifest-replay-import-fix
title: Fix ImportError for _resolve_manifest_replay_readiness_verdict
task_id: manifest-replay-import-fix
created_at: '2026-05-29T18:14:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/_run_manifest_diagnostics_replay.py
summary: Restored backward-compatible export surface by adding _resolve_manifest_replay_readiness_verdict
  to __all__ in _run_manifest_diagnostics_replay and re-running historical support
  CLI interface tests. The failing import chain no longer breaks module import.
---

# Episodic summary

## Task

- Title: Fix ImportError for _resolve_manifest_replay_readiness_verdict

## Outcome

- Restored backward-compatible export surface by adding _resolve_manifest_replay_readiness_verdict to __all__ in _run_manifest_diagnostics_replay and re-running historical support CLI interface tests. The failing import chain no longer breaks module import.

## Lessons learned

- Replace with durable follow-up if needed
