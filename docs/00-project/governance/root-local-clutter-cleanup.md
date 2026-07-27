# Root local clutter cleanup (operator guidance)

**Status:** active
**Linked issues:** #6703 (RH-03), #6717 (CR-01), epic #6700 / #6716
**Last verified:** 2026-07-27

This note documents **local-only** cleanup for the repository root. It does not
redefine runtime behavior. Canonical policy remains
`docs/00-project/governance/03-file-policy.md` §0 and
`.github/root-allowlist.txt`.

Also see `configs/quality/repo_structure_catalog.yaml` (`local_tolerated_root_dirs`)
for machine-readable tolerated local roots.

## 1. Safe ephemeral outputs (untracked)

These are rebuildable or disposable **generated** surfaces. Safe to delete when
untracked:

| Pattern / path | Why |
|---|---|
| `uchunk*.xml`, `final_chunk*.xml`, `extra_chunk*.xml` | Accidental JUnit / pytest XML dumps |
| `pytest_*.log`, `mcp-shell.log`, `*.log` at root | Local test/agent logs (also `*.log` gitignored) |
| `tmp_sub_*.txt`, `temp_closeout.json`, `.tmp_test_run.log` | Agent scratch files |
| `.coverage`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/` | Tool caches |
| `.venv/`, `.venv-win/`, `node_modules/` | Local environments |
| `logs/`, `tmp/`, `test-output/`, `caddy/` | Local output trees (not retained git sinks) |

## 2. Local tooling / editor roots (delete only if rebuildable)

These may hold **machine-local configuration** that is not always trivial to
rebuild. Delete only after confirming the contents are disposable or can be
regenerated (for example from `scripts/ai/codex/setup_mcp.py` or IDE import):

| Pattern / path | Why |
|---|---|
| `.idea/` | PyCharm local project state (portable templates under `configs/ide/pycharm/`) |
| `.qodo/` (local, untracked) | Local Qodo Desktop MCP/runtime state — not repo policy source |
| `.agents/`, `.ai/`, `.grok/`, `.windsurf/`, `.junie/` | Local agent/editor runtime state (untracked by policy) |
| `.cursor/`, `.vscode/`, `.gemini/` when **untracked** | Local editor mirrors; do not delete curated **tracked** shared metadata |

If unsure, leave the directory alone and only remove files you created.

## 3. Forbidden without explicit per-task approval

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
- `docs/00-project/governance/03-file-policy.md` §0
