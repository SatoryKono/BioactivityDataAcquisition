---
name: documentation-audit
description: Full audit and update of BioETL project documentation for v5.14+. Use when asked to review docs for staleness, reconcile docs with code, sync RULES.md and REQUIREMENTS.md, update architecture/provider/contract docs, reflect ADR-010/ADR-014/ADR-017, or identify dead documentation.
---

# Documentation Audit

## Overview
Perform a full documentation audit of BioETL and bring docs in sync with code and ADRs (v5.14+). Produce a clear audit report, a prioritized plan, and updated documentation changes.

## Workflow (default)
1. Intake and scope
- Confirm repo root and target version (v5.14+).
- Identify doc entry points (for example: README.md, mkdocs.yml).
- Load `references/audit-checklist.md` and `references/report-template.md`.

2. Audit
- Compare documentation to current code and configs.
- Focus on RULES.md, REQUIREMENTS.md, architecture docs, provider docs, and contract docs.
- Check alignment with ADR-010 Local-Only, ADR-014 Determinism, ADR-017 Observability.
- Record findings with severity (Critical, High, Medium, Low).

3. Plan
- Turn findings into a concrete change list.
- Prioritize by impact (Critical > High > Medium > Low).
- Call out unknowns that need user confirmation.

4. Update
- Edit docs to match current code and ADRs.
- Keep versions and dates explicit in text.
- For obsolete or unreferenced docs, propose delete/archive unless the user explicitly asks to remove.

5. Verify
- Check links between docs and nav entries.
- Ensure RULES.md and REQUIREMENTS.md are synchronized.
- Confirm ADRs are reflected in top-level docs and architecture sections.

## Practical checks and commands
- Find ADR references: `rg -n "ADR-010|ADR-014|ADR-017" docs README.md mkdocs.yml`
- Find version mentions: `rg -n "v5\.14|5\.14" docs README.md`
- Find doc references in nav: `rg -n "docs/|\.md" mkdocs.yml README.md`
- Scan for orphan docs: list files in `docs/` then search for each filename in `mkdocs.yml` and other docs.

## Outputs
- Use `references/report-template.md` for the audit report.
- Provide a short prioritized change list and note any required user decisions.

## Notes
- Prefer documenting reality over desired behavior; if code and docs diverge, flag it and propose options.
- Avoid code changes unless the user explicitly asks; this skill focuses on documentation.
