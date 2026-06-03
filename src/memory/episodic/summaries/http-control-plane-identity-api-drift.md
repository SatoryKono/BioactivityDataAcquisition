---
id: http-control-plane-identity-api-drift
title: Fix HTTP control-plane identity public API drift
task_id: http-control-plane-identity-api-drift
created_at: '2026-06-03T10:55:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/interfaces/http/test_control_plane_identity.py
summary: 'Restored legacy-compatible HTTP control-plane identity public entrypoints:
  AnchorSpec legacy aliases/constructor names, AnchorValues, extract_*_anchors wrappers,
  validate_identity_payload, ControlPlaneSourceModel, spec version helpers, and format
  validators. Targeted HTTP identity tests pass; ruff check/format on touched src
  modules pass; module coverage inventory and architecture dependency docs were refreshed
  and guards pass.'
---

# Episodic summary

## Task

- Title: Fix HTTP control-plane identity public API drift

## Outcome

- Restored legacy-compatible HTTP control-plane identity public entrypoints: AnchorSpec legacy aliases/constructor names, AnchorValues, extract_*_anchors wrappers, validate_identity_payload, ControlPlaneSourceModel, spec version helpers, and format validators. Targeted HTTP identity tests pass; ruff check/format on touched src modules pass; module coverage inventory and architecture dependency docs were refreshed and guards pass.

## Lessons learned

- Replace with durable follow-up if needed
