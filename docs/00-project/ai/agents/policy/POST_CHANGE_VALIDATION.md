# POST_CHANGE_VALIDATION.md

*Status: internal-published (AI runtime validation policy)*

## Purpose

Define the minimum validation protocol after AI-assisted changes to code,
configs, docs, contracts, prompts, diagrams, and runtime instruction surfaces.

## Canonical Sources

Verify changes against the current normative stack:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- `AGENTS.md`

## Applies To (incl. .devin/**)

- production code
- tests
- configs
- docs and diagrams
- prompts
- runtime AI files in `.codex/**` and `.junie/**` (equal-peer tracked runtime
  trees), any tracked `.gemini/**` tree that exists in the current checkout,
  `AGENTS.md`, and `.junie/guidelines.md`

## Required Protocol

1. Re-scan impacted surfaces before finalizing.
1. Use memory plus repo search to locate related tests, docs, contracts,
   configs, workflows, diagrams, reports, golden data, and mirrors.
1. Run the smallest sufficient verification set for the touched surface.
1. If runtime behavior changed, update the runtime tree first and the docs
   mirror second.
1. Record executed checks, skipped checks, and unresolved uncertainty in the
   final report.

## Minimum Surface Checks

### Runtime AI files

- verify canonical links and stale-path cleanup
- verify runtime-source-first precedence language remains aligned across
  `AGENTS.md`, `.junie/guidelines.md`, runtime maps
  (`.codex/agents/CODEX-RUNTIME.md`, `.junie/agents/JUNIE-RUNTIME.md`), and
  memory policy
- **MUST** run `bash scripts/ai/junie/check_junie_mirror.sh --check` after any
  change under `.codex/agents/**`, `.codex/skills/**`, `.junie/agents/**`, or
  `.junie/skills/**`; report exit code and, on drift, either resolve via
  `--sync` (`.codex/** → .junie/**`) or land a coupled Codex-side change in
  the same commit before submit
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`
- run the AI-surface drift check when available in `scripts.docs check-drift`

### Docs, guides, prompts, diagrams

- verify doc claim surfaces and cited runtime/code/config targets
- verify runtime/mirror consistency when AI guidance or published examples changed
- run `python -m scripts.docs check-links --links --specs --configs`
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`
- when markdown/docs changes add, remove, or retarget local links, or change
  `Owner:` / `Status:` / `Class:` headers, refresh the documentation cleanup
  inventory in the **same changeset**:
  - `python -m scripts.docs generate-cleanup-inventory --update`
  - verify: `python -m scripts.docs generate-cleanup-inventory --check`
  - artifacts: `docs/reports/generated/documentation-cleanup-inventory.json`
    and `docs/reports/generated/documentation-cleanup-inventory.md`
  - `--check` rebuilds from the working tree, not `HEAD`. A docs-cycle that
    edits links or headers without `--update` fails
    `tests/architecture/test_documentation_cleanup_inventory.py::test_documentation_cleanup_inventory_check_passes`
    and stops `architecture-fast` at the first failure
  - `--check` prints field-level diffs (`inbound_links`, `outbound_links`,
    `declared_status`, generated-only rows). Do not treat a bare JSON-path
    mismatch as a flake

### Code and tests

- locate impacted tests before deciding validation scope
- include golden, architecture, contract, and regression tests when the touched
  surface can affect them
- run targeted unit/integration/architecture tests appropriate to the change
- when any file under `src/bioetl/**/*.py` is added, removed, renamed, or
  content-changed, refresh the committed module-coverage inventory digest before
  closeout:
  - artifact: `reports/quality/module-coverage-inventory.json`
  - field: `source_tree_sha256` (SHA-256 over all `src/bioetl/**/*.py` paths and
    contents)
  - hash-only refresh (no new `coverage.xml` required):
    `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml`
  - full inventory regen (coverage rows changed): run the `coverage-verify`
    generator from `scripts/engineering/qa/report_module_coverage_inventory.py`
    against `reports/coverage/coverage.xml`
  - verify:
    `pytest tests/architecture/test_module_coverage_inventory_freshness.py`
  - on cloud-synced checkouts (for example Google Drive), wait for sync to finish
    before computing or verifying the hash to avoid transient drift

### Configs and contracts

- locate related config validators, contract tests, and docs references
- run the narrowest relevant config/contract validation commands
- when any file under `grafana/dashboards/**` changes, MUST run
  `pytest tests/integration/test_dashboard_operator_readability.py`
  (inline copy roles, operator clock `YYYY-MM-DD HH:MM`, first-window
  no-scroll). Do not treat dashboard JSON edits as done without this gate.

### MCP runtime settings and local-only surfaces

- validate JSON/TOML syntax of changed runtime config files
- confirm local-only classification and portability notes stay accurate
- do not silently rewrite machine-specific paths without an explicit strategy

## Final Report Requirements

The closeout MUST include:

1. changed files or change areas
1. related tests, golden tests, architecture tests, contract tests, docs, ADRs,
   diagrams, configs, and reports found through memory plus repo search
1. checks run
1. command outcomes
1. skipped checks with reason and the exact command to run later
1. mirror-sync status when AI runtime files or docs mirrors changed,
   including `scripts/ai/junie/check_junie_mirror.sh --check` exit code for
   any touched `.codex/agents/**`, `.codex/skills/**`, `.junie/agents/**`, or
   `.junie/skills/**`
1. explicit callout if any stale guidance remains for follow-up

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
