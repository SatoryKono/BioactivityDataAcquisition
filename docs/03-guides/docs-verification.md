---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-04'
---

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

## Prerequisites

- Preferred: `uv`
- Required for strict docs/site checks: docs extra installed

Recommended setup:

```bash
uv sync --extra dev --extra tracing --extra docs
```

Fallback without `uv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,tracing,docs]"
```

## Verification Flow

### 1. Link and reference checks

```bash
uv run python -m scripts.docs check-links --links --specs --configs
```

Use this first to catch broken internal references, spec links, and config docs
drift at the published surface.

### 2. Docs drift review

```bash
uv run python -m scripts.docs check-drift --ports --classes
```

Use this when docs mention code structures that are expected to stay aligned
with current ports, classes, or generated references.

### 3. Docstring inventory check

```bash
uv run python -m scripts.docs check-docstrings --summary
```

Use this when API/reference-facing code or generated reference expectations
changed.

### 4. Strict site build

```bash
bash scripts/docs/build_docs_site.sh --strict
```

Use the strict build after the checks above when you need confidence that the
published MkDocs surface still renders cleanly.

For a quick non-strict local preview, `make docs-build` remains acceptable.

## Mixed Windows + WSL Notes

If you use the same checkout from both PowerShell and WSL, keep docs/tooling
execution inside the OS-appropriate environment:

```powershell
.\scripts\dev\setup_env_windows.ps1
.\.venv-win\Scripts\python.exe -m scripts.docs check-links --links --specs --configs
```

```bash
bash scripts/dev/setup_env_wsl.sh
"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m scripts.docs check-links --links --specs --configs
```

If `uv` cache placement causes filesystem issues in WSL, use a writable cache
location explicitly:

```bash
UV_CACHE_DIR=/tmp/.uv-cache uv run python -m scripts.docs check-links --links --specs --configs
```

## Recurring Audit Checklist

Run this checklist for recurring documentation maintenance:

1. CLI surface vs docs
   - Top-level CLI help text
   - Published CLI reference
   - Runbook command examples
2. `make` / `uv` / bootstrap commands
   - `README.md`
   - `docs/03-guides/getting-started.md`
   - `docs/03-guides/quick-start.md`
   - `docs/00-project/RULES.md`
3. Provider/entity inventory parity
   - `configs/providers/*.yaml`
   - `configs/entities/{provider}/*.yaml`
   - `docs/04-reference/providers/**`
   - `README.md` supported-provider table
4. Contract export parity
   - `src/bioetl/domain/contracts/**`
   - `src/bioetl/domain/control_plane/**`
   - `docs/04-reference/contracts/**`
5. ADR cross-links
   - Confirm ADR-010 / ADR-014 / ADR-017 references remain accurate where runtime behavior is described
6. Published vs repo-only boundaries
   - `docs/00-05` stays normative
   - `docs/99-archive`, `docs/plans`, `docs/reports`, `reports` remain clearly non-normative

## Related Documents

- [Getting Started](getting-started.md)
- [Quick Start](quick-start.md)
- [Running Pipelines](running-pipelines.md)
- [Tools Hub](../00-project/TOOLS.md)
- [Documentation Governance](../00-project/governance/01-documentation-governance-style-guide.md)
