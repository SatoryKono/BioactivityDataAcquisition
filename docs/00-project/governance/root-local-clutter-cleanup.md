# Root local clutter cleanup (operator guidance)

**Status:** active  
**Linked issues:** #6703 (RH-03), epic #6700  
**Last verified:** 2026-07-27  

This note documents **local-only** cleanup for the repository root. It does not
redefine runtime behavior. Canonical policy remains
`docs/00-project/governance/03-file-policy.md` §0 and
`.github/root-allowlist.txt`.

## Safe to delete locally (untracked)

| Pattern / path | Why |
|---|---|
| `uchunk*.xml`, `final_chunk*.xml` | Accidental JUnit / pytest XML dumps |
| `pytest_*.log`, `mcp-shell.log`, `*.log` at root | Local test/agent logs (also `*.log` gitignored) |
| `tmp_sub_*.txt`, `temp_closeout.json`, `.tmp_test_run.log` | Agent scratch files |
| `.coverage`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/` | Tool caches |
| `.venv/`, `.venv-win/`, `node_modules/` | Local environments |
| `logs/`, `tmp/`, `test-output/`, `caddy/` | Local output trees (not retained git sinks) |
| `.idea/`, `.qodo/` (local), `.agents/`, `.ai/`, `.grok/`, `.windsurf/`, `.junie/` | Editor/agent local state |

## Forbidden without explicit per-task approval

| Path | Why |
|---|---|
| `.env`, `.env.local`, any real `.env*` | Secret-bearing (AGENTS.md) |
| Tracked allowlisted root files | Exact-root tool/governance contracts |
| `.codex/`, `.devin/`, curated `.vibe/`, `.zed/` when tracked | Approved agent/editor subsystems |

## Preferred commands

```bash
# Inspect root
git status --short
git ls-files | python -c "import sys; print('\n'.join(f for f in sys.stdin if '/' not in f.strip()))"

# Strict tracked-root cleanliness (local caches may still fail --strict-untracked)
uv run python -m scripts.engineering.repo check-cleanliness --strict-untracked

# CI workflow parity
# .github/workflows/root-hygiene.yml
```

## Related

- `.github/workflows/root-hygiene.yml`
- `configs/quality/root_hygiene_review_registry.yaml`
- `configs/quality/repo_structure_catalog.yaml`
