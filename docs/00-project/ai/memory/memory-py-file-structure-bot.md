# Memory: py-file-structure-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.0 | Date: 2026-05-28 | Parent: agent-memory.md*

> **Focus**: canonical file layout rules, zone ownership, directory depth limits,
> naming conventions for files and directories, orphan/stale detection heuristics.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: file structure auditor and optimizer
- **Write zone**: `reports/` (audit artifacts only)
- **Read zone**: entire repository tree
- **Output artifacts**: `reports/{LLM}/review_py-file-structure-bot_*.md`
- **Finding prefix**: `FS-`

## 2. Canonical Layout

### Top-level repo zones (7 primary)

| Zone | Path | Contents |
| --- | --- | --- |
| Source | `src/bioetl/` | Runtime Python code, 5 architectural layers |
| Configs | `configs/` | `entities/`, `composites/`, `quality/` YAML configs |
| Tests | `tests/` | `unit/`, `integration/`, `architecture/`, `e2e/` |
| Scripts | `scripts/` | `engineering/`, `ops/`, `schema/`, `docs/`, `diagrams/` |
| Docs | `docs/` | `00-project/`, `01-requirements/`, `02-architecture/`, `03-guides/`, `reports/` |
| Reports | `reports/` | Quality/audit artifacts, agent review outputs |
| AI Runtime | `.codex/`, `.gemini/` | Agent profiles, skills, runtime configs |

### Source layers (5 canonical under `src/bioetl/`)

| Layer | Subpackages | Purpose |
| --- | --- | --- |
| `domain` | ports, types, exceptions, entities, value_objects, config, models | Pure business logic, no I/O |
| `application` | pipelines, services, strategies, transformers | Use cases, orchestration |
| `infrastructure` | adapters, observability, persistence, http | External integrations |
| `composition` | bootstrap, factories, registries | Wiring, DI, composition root |
| `interfaces` | cli, api | User-facing entry points |

## 3. Naming Rules

### Python files and directories

- **Files**: `snake_case.py` — no uppercase, no hyphens
- **Directories (packages)**: `snake_case` — no uppercase, no hyphens
- **Test files**: `test_{source_module_name}.py`
- **Config files**: `{entity}.yaml` or `{provider}_{entity}.yaml`
- **Shim files**: `_compat.py`, `_legacy.py` — допустимо для backward compatibility

### Exceptions (valid, not violations)

- `__init__.py`, `__main__.py`, `conftest.py`
- `Makefile`, `Dockerfile`, `README.md`, `CHANGELOG.md`, `LICENSE`
- `.env`, `.env.*` (secret-bearing, но naming корректный)
- AI runtime dirs: `.codex/`, `.gemini/`, `.github/`

## 4. Depth Limits

- **Recommended max depth** from repo root: 7 levels
- **Source code recommended max**: `src/bioetl/{layer}/{package}/{subpackage}/{module}.py` = 5 levels
- Deeper nesting is a yellow flag requiring justification (e.g., provider-specific adapters)

## 5. Orphan Detection Heuristics

A file is considered potentially orphan when:

1. Python module not imported by any other module in `src/` or `tests/`
2. Empty `__init__.py` with no re-exports and no sibling modules
3. Config YAML not referenced in any pipeline config or composite
4. Report file older than 90 days with no ADR or issue reference
5. Script not referenced in `Makefile`, CI, or documentation

**False positive exclusions:**

- `conftest.py` at any level
- `__init__.py` with re-exports or `TYPE_CHECKING` blocks
- Files in `scripts/archive/` or `docs/archive/`
- Generated snapshots in `reports/quality/`
- Fixture data files in `tests/fixtures/`

## 6. Evidence Anchors

Before making structural claims, verify against current evidence packs:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`

Operational rule: package count alone does not trigger restructuring; topology
shows where to look, governance signals show where to act.

## 7. Integration Points

| Trigger | Target agent | Action |
| --- | --- | --- |
| Layout violations in `src/` | py-architecture-debt-bot | Debt wave inclusion |
| Orphan test files | py-test-bot | Test cleanup/rewrite |
| Naming violations in `configs/` | py-config-bot | Mass-rename |
| Doc structure drift | py-doc-bot | Doc reorganization |
| Actionable restructuring plan | py-plan-bot | RF-* decomposition |
| Post-restructuring verification | py-audit-bot | Final audit |
