# Repository Cleanup Guide

*Compatibility entrypoint; canonical cleanup guidance lives elsewhere.*

This file is retained as a stable path for older links and ad-hoc references.
It is no longer the authoritative cleanup guide.

## Canonical Cleanup Surfaces

- Active published guide:
  [cleanup-policy.md](cleanup-policy.md)
- Retention-sensitive cleanup runbook:
  [retention-sensitive-cleanup.md](../05-operations/runbooks/retention-sensitive-cleanup.md)
- Repo structure and placement policy:
  [03-file-policy.md](../00-project/governance/03-file-policy.md)

## Current Rule

Use `cleanup-policy.md` for deterministic local cleanup, repo-hygiene review
lanes, and machine-readable evidence outputs. Use the retention-sensitive
runbook before touching `data/**`, control-plane artifacts, `tests/fixtures/**`,
`docs/reports/**`, `reports/**`, or `docs/99-archive/**`.

## Why This Shim Exists

- It preserves historical inbound links.
- It makes the cleanup boundary explicit without duplicating active guidance.
- It avoids keeping two long-form cleanup guides in sync.

If you are updating cleanup behavior, edit `cleanup-policy.md` first and keep
this page as a short compatibility redirect only.
