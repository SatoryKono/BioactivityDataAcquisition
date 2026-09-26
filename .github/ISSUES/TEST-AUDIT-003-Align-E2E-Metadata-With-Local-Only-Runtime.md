---
title: "[TEST-AUDIT] Align E2E metadata with Local-Only runtime and maintenance carve-outs"
github_issue: 5426
labels: enhancement, documentation, technical-debt
assignees: []
---

## Context

The E2E suite is explicitly Local-Only, but the pytest marker metadata still
describes E2E as "requires Docker". The same E2E harness also intentionally
disables Bronze cleanup and postrun Silver compaction to preserve deterministic
end-to-end assertions.

## Problem

- `pyproject.toml` still advertises outdated Docker expectations for E2E.
- The maintenance carve-out is implemented in code but not reflected cleanly in
  the public test-surface metadata.
- This creates onboarding and automation drift.

## Evidence

- `pyproject.toml`
- `tests/e2e/conftest.py`
- `docs/03-guides/getting-started.md`

## Proposed Solution

1. Update the `e2e` marker description to match Local-Only reality.
2. Document that E2E intentionally excludes cleanup/compaction fidelity.
3. Cross-link the carve-out to the dedicated maintenance-path test strategy.

## Acceptance Criteria

- [ ] `e2e` marker metadata no longer claims Docker is required
- [ ] E2E docs explicitly call out cleanup/compaction carve-outs
- [ ] Local-only guidance is consistent across marker metadata, E2E conftest,
      and contributor docs

## Validation

```bash
./.venv/bin/python -m pytest --markers
rg -n "requires Docker|Local-Only|compaction|cleanup_old_files" \
  pyproject.toml tests/e2e/conftest.py docs/03-guides/getting-started.md
```

## Risks

- Narrow wording updates can still drift if the carve-out is not described in
  one canonical place.
