# Codex Branches Summary — 2026-02-24

> Автоматически собрано: 20 веток `codex/*` за последние 5 часов (03:08–08:08 UTC).

## Сводная таблица

| Группа | Веток | Code | Docs-only | Дубли |
|--------|-------|------|-----------|-------|
| Architectural Audit | 3 | 0 | 3 | 3 |
| Remove Deprecated Code | 3 | 3 | 0 | частично |
| Cleanup Dead Code | 2 | 2 | 0 | 0 |
| Analyze Duplication | 3 | 0 | 3 | 3 |
| Refactor Resume/Merge | 4 | 1 | 3 | 3 |
| Update Docs | 2 | 0 | 2 | 2 |
| Codex Instructions | 3 | 0 | 3 | 3 |
| **Итого** | **20** | **6** | **14** | **~14** |

---

## 1. Architectural Audit (3 ветки)

Три параллельных запуска одной задачи — провести architectural audit.
Все базируются на длинной цепочке (~7261 коммитов) и добавляют отчёт
с минимальными различиями.

| Branch | Commit |
|---|---|
| `codex/conduct-architectural-audit-for-bioetl-c3a0l8` | `docs: add architecture audit report for 2026-02-21` |
| `codex/conduct-architectural-audit-for-bioetl-7sbz2s` | `Add architecture audit report for 2026-02-21` |
| `codex/conduct-architectural-audit-for-bioetl-6k706u` | `docs: add BioETL architecture audit report` |

**Статус:** дубликаты, достаточно одной.

---

## 2. Remove Deprecated Code (3 ветки)

Три подхода разной степени агрессивности:

| Branch | Commit | Scope |
|---|---|---|
| `codex/remove-deprecated-code-in-bioetl` | `refactor: remove DeprecationWarning emissions` | Консервативно: убирает warnings, добавляет alias-тесты. 14 files, -321 lines |
| `codex/remove-deprecated-code-from-bioetl` | `refactor: remove deprecated aliases and warning emissions` | Радикально: удаляет deprecated модули целиком. 15 files, -456 lines |
| `codex/remove-deprecated-code-from-bioetl-6ecjp0` | `fix(scripts): restore terminology wrapper compatibility` | Точечно: упрощает `scripts/lint-terminology.py`. 1 file, -60/+12 lines |

---

## 3. Cleanup Dead/Unused Code (2 ветки)

Два неконфликтующих аспекта чистки — можно мержить оба.

| Branch | Commit | Scope |
|---|---|---|
| `codex/cleanup-dead-and-unused-code` | `chore: remove impossible async-generator branches` | crossref, openalex, semanticscholar, uniprot, filterable-mixin. 5 files, -10 lines |
| `codex/cleanup-dead-and-unused-code-3j1ahg` | `chore: remove unused imports and no-op statements` | cached-bronze, circuit-breaker, base-schemas, delta-reader, metadata-writer. 5 files, -8 lines |

---

## 4. Analyze Code Duplication (3 ветки)

Три варианта отчёта об анализе дублирования, все docs-only.

| Branch | Commit | Lines |
|---|---|---|
| `codex/analyze-code-duplication-and-extract-logic` | `docs: add code duplication analysis report` | +186 |
| `codex/analyze-code-duplication-and-extract-logic-qds3s7` | `docs: add 2026-02-24 code duplication analysis report` | +235 |
| `codex/analyze-code-duplication-and-extract-logic-n50rpx` | `docs: consolidate duplication audit findings` | +170 (2 коммита, наиболее зрелая) |

---

## 5. Refactor Resume/Merge After Reload (4 ветки)

Задача: resume пайплайна без повторной загрузки данных.

| Branch | Commit | Тип |
|---|---|---|
| `codex/refactor-code-for-data-merging-after-reload` | `docs: propose cursor-based resume and dual-run merge strategy` | Design doc, +117 |
| `codex/refactor-code-for-data-merging-after-reload-fl4atb` | `docs: add proposal for stateful resume without re-downloading` | Design doc, +149 |
| `codex/refactor-code-for-data-merging-after-reload-7ay1zg` | `docs: propose resume strategy without refetch and duplicate loads` | Design doc, +175 |
| **`codex/refactor-code-for-data-merging-after-reload-1sq8e7`** | **`Add PubMed resume offset handling`** | **Code: PubMed client + тест, +76 lines** |

Единственная ветка с рабочим кодом — `1sq8e7`.

---

## 6. Update Documentation (2 ветки)

| Branch | Commit | Scope |
|---|---|---|
| `codex/update-bioetl-project-documentation` | `docs: add codex agent guidance and navigation links` | 4 files, +365/-137 (рефакторит 00-map.md) |
| `codex/update-bioetl-project-documentation-hvktvz` | `docs: add Codex governance playbook and references` | 4 files, +221/-1 (консервативная) |

---

## 7. Develop Codex User Instructions (3 ветки)

Три варианта CODEX.md с инструкциями для Codex-агента.

| Branch | Commit | CODEX.md size |
|---|---|---|
| `codex/develop-user-instructions-for-codex` | `docs(agents): add Codex custom architecture-audit instructions` | 238 lines |
| `codex/develop-user-instructions-for-codex-rial2t` | `docs: add Codex architecture auditor instructions` | ~205 lines |
| `codex/develop-user-instructions-for-codex-qwldm4` | `docs(agents): add Codex custom instruction profile` | ~149 lines |

---

## Ключевые наблюдения

1. **~70% дублирование**: 14 из 20 веток — параллельные попытки одних и тех же задач.
2. **70% docs-only**: 14 веток содержат только документацию/отчёты, без code changes.
3. **Code-кандидаты на merge** (6 веток):
   - `codex/cleanup-dead-and-unused-code` — unreachable async branches
   - `codex/cleanup-dead-and-unused-code-3j1ahg` — unused imports
   - `codex/remove-deprecated-code-from-bioetl` — удаление deprecated modules
   - `codex/remove-deprecated-code-from-bioetl-6ecjp0` — чистка lint-terminology.py
   - `codex/remove-deprecated-code-in-bioetl` — убрать DeprecationWarnings
   - `codex/refactor-code-for-data-merging-after-reload-1sq8e7` — PubMed resume offset
