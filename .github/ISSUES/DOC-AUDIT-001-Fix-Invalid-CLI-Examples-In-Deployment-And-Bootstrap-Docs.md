---
title: "docs(deployment): fix invalid BioETL CLI examples in deployment and bootstrap docs"
labels: documentation, enhancement
assignees: []
---

## Context

The 2026-06-19 documentation audit found published examples that do not match
the live CLI surface. The problem is not conceptual drift only; some commands
shown to operators cannot work as written on the current codebase.

## Problem

Deployment and bootstrap documentation still shows invalid or misleading
command forms:

1. `python -m bioetl run <pipeline-name>`
2. `python -m bioetl run <pipeline-name> --config <config-file>`

The active `bioetl run` CLI requires `--pipeline`, and the audited canonical
entrypoint does not publish `--config` as the supported execution surface.

## Evidence

- `docs/05-operations/deployment/README.md:66`
- `docs/05-operations/deployment/README.md:69`
- `src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py`
- `src/bioetl/interfaces/cli/commands/run.py`
- `docs/03-guides/quick-start.md`
- `docs/03-guides/getting-started.md`
- `docs/03-guides/running-pipelines.md`

## Proposed Solution

1. Replace invalid positional run examples with the supported canonical form:
   `bioetl run --pipeline <name>`.
2. Remove or rewrite any `--config <config-file>` examples unless a live,
   tested, supported CLI surface exists for that behavior.
3. Align deployment extras with the same bootstrap and run commands already
   documented as canonical in the current guides.
4. Re-scan docs for other `bioetl run <pipeline-name>` variants so the same
   drift does not remain in secondary pages.

## Acceptance Criteria

- [ ] No published docs recommend `bioetl run <pipeline-name>` as a positional form.
- [ ] No published docs recommend undocumented `--config <config-file>` for `bioetl run` unless backed by code and tests.
- [ ] Deployment/bootstrap docs use the same canonical `bioetl run --pipeline <name>` form.
- [ ] A repo search for stale command variants is clean or reduced to explicit archive-only material.

## Validation

```bash
rg -n "python -m bioetl run <pipeline-name>|bioetl run <pipeline-name>|--config <config-file>" \
  docs README.md .github/ISSUES
rg -n -- "--pipeline" src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py
```

## Non-Goals

- changing the runtime CLI behavior
- adding a new `--config` command surface
- rewriting unrelated deployment extras

