---
trigger: model_decision
description: "Documentation standards and governance sync"
---

# Documentation Standards

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

- Active source of truth is `docs/00-05`; `docs/99-archive` is historical only.
- Align wording with RFC 2119 where requirements are normative.
- Reflect code-level contract changes in docs and add migration guidance for breakings.
- Keep ADR and cross-links consistent when architecture decisions are affected.
- For schema/column/CLI changes, update docs and `CHANGELOG.md`.
- Avoid ambiguous guidance; prefer explicit, testable statements.
