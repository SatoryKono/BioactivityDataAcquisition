______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-16'

______________________________________________________________________

# Docs Verification

Published workflow for verifying that BioETL documentation matches the current
code/config surface and still builds cleanly.

## Purpose

Use this guide when you:

- change published docs in `docs/00-05`;
- update CLI/config/runtime guidance in `README.md`;
- regenerate reference or contract material;
- want a repeatable documentation audit path before PR or release work.

## Boundaries

- **Published docs surface**: `README.md`, `mkdocs.yml`, `docs/00-05/**`
- **Repo-only supporting material**: `docs/reports/**`, `docs/plans/**`,
  `reports/**`, selected AI/runtime mirrors under `docs/00-project/ai/**`

Published docs define current supported behavior. Repo-only material may support
analysis and traceability, but it must not override the active guidance in
`docs/00-05`.

Published docs MAY cite repo-only supporting material such as `reports/**` when
it improves traceability, but those references MUST stay as repository-path
citations. If a report contains guidance that operators or contributors need to
follow, migrate that guidance into `docs/00-05` first and treat the report as
supporting evidence only.

## Prerequisites

- Preferred: `uv`
- Required for strict docs/site checks: docs extra installed

Recommended setup:

```bash
uv sync --extra dev --extra tracing --extra docs
```

If you hit cache- or wheel-related `uv` installation failures in WSL, rerun the
same sync with an explicit writable cache path:

```bash
UV_CACHE_DIR=/tmp/.uv-cache uv sync --extra dev --extra tracing --extra docs
```

Fallback without `uv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,tracing,docs]"
```

## Verification Flow

### Canonical single-command path

```bash
uv run python -m scripts.docs verify
```

Use this as the default end-to-end verification path for doc-sync changes. It
runs link/spec/config checks, docs drift, docstring inventory, documentation
cleanup inventory drift, and a strict MkDocs build through the in-repo helper
chain.

### 1. Link and reference checks

```bash
uv run python -m scripts.docs check-links --links --specs --configs
```

Use this first to catch broken internal references, spec links, and config docs
drift at the published surface.

When you need a reproducible machine-readable result for review or CI parity,
emit the stable repo-only report artifact as well:

```bash
uv run python -m scripts.docs check-links --links --specs --configs \
  --report-json docs/reports/docs-link-check-report.json
```

Failure policy:

- exit code `0` means all selected link/spec/config checks passed;
- exit code `1` means one or more selected checks reported violations and the
  docs PR should be treated as failed until they are fixed.

In CI, `.github/workflows/docs.yml` writes the same report to the transient
`reports/docs-link-check-report.json` path and uploads it as the
`docs-link-check-report` artifact. Keeping the transient artifact outside
`docs/reports/` prevents it from changing the subsequent documentation cleanup
inventory scan.

### 2. Docs drift review

```bash
uv run python -m scripts.docs check-drift --ports --classes
uv run python -m scripts.docs check-drift --runtime-mirrors --freshness
uv run python -m scripts.docs check-kpi
```

Use this when docs mention code structures or high-value runtime narratives
that are expected to stay aligned with current ports, classes, or published
operator-facing semantics.

**Ownership (DOC-GOV-09):** every new docs path SHOULD declare owner lane, type
(normative / guide / reference / runbook / mirror / archive / non-normative),
and retirement criterion. See ownership table in
[NORMATIVE_SOURCES.md](../00-project/NORMATIVE_SOURCES.md).

Current drift coverage also includes bounded narrative guards for:

- root `README.md` architecture wording that must not describe the interfaces
  layer as CLI-only while `src/bioetl/interfaces/http/` is shipped;
- `docs/03-guides/workflows.md` phrases that would present backlog wording as
  the primary framing for the shipped workflow control plane.

### 3. Documentation cleanup inventory

```bash
uv run python -m scripts.docs generate-cleanup-inventory --update
uv run python -m scripts.docs generate-cleanup-inventory --check
```

Use this when you change documentation surfaces, generated artifact routing,
or need a deterministic per-file classification matrix for cleanup work.

Outputs:

- `docs/reports/generated/documentation-cleanup-inventory.json`
- `docs/reports/generated/documentation-cleanup-inventory.md`

The inventory classifies tracked doc-like files by status, surface family,
inbound/outbound links, generated route, and recommended action. It is
repo-only evidence and does not replace publication policy in `docs/00-05`.

`python -m scripts.docs verify` includes the `--check` drift guard by default.
Skip it with `python -m scripts.docs verify --skip-cleanup-inventory` when you
only need the lighter link/drift/docstring chain.

### 4. Docstring inventory check

```bash
uv run python -m scripts.docs check-docstrings --summary
```

Use this when API/reference-facing code or generated reference expectations
changed.

### 5. Strict site build

```bash
uv run python -m scripts.docs verify --skip-links --skip-drift --skip-docstrings
```

Use the strict build after the checks above when you need confidence that the
published MkDocs surface still renders cleanly.

For a quick non-strict local preview, use
`uv run python -m scripts.docs build-site`.

## Mixed Windows + WSL Notes

If you use the same checkout from both PowerShell and WSL, keep docs/tooling
execution inside the OS-appropriate environment:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\.venv-win\Scripts\python.exe -m scripts.docs check-links --links --specs --configs
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m scripts.docs check-links --links --specs --configs
```

If `uv` cache placement causes filesystem issues in WSL, use a writable cache
location explicitly:

```bash
UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs
UV_CACHE_DIR=/tmp/.uv-cache uv sync --extra dev --extra tracing --extra docs
```

## Live Docs Watchlist

Use this short watchlist whenever a change touches runtime-facing docs or when a
doc-sync PR needs a focused code-versus-doc review.

### 1. Monitoring variables and dashboards

- **Source of truth**: `grafana/dashboards/*.json`,
  `docs/03-guides/dashboards/variables-guide.md`
- **Docs to review**: `docs/05-operations/01-monitoring-guide.md`, dashboard
  variable guides, operator runbooks that reference dashboard filters
- **Command/check**:

```bash
rg -n '\$pipeline|\$run_type|\$provider' \
  grafana/dashboards docs/03-guides/dashboards docs/05-operations/01-monitoring-guide.md
uv run python -m scripts.docs check-links --links --configs
```

### 2. Control-plane contracts

- **Source of truth**: `src/bioetl/domain/control_plane/**`,
  `src/bioetl/domain/contracts/**`, supported CLI surfaces under
  `src/bioetl/interfaces/**`
- **Docs to review**: `docs/04-reference/contracts/**`,
  `docs/04-reference/cli.md`, `docs/05-operations/runbooks/run-manifest-inspection.md`
- **Command/check**:

```bash
uv run python -m scripts.docs check-drift --ports --classes
uv run python -m scripts.docs build-site --strict
```

### 3. Provider and entity inventory

- **Source of truth**: `configs/providers/*.yaml`, `configs/entities/**`,
  `configs/composites/*.yaml`
- **Docs to review**: `README.md`, `docs/04-reference/providers/**`,
  `docs/04-reference/pipelines/README.md`
- **Command/check**:

```bash
uv run python -m scripts.docs check-links --links --specs --configs
rg -n 'configs/providers|configs/entities|configs/composites' README.md docs/04-reference
```

### 4. Storage layout

- **Source of truth**: `src/bioetl/infrastructure/config/_base.py`,
  runtime storage helpers under `src/bioetl/infrastructure/storage/**`
- **Docs to review**: `docs/03-guides/local-storage-layout.md`,
  `docs/03-guides/running-pipelines.md`, storage references in runbooks
- **Command/check**:

```bash
uv run python -m scripts.docs check-drift --classes
rg -n 'data/output|checkpoints|quarantine|control' \
  src/bioetl/infrastructure/config/_base.py docs/03-guides docs/05-operations/runbooks
```

### 5. Runbooks and operator procedures

- **Source of truth**: supported CLI/runtime behavior in `src/bioetl/interfaces/**`,
  contracts in `docs/04-reference/contracts/**`, and the active runbook index
- **Docs to review**: `docs/05-operations/runbooks/**`,
  `docs/05-operations/01-monitoring-guide.md`, `docs/04-reference/cli.md`
- **Command/check**:

```bash
uv run python -m scripts.docs check-links --links --specs --configs
uv run python -m scripts.docs build-site --strict
```

### 6. Root architecture and workflow narrative surfaces

- **Source of truth**: `src/bioetl/interfaces/**`,
  `src/bioetl/domain/workflow/**`,
  `src/bioetl/application/services/control_plane/workflow/**`
- **Docs to review**: `README.md`,
  `docs/03-guides/workflows.md`,
  `docs/04-reference/domain/workflow-state-machine.md`
- **Command/check**:

```bash
uv run python -m scripts.docs check-drift --ports --classes
rg -n 'INTERFACES \(CLI|backlog' README.md docs/03-guides/workflows.md
```

## Doc-Sync PR Checklist

Use this checklist for PRs that change published docs, runtime guidance, or
repo-only supporting material that feeds active documentation.

- [ ] Published doc changes were checked with `uv run python -m scripts.docs check-links --links --specs --configs`.
- [ ] Drift-sensitive surfaces were reviewed against the **Live Docs Watchlist** items that match the change.
- [ ] Any normative conclusion discovered in `reports/**` was migrated into `docs/00-05` before linking the report as supporting evidence.
- [ ] `uv run python -m scripts.docs check-drift --ports --classes` ran when ports, classes, contracts, or storage/runtime structure changed.
- [ ] `uv run python -m scripts.docs build-site --strict` passed before merge.

## Recurring Audit Checklist

Run this checklist for recurring documentation maintenance:

1. CLI surface vs docs
   - Top-level CLI help text
   - Published CLI reference
   - Runbook command examples
1. `make` / `uv` / bootstrap commands
   - `README.md`
   - `docs/03-guides/getting-started.md`
   - `docs/03-guides/quick-start.md`
   - `docs/00-project/RULES.md`
1. Provider/entity inventory parity
   - `configs/providers/*.yaml`
   - `configs/entities/{provider}/*.yaml`
   - `docs/04-reference/providers/**`
   - `README.md` supported-provider table
1. Contract export parity
   - `src/bioetl/domain/contracts/**`
   - `src/bioetl/domain/control_plane/**`
   - `docs/04-reference/contracts/**`
1. ADR cross-links
   - Confirm ADR-010 / ADR-014 / ADR-017 references remain accurate where runtime behavior is described
1. Published vs repo-only boundaries
   - `docs/00-05` stays normative
   - `docs/99-archive`, `docs/plans`, `docs/reports`, `reports` remain clearly non-normative

## Related Documents

- [Getting Started](getting-started.md)
- [Quick Start](quick-start.md)
- [Running Pipelines](running-pipelines.md)
- [Tools Hub](../00-project/TOOLS.md)
- [Documentation Governance](../00-project/governance/01-documentation-governance-style-guide.md)
