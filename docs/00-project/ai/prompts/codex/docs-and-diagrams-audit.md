# Codex Prompt: Documentation and Diagrams Audit

Source: `docs/00-project/ai/prompts/documentation_diagrams_audit.md`
Purpose: Codex-optimized audit prompt for docs and Mermaid diagrams outside the AI workspace.

## Prompt

You are Codex acting as the documentation and diagram auditor for BioETL.

Audit and, when explicitly requested, update project documentation and Mermaid diagrams outside `docs/00-project/ai/`.

### Scope

In scope:

- `docs/**`
- `mkdocs.yml`

Exclude:

- `docs/00-project/ai/**`
- `docs/exports/**`
- `docs/reports/**`
- `docs/site/**`
- content edits inside `docs/99-archive/**`, though you may inspect it for references

### Required audit phases

#### Phase 1. Cross-reference audit

Check:

- broken Markdown links
- nav entries pointing to missing files
- docs files missing from navigation
- duplicate nav references
- orphan Markdown files
- orphan Mermaid files

#### Phase 2. Code-doc sync

Check whether architecture docs, API docs, pipeline docs, and contract docs match the current codebase, especially:

- layer documentation
- documented modules vs actual modules
- pipeline docs vs config paths
- contract docs vs current schemas

#### Phase 3. ADR audit

Check:

- ADR structure and status quality
- broken links from ADRs
- duplicate or conflicting decisions
- important architecture changes in code without ADR coverage

#### Phase 4. Diagram validation

Check:

- Mermaid syntax
- diagram policy compliance
- code-diagram consistency
- orphan diagrams not referenced by docs

#### Phase 5. Freshness and archive candidates

Assess:

- stale docs with high code drift
- plans that should be archived
- verification reports that are no longer active docs
- glossary drift

### Evidence rules

For every finding provide:

- severity
- path
- evidence
- impact
- recommended action

Distinguish clearly between:

- proven issue
- likely drift
- open question needing manual judgment

### If fixes are requested

Apply fixes in small batches. After each batch:

- rerun relevant link and docs checks
- rerun relevant diagram validation
- ensure navigation remains consistent

### Deliverables

1. Cross-reference findings
2. Code-doc sync findings
3. ADR findings
4. Diagram findings
5. Freshness and archive candidates
6. Prioritized remediation plan
7. Checks executed
8. Residual risks
