# Test lane mental model (agents & contributors)

**Source of truth:** `configs/quality/test_matrix.yaml` (ADR-042)  
**Linked issues:** #6890, #6900 (TB-10)

## Default local commands

| Intent | Command | Notes |
|--------|---------|-------|
| Fast product unit feedback | `pytest tests/unit -m "not repo_backed and not subprocess_backed and not slow and not benchmark and not memory" --ignore=tests/unit/scripts --ignore=tests/unit/repo_backed` | Canonical **unit-fast** |
| Architecture boundary feedback | `pytest tests/architecture -m "architecture and not slow and not benchmark and not memory"` | Canonical **architecture-fast-boundary** |
| Full architecture governance | `pytest tests/architecture` (or CI slow-governance lane) | Heavy; avoid as first local default |
| Repo-backed unit | `pytest tests/unit/repo_backed -m "repo_backed and not slow"` | Reads repo files |
| Scripts tooling | `pytest tests/unit/scripts` | **Not** pure hexagonal unit |

Local pytest defaults remain **serial** (`forbid_global_xdist_addopts`). CI enables xdist only on maintained parallel lanes.

## Mental model

1. **Domain unit** (`tests/unit/domain/**`): pure domain, no network, no durable I/O.
2. **Application / composition unit**: may use fakes; bootstrap may use **session-scoped immutable catalogs** only (`tests/helpers/bootstrap_cache.py`).
3. **FS-heavy “unit”** (`tmp_path` / `write_text`): prefer `repo_backed` or integration when behavior is filesystem/config-path contract, not domain logic (#6893).
4. **Architecture tests**: boundary/determinism fast suite first; tech-debt residual non-growth is centralized in `reports/quality/live-residual-snapshot.json` + `tests/architecture/test_live_residual_snapshot.py` (#6891).
5. **Scripts tooling tests**: separate lane; do not mix into unit-fast interpretation.

## Do not

- Run full `tests/architecture` as the only feedback loop for code edits.
- Treat `tests/unit/scripts` failures as domain architecture regressions.
- Raise tech-debt budgets to silence freezes; residual is shrink-only.
- Use retries to hide nondeterminism (uuid4 / wall clock / random).

## Related artifacts

- `configs/quality/test_matrix.yaml`
- `reports/quality/test-governance-current.json`
- `reports/quality/live-residual-snapshot.json`
- `reports/quality/test-bootstrap-fixture-scope-profile.json`
