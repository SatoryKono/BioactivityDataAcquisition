# Preflight — step 01

- Card: `prompt.audit.cycle.docs` v1.0.0.
- Base: `origin/main` at `dd076a79f53f708081acb0cc27868bb2d9f08cf7`.
- Branch: `fix/audit-seq-dd076a79f5`.
- Scope: `README.md`, `docs/`, `mkdocs.yml`, `scripts/docs/`, docs CI jobs.
- Source checkout contained foreign staged work; this run uses the isolated
  worktree `/tmp/bioetl-audit-seq-dd076a79f5`.
- Prompt source SHA-256:
  `3eeb6329f8f244c2132b722d8b144caf53a8b0433efe86e7626c8093733afd31`.
- `MONITORING=false`; monitoring was not started.
- Memory pre-task: degraded because rebuild-only RAG chunks and timeline events
  were absent; repository sources remain authoritative.
- `gh auth status`: stored CLI credential is invalid. GitHub deduplication and
  tracking must use the connected GitHub API unless CLI authentication is
  restored without changing `.env`.
