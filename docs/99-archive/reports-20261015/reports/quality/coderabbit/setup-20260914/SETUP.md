# CodeRabbit setup validation — 2026-09-14

Result: local launcher configured and regression-tested; live service validation BLOCKED_NETWORK.

Changed sources:
- `.coderabbit.yaml`: ru-RU review language.
- `scripts/ops/run-coderabbit-reviews.sh`: root dotenv key loading without sourcing or editing, preflight-only mode, one-review changes topic, directory/uncommitted scope, NDJSON and source snapshot logs, failure propagation and completion validation.
- `tests/unit/scripts/ops/test_run_coderabbit_reviews.py`: failure and argument regression coverage.
- `docs/03-guides/development/coderabbit-local-reviews.md`: current Windows/WSL operator commands and limits.

Checks:
- Bash syntax: PASS.
- Ruff check and format check of the changed test: PASS.
- YAML parse: PASS; language ru-RU. Official remote schema validation: NOT_VERIFIED, fetch timed out.
- Regression tests: 20 PASS. Exact final script and test were copied to an isolated WSL /tmp tree and run with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONDONTWRITEBYTECODE=1, pytest --noconftest and a minimal pytest.ini. Initial repository-local runs were blocked by a plugin calling git describe and by pytest traversing Windows system files; those attempts are not passing evidence.
- `python -m scripts.docs check-links --links --specs --configs`: PASS.
- `python -m scripts.docs check-drift --runtime-mirrors --freshness`: PASS, zero errors/warnings at check time.
- `git diff --check` for four changed sources: PASS.
- Real final preflight: FAIL at API key validation because the CodeRabbit server could not be reached; see auth.log. Key validity remains unknown.

Network evidence:
- CLI 0.7.5 installed in Ubuntu; cached browser authentication previously reported authenticated.
- `coderabbit doctor`: 7 pass, backend and WebSocket connectivity fail.
- WSL DNS queries time out. HTTPS with a Windows-resolved address also times out.
- Windows HTTPS request to app.coderabbit.ai failed with a TLS handshake error.
- No changes made to .env, system DNS, proxies, workflow activation, or secrets.

Remaining checks after connectivity is restored:
- `wsl -d Ubuntu --cd /mnt/e/github/BioactivityDataAcquisition --exec bash scripts/ops/run-coderabbit-reviews.sh --preflight`
- `wsl -d Ubuntu --cd /mnt/e/github/BioactivityDataAcquisition --exec bash scripts/ops/run-coderabbit-reviews.sh changes --uncommitted`

Scope and governance:
- CLI reviews Git diffs. No completed CodeRabbit audit, no full-project coverage claim.
- Legacy comprehensive launcher and CI workflow are not migrated/enabled by this local setup; current runbook records their limitations.
- Runtime source trees unchanged; Codex–Junie mirror sync not applicable.
- No new/retargeted Markdown links or ownership/status/class headers; cleanup inventory regeneration not applicable.
- No src/bioetl code changed by this task; module-coverage refresh not applicable.
- Debt budgets unchanged; full architecture/debt suite not run for this launcher change.
- Memory pre-task: read-only, degraded due to missing RAG/timeline artifacts. Post-task persistence skipped in read-only mode.
- Proof-or-Stop plan/assemble/verify executed. Outcome STOP: no normalized tests/governance/docs_runtime/debt receipts were supplied; local test output does not substitute for those receipts. No merge/release readiness claim.
- Concurrent unrelated project edits continued throughout; no commits or cleanup performed.

Source SHA-256:
- scripts/ops/run-coderabbit-reviews.sh: 3867196883595fd170db41c684e5c90553927f900085a76d889b8d2fa09c7059
- tests/unit/scripts/ops/test_run_coderabbit_reviews.py: a19b7ae6ff1aa834a6b9f0e36c0055a08bb2411af7d658b81519d9dbd598c4f1

CLI reference: https://docs.coderabbit.ai/cli/reference
