# Docs content audit — `docs-content`

| Field | Value |
| --- | --- |
| domain_id | `docs-content` |
| prompt_id | `prompt.audit.docs-content` |
| MODE | full / AUDIT_MODE=full |
| LANGUAGE | ru |
| SCOPE | README.md, docs/ |
| BASE | main `b48ac65c98` |
| Date | 2026-08-21 |
| surface_score | **2** |
| Score mapping | Domain card 0-3 control maturity |
| gate | WARN |
| issues | #9284 #9286 #9285 #9283 |

## Executive summary

Onboarding describes a reproducible local-only bootstrap: Python 3.12 baseline,
`uv sync --extra dev --extra tests --extra tracing`, mixed Windows `.venv-win` /
WSL split, 22 entity YAMLs, version `6.1.0`. `check-links` PASS.

PROVEN in-scope drift was in operator recovery and env SSOT:

- P1 #9284 / DOCS-001: P0 runbook `--resume-from` (fixed this run)
- P1 #9286 / DOCS-002: Spark `RESTORE TABLE` (fixed this run)
- P2 #9285 / DOCS-003: env reference invented ChEMBL key (fixed this run)
- P2 #9283 / DOCS-004: `.github/SECURITY.md` phantom keys (out of SCOPE)

Prior inventory drift #9265 is already on origin/main.

## Checklist

- [x] README states project purpose
- [x] Bootstrap path confirmed
- [x] Commands match manifests/CI for sampled resume/rebuild
- [x] Required env vars documented (names only; no secret values)
- [x] Links resolve
- [x] No P0 secret leak
