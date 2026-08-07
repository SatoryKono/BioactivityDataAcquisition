# Root local clutter cleanup (operator guidance)

**Status:** active
**Linked issues:** #6703 (RH), #6766 (RH2-01), #6798/#6799 (RH3), #6813/#6814/#6816 (RH4), #6876/#6877 (RH 2026-07-28), #7015–#7023 (RH5 2026-07-29); RH7 #8292–#8295, #8299–#8300, #8306–#8307; epics #6700, #6765, #6795, #6812, #6874, #7015
**Last verified:** 2026-08-07

This note documents **local-only** cleanup for the repository root. It does not
redefine runtime behavior. Canonical policy remains
`docs/00-project/governance/03-file-policy.md` §0 and
`.github/root-allowlist.txt`.

Tracked root is allowlist-minimal (**37 ≡ allowlist** after RH-01 / #6876;
re-verified RH5 / #7016). Most live root noise is **recreated by normal tooling**
(coverage, logs, test dumps). Use the recurring checklist below instead of
inventing new allowlist entries.

### Local vs CI (RH-02 / #6877)

| Surface | Local developer host | CI `root-hygiene` job |
|---------|----------------------|------------------------|
| Tracked root ≡ allowlist | Must hold | Must hold |
| Untracked caches (`.coverage`, `.pytest_cache/`, …) | Common; purge before strict runs | Clean checkout — usually absent |
| Secret `.env*` | May exist machine-local; **never** commit | Must stay untracked / absent |
| `check-cleanliness --strict-untracked` | Can fail on local scratch until purged | Expected green on clean runner |
| `--check-local-forbidden-outputs` | Documents forbidden patterns | Enforced on CI clean tree |

**Never** follow any guide that says to commit `.env`, `.env.local`, or real
`.env*` files. Only `.env.example` is the tracked template.

## Recurring 5-minute checklist (pre-PR / pre-audit)

1. **Never** create, edit, delete, rename, or move `.env` / `.env.local` / real
   `.env*` without **explicit per-task user approval**.
2. Confirm tracked root still matches allowlist (expect **37** files):
   ```bash
   git ls-files | python -c "import sys; xs=sorted(f.strip() for f in sys.stdin if f.strip() and '/' not in f.strip()); print(len(xs)); print('\\n'.join(xs))"
   ```
3. Safe local purge (untracked only), when present:
   - `.coverage`, root `logs/`, `tmp/`, `test-output/`, `caddy/`, `.tmp_fix/`
   - `_tmp_*.py`, `/_cr_*.py`, `/_publish_*.py`, `_fail_*.txt`, `_a.txt`
   - `temp_closeout.json`, `.tmp_*`, `.tmp_test_run.log`, `mcp-shell.log`
   - `bash.exe.stackdump`, `nul` / `NUL` (Windows pseudo-file)
   - empty exact-root `.worktrees/` (strict-untracked rejects it; non-empty trees hold active worktrees — do not recursive-delete)
   - `arch_fail_report.txt` / other root `*report*.txt`
   - `.gitignore~`
4. Preferred reviewed tooling (exact root only; never secret `.env*`):
   ```bash
   # Safe reviewed paths (logs need --include-logs)
   python -m scripts.engineering.repo.cleanup_root_local_clutter --include-logs --apply
   # Empty .worktrees only (refuses non-empty)
   python -m scripts.engineering.repo.cleanup_root_local_clutter --apply --path .worktrees
   # Windows nul when listed in the root directory (uses listing + \\?\ helper)
   python -m scripts.engineering.repo.cleanup_root_local_clutter --apply --path nul
   ```
5. Optional / expensive: tool caches and venvs
   (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/`,
   `.venv*`, `node_modules/`) — purge only if you accept rebuild cost.
6. Leave allowlisted tracked files and curated agent trees
   (`.codex/`, tracked `.devin`/`.vibe`/`.zed`) alone.
7. Re-check:
   ```bash
   uv run python -m scripts.engineering.repo check-cleanliness --strict-untracked
   ```

Long-lived retained logs belong under `reports/logs/`, not root `logs/`.

## Agent / scratch placement (RH4-03 / RH5-04)

**Do not** create agent or closeout scratch Python at the exact repository root:

| Banned root pattern | Notes |
| --- | --- |
| `_tmp_*.py` | gitignored; still fails `--strict-untracked` |
| `/_cr_*.py` | e.g. CodeRabbit one-offs; gitignored (RH5) |
| `/_publish_*.py` | one-off issue publishers; rehome under `scripts/**` if needed |
| ad-hoc `temp_*.py`, `test_*.py` at root | never allowlist |

Preferred placement for disposable scripts and dumps:

- under `scripts/engineering/repo/**` or `scripts/ops/**` when reusable, or
- under `reports/` (generated/local; many paths already gitignored), or
- under an existing ignored tool cache tree, or
- OS temp **outside** the repository

Root scratch files remain **safe to delete** and **must not be recreated**.
Do not weaken `--strict-untracked` to allow root scratch Python. Do not expand
the root allowlist for temps.

## Ops writers that must not re-clutter root logs/ (RH4-02)

- `scripts/ops/runtime/docker/watchdog-docker-stable.ps1` defaults state/logs to
  `reports/logs/docker-watchdog/` (not root `logs/`). Override with `-StateDir`
  if a host already pinned another path.

## Safe to delete locally (untracked)

The following untracked patterns are **safe to delete** on a developer host
when no active process depends on them:

| Pattern / path | Why |
|---|---|
| `uchunk*.xml`, `final_chunk*.xml` | Accidental JUnit / pytest XML dumps |
| `pytest_*.log`, `mcp-shell.log`, `*.log` at root | Local test/agent logs (also `*.log` gitignored) |
| `tmp_sub_*.txt`, `temp_closeout.json`, `.tmp_*`, `_tmp_*.py`, `/_cr_*.py`, `/_publish_*.py`, `_fail_*.txt`, `_a.txt` | Agent / accidental scratch files |
| `bash.exe.stackdump` | MSYS/Cygwin crash dump |
| `arch_fail_report.txt`, `*report*.txt` at root | Local architecture/test report dumps |
| `.gitignore~` | Editor backup; `.gitignore` is the tracked source of truth |
| `.coverage`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/` | Tool caches |
| `.venv/`, `.venv-win/`, `node_modules/` | Local environments (optional purge) |
| `logs/`, `tmp/`, `test-output/`, `caddy/`, `.tmp_fix/` | Local output trees (not retained git sinks) |
| root `~/` | Accidental tool home-mirror directory (not user `$HOME`) |
| `.idea/`, `.qodo/` (local), `.ai/`, `.grok/`, `.windsurf/` | Editor/agent local state |
| non-SKILL.md content under `.agents/` | Local agent workspace noise; curated `SKILL.md` adapters remain tracked |
| `nul` / `NUL` | Windows reserved-name pseudo-file; ignored. Presence must be detected via directory listing (not `Path.exists()` / bare `is_file()`). Reviewed cleanup supports `nul`/`NUL` with a `\\?\` extended-path helper; Git Bash `rm -f ./nul` remains a fallback when Win32 denies unlink. |

## Retain while in use; safe to regenerate

| Path | Guidance |
|---|---|
| `.mcp-server-context.md` | Machine-local generated MCP context. Keep while an active MCP client uses it; delete only when no client depends on the current context. It is ignored and may be regenerated by MCP tooling; it MUST NOT be promoted to a tracked source of truth. |

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

## RH3-01 local purge (2026-07-28)

Deleted on the audit host when present (untracked only):

- `.coverage`
- `logs/`, `test-output/`

Left in place:

- `.env`, `.env.local` (secret lane)
- `.mcp-server-context.md` (regenerable MCP context still in use)
- Windows `nul` (Access denied on unlink; already gitignored)

## RH4-01 local purge (2026-07-28)

Deleted on the audit host when present (untracked only):

- `_tmp_check_helper_ratio.py`, `_tmp_issue_6787_closeout.py`
- root `logs/` (including recreated `logs/docker-watchdog/`)

Left in place:

- `.env`, `.env.local` (secret lane)
- `.mcp-server-context.md` (regenerable MCP context still in use)
- Windows `nul` (Access denied on unlink; already gitignored)

Watchdog default relocated under `reports/logs/docker-watchdog/` (RH4-02 / #6816)
so future runs do not recreate root `logs/` by default.

## RH-01 tracked scratch closeout (2026-07-28)

- Removed unexpected tracked root file `_a.txt` (not on allowlist).
- Gitignore now blocks reintroduction of `_a.txt`.
- Tracked root restored to **37 ≡ allowlist**.

## RH-05 retention decisions (2026-07-28 / #6878)

| Root file | Decision | Consumer evidence |
|-----------|----------|-------------------|
| `.secrets.baseline` | **retain** | `tests/architecture/test_antipatterns.py::test_no_hardcoded_secrets` (detect-secrets baseline); pre-commit hook `detect-secrets-baseline`; `tests/architecture/conftest.py` inventory |
| `.aiignore` | **retain** | Exact-root AI-client ignore surface (Cursor/compatible tooling); no hard Python importer; keep while allowlist lists it — do not grow scope; drop only with allowlist+policy+registry sync |

## RH7 residual closeout (2026-08-07)

Campaign branch: `grok-260807-root-hygiene-5cycle` (5 full Stage1–3 cycles).

| Cycle | Issues | What landed |
|---|---|---|
| C1 | #8292, #8293 | Purged recreated `mcp-shell.log`; removed empty `.worktrees/` |
| C2 | #8294, #8295 | Purged `logs/`, `test-output/`, `.coverage`; cleanup SAFE + listing-based `nul` support |
| C3 | #8299, #8300 | Audit forbidden temps without requiring `is_file()`; empty-only `.worktrees` cleanup + registry candidate |
| C4 | #8306, #8307 | This docs refresh; optional tool-cache purge on audit host |

**Strict gate after RH7 C1–C3:** `check-cleanliness --strict-untracked` OK; tracked root **37 ≡ allowlist**.

**Tooling notes (RH7):**

- `Path('nul').exists()` is true on Win32 for the NUL device even when no root file is listed — cleanup/audit use **directory listing** membership.
- Empty `.worktrees/` fails strict-untracked; cleanup deletes **only when empty** and refuses non-empty trees so exclusive worktrees are not destroyed.
- Retain `.gitignore` rules for `*.log`, `nul`, and `.worktrees/`; do not expand the root allowlist for temps.

## Related

- `.github/workflows/root-hygiene.yml`
- `configs/quality/root_hygiene_review_registry.yaml`
- `configs/quality/repo_structure_catalog.yaml`
- Epic RH3: #6795
- Epic RH4: #6812
- Epic RH (2026-07-28): #6874
- RH7 issues: #8292–#8295, #8299–#8300, #8306–#8307
- Pack: `.github/ISSUES/RH-2026-07-28-ROOT-HYGIENE-MINIMIZATION-ISSUE-PACK.md`
- Pack RH4: `.github/ISSUES/RH4-2026-07-28-ROOT-HYGIENE-POST-RH3-RESIDUAL-ISSUE-PACK.md`
