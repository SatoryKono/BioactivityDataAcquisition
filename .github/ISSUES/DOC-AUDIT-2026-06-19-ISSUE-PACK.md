# Documentation Audit 2026-06-19 Issue Pack

This pack converts the validated 2026-06-19 documentation audit into a
publish-ready GitHub issue set.

## Scope

The pack covers only findings re-verified against the current repository state:

- invalid CLI examples in deployment/bootstrap docs
- stale Grafana provisioning paths in active observability/dashboard docs
- stale Windows mixed-checkout pytest examples
- architecture/ADR drift in control-plane and observability decision docs
- stale current-state inventory fields and missing domain control-plane
  reference coverage

## Issue Set

1. `DOC-AUDIT-001` — fix invalid BioETL CLI examples in deployment and bootstrap docs — [#5438](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5438)
2. `DOC-AUDIT-002` — refresh Grafana provisioning path docs to the current split datasource layout — [#5439](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5439)
3. `DOC-AUDIT-003` — align mixed Windows + WSL pytest examples with the current xdist worker cap — [#5440](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5440)
4. `DOC-AUDIT-004` — repair control-plane ADR cross-links and ADR-022 observability guidance — [#5441](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5441)
5. `DOC-AUDIT-005` — refresh current-state inventory and publish a dedicated domain control-plane reference page — [#5442](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5442)

## Recommended Execution Order

### Phase 1: operator-facing correctness

1. `DOC-AUDIT-001`
2. `DOC-AUDIT-002`
3. `DOC-AUDIT-003`

### Phase 2: architecture/reference cleanup

4. `DOC-AUDIT-004`
5. `DOC-AUDIT-005`

## Notes

- This pack intentionally does **not** propose runtime refactoring.
- The issues are documentation-governance workstreams derived from
  [review_documentation-cascade-audit_20260619_1230.md](../../reports/codex/review_documentation-cascade-audit_20260619_1230.md).
- The split keeps immediate operator-facing breakage separate from slower
  architecture/reference cleanup.

## Closure Evidence

- `#5438` resolved in `docs/05-operations/deployment/README.md`, `README.md`,
  `docs/03-guides/getting-started.md`, and `docs/03-guides/quick-start.md` by
  replacing invalid positional `bioetl run` examples with the supported
  `--pipeline` form.
- `#5439` resolved in `docs/03-guides/dashboard-guide.md`,
  `docs/02-architecture/current-state-inventory.md`, `grafana/README.md`, and
  `docs/plans/monitoring-observability-expansion-plan-2026-03-26.md` by
  documenting `datasources-core/` and `datasources-tracing/` plus
  `bioetl.yaml`.
- `#5440` resolved in `README.md`, `docs/03-guides/getting-started.md`,
  `docs/03-guides/quick-start.md`, `docs/03-guides/testing.md`,
  `docs/03-guides/github-local-workflow.md`, `docs/00-project/index.md`,
  `docs/ru/00-project/index.md`, `docs/00-project/ai/memory/agent-memory.md`,
  `docs/00-project/ai/agents/guides/CLAUDE.md`, and
  `docs/00-project/ai/agents/guides/AGENT.md` by aligning Windows examples to
  `-n 1` and WSL examples to `-n auto`, with the
  `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS` override documented.
- `#5441` resolved in `docs/02-architecture/domain-control-plane.md`,
  `docs/02-architecture/decisions/ADR-022-tracing-noop.md`,
  `docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd`, and
  `docs/02-architecture/diagrams/views/30-port-adapter-mapping-full.mermaid`
  by fixing ADR mappings, noop package paths, and `run_id` observability
  wording.
- `#5442` resolved in `docs/02-architecture/current-state-inventory.md`,
  `docs/04-reference/domain/README.md`, `docs/04-reference/domain/control-plane.md`,
  and `mkdocs.yml` by refreshing generated/current counts and adding a dedicated
  domain control-plane reference page.

## Verification

```bash
python3 -m scripts.docs check-links --links --specs --configs
python3 -m scripts.docs check-drift --runtime-mirrors --freshness
/home/fedor/.venvs/bioetl/bin/python -m pytest -q \
  tests/integration/test_grafana_datasource_provisioning.py \
  tests/architecture/test_documentation_sync.py \
  tests/architecture/test_control_plane_runtime_docs_alignment.py \
  tests/architecture/test_check_doc_links_guardrails.py \
  --no-cov
```
