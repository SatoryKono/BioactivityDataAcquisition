# Docs content audit

Cycle-run: `20260827T0846Z-docs-new-b9aa36efdd`  
Method: `prompt.audit.docs-content`  
`surface_score`: **2**

## Checklist

- [x] README states project purpose
- [x] Bootstrap path confirmed against `getting-started.md` / AGENTS.md (Windows `.venv-win` restored in worktree)
- [x] Commands sampled vs `scripts/docs/__main__.py` and CI
- [x] Required env vars: documented names only; no secret values in SCOPE
- [x] Sampled relative links in edited files resolve
- [x] No P0 dangerous runbook steps found

## Findings

| ID | P | Outcome |
| --- | --- | --- |
| AUD-DOC-002 | P1 | remediated in worktree (`.venv-win`) |
| AUD-DOC-001 | P2 | remediated in worktree (dispatcher command); also tagged pipeline |

## Kit extras

`docs-inventory.csv`, `broken-links.json`, `stale-docs.csv`, `docs-code-drift.csv`
