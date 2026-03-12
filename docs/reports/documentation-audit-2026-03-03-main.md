# Documentation Audit Report (BioETL v5.23+)

## Summary
- Date: 2026-03-03
- Scope: Полный doc-аудит с фокусом на `docs/04-reference/providers/**`, синхронизацию ключей с code/config, и контроль сборки/ссылок в основной ветке (без `.worktrees/**`).
- Overall status: **Remediated (blocking checks pass)**. Ключевой дрейф провайдер-доков устранён; остались неблокирующие зоны улучшений по навигации/гигиене документации.

## Inventory
- Docs scanned: `696` markdown-файлов в `docs/`.
- Provider docs scanned: `22` файла в `docs/04-reference/providers`.
- Entry points (README.md, mkdocs.yml): проверены.

## Findings by severity
### Critical
- None.

### High
- None.

### Medium
- `mkdocs` nav coverage gap: ориентировочно `131` markdown-файл не включён в nav (в основном `02-architecture/diagram-descriptions/**`, `99-archive/**`, части `plans/**` и `reports/**`). Это снижает discoverability и осложняет поддержку единого source of truth.
- `mkdocs --strict` проходит, но при сборке есть предупреждение о несовместимости Material с будущим MkDocs 2.0; это не блокирует текущий релиз, но создаёт среднесрочный риск toolchain drift.

### Low
- В `git diff` по docs наблюдаются массовые CRLF/LF предупреждения (не блокирует проверку, но шумит аудит и ревью).
- В audit-процедурах встречается ожидание `docs/00-project/REQUIREMENTS.md`, тогда как фактический путь — `docs/01-requirements/REQUIREMENTS.md`.

## Proposed changes (prioritized)
1. **Stabilize provider docs (done)**
   - Привести provider reference к canonical `snake_case`, синхронизировать с `configs/entities/**` и трансформерами.
   - Статус: выполнено.
2. **Close nav/discoverability gap**
   - Явно определить policy: какие docs должны быть в nav, а какие должны быть помечены как archive/internal-only.
   - Добавить/обновить index-страницы для `diagram-descriptions`, `reports`, `plans` и архивных зон.
3. **Harden doc-audit automation**
   - Обновить чек-листы/скрипты на актуальный путь REQUIREMENTS (`docs/01-requirements/REQUIREMENTS.md`).
   - Добавить отдельную проверку «legacy field naming drift» для provider docs.
4. **Toolchain risk mitigation**
   - Зафиксировать план миграции/пинов для MkDocs/Material (без срочного внедрения, но с владельцем и сроком).

## Required decisions
- Decision 1: Делаем ли `99-archive/**` и `diagram-descriptions/**` явно «out-of-nav archival» (и оставляем как есть), или постепенно возвращаем релевантные страницы в основную навигацию?
- Decision 2: Нужен ли отдельный CI-check на лимит `not_in_nav` (например, baseline + запрет роста), чтобы не накапливать orphan docs?

## Updated files (if changes applied)
- `docs/04-reference/providers/chembl/assay-parameters.md`
- `docs/04-reference/providers/chembl/assay.md`
- `docs/04-reference/providers/chembl/cell-line.md`
- `docs/04-reference/providers/chembl/compound-record.md`
- `docs/04-reference/providers/chembl/molecule.md`
- `docs/04-reference/providers/chembl/protein-class.md`
- `docs/04-reference/providers/chembl/publication-similarity.md`
- `docs/04-reference/providers/chembl/publication-term.md`
- `docs/04-reference/providers/chembl/publication.md`
- `docs/04-reference/providers/chembl/subcellular-fraction.md`
- `docs/04-reference/providers/chembl/target-component.md`
- `docs/04-reference/providers/chembl/target.md`
- `docs/04-reference/providers/chembl/tissue.md`
- `docs/04-reference/providers/crossref/publication.md`
- `docs/04-reference/providers/openalex/publication.md`
- `docs/04-reference/providers/pubchem/compound.md`
- `docs/04-reference/providers/pubmed/publication.md`
- `docs/04-reference/providers/semanticscholar/publication.md`
- `docs/04-reference/providers/uniprot/idmapping.md`
- `docs/04-reference/providers/uniprot/protein.md`
- `mkdocs.yml` (strict build hygiene)

## Dead or orphan docs (candidates)
- Категория 1: `docs/02-architecture/diagram-descriptions/mmd-diagrams/**` (часть страниц без nav-включения).
- Категория 2: `docs/99-archive/**` (archive-материалы, ожидаемо вне основной навигации; требуется явная policy/labels).
- Категория 3: `docs/plans/**`, `docs/reports/**` (частично без nav-включения, не всегда понятно active vs archival).

## Verification
- RULES.md and REQUIREMENTS.md sync:
  - `docs/00-project/RULES.md` и `docs/01-requirements/REQUIREMENTS.md` содержат согласованные Local-Only/Observability требования.
  - Требуется унифицировать ссылки в audit-чеклистах на актуальный путь REQUIREMENTS.
- ADR alignment (ADR-010, ADR-014, ADR-017):
  - Подтверждено в `README.md`, `mkdocs.yml`, `docs/00-project/RULES.md`, `docs/02-architecture/**`.
- Link check:
  - `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py` — PASS
  - `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --legacy-paths` — PASS
- Additional validation:
  - `./.venv/Scripts/python.exe -m pytest tests/architecture/test_docs_version_sync.py -q -p no:xdist --tb=short` — PASS
  - `./.venv/Scripts/python.exe -m pytest tests/architecture/test_check_doc_links_guardrails.py -q -p no:xdist --tb=short` — PASS
  - `./.venv/Scripts/python.exe -m mkdocs build --strict` — PASS
