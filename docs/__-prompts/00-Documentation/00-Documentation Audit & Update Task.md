Documentation Audit & Update Task

**Контекст**: BioETL project, RULES.md v5.0 (2025-12-15)
**Scope**: Полный аудит, оптимизация и актуализация документации

---

## 1. Фаза: Инвентаризация

### 1.1. Построить карту документов

Выполнить сканирование `docs/` и `.cursor/rules/`:
```bash
find docs/ .cursor/rules/ -name "*.md" -type f | sort
```

Для каждого файла зафиксировать:
| Поле | Описание |
|------|----------|
| `path` | Полный путь |
| `title` | H1 заголовок |
| `last_sync` | Версия RULES.md, указанная в файле |
| `size_lines` | Количество строк |
| `has_diagrams` | Mermaid/PlantUML/ASCII |
| `cross_refs` | Ссылки на другие документы |

### 1.2. Выявить проблемы

**Категории проблем**:

| Код | Тип | Критерий | Действие |
|-----|-----|----------|----------|
| `DUP` | Дублирование | >50% совпадение контента | Merge или удаление |
| `STALE` | Устаревший | `last_sync` < v5.0 | Обновление или удаление |
| `ORPHAN` | Осиротевший | Нет входящих ссылок | Проверить релевантность |
| `NUM` | Конфликт нумерации | Два файла с одинаковым NN- | Перенумеровать |
| `EMPTY` | Пустой/stub | <30 строк без контента | Удаление или дополнение |

---

## 2. Фаза: Удаление устаревшего

### 2.1. Критерии удаления (MUST)

Удалить файл, если:
- [ ] Контент полностью покрыт другим документом
- [ ] Описывает deprecated функционал без пометки `[DEPRECATED]`
- [ ] Не обновлялся >6 месяцев И не ссылается из актуальных документов
- [ ] Содержит только TODO/placeholder

### 2.2. Процедура удаления
```bash
# 1. Проверить входящие ссылки
grep -r "filename.md" docs/ .cursor/

# 2. Если ссылок нет — удалить
git rm docs/path/to/obsolete.md

# 3. Если есть ссылки — обновить их перед удалением
```

### 2.3. Кандидаты на проверку (из текущей структуры)

| Файл | Проблема | Рекомендация |
|------|----------|--------------|
| `00-rules-summary.md` + `01-project-rules.md` | Потенциальное `DUP` | Проверить overlap |
| `04-duplication-reduction.md` vs `04-extending-bioetl.md` | `NUM` конфликт | Перенумеровать |
| `05-physical-layout.md` vs `05-cleanup-policy.md` | `NUM` конфликт | Перенумеровать |

---

## 3. Фаза: Оптимизация

### 3.1. Структурная оптимизация

**Целевая иерархия** (согласно `03-file-policy.md`):
```
docs/
├── architecture/           # ADR, диаграммы, принципы
│   ├── decisions/          # NNNN-title.md
│   ├── diagrams/           # .mermaid/.puml источники
│   └── 0N-*.md             # Архитектурные документы
├── contracts/
│   └── gold/               # JSON Schema
├── guides/                 # How-to
├── runbooks/               # Операционные процедуры
└── rules/                  # Консолидированные правила
    ├── 00-rules-summary.md # Quick reference (единственный)
    └── RULES.md            # Canonical source of truth
```

### 3.2. Консолидация правил

**Проблема**: `00-rules-summary.md`, `01-project-rules.md`, `02-user-rules.md` частично дублируют `RULES.md`.

**Решение**:
1. `RULES.md` — единственный canonical source
2. `00-rules-summary.md` — краткий TL;DR (≤200 строк)
3. `01-project-rules.md` → удалить, контент в RULES.md
4. `02-user-rules.md` → переместить в `.cursor/rules/` как user-specific overlay

### 3.3. Перенумерация архитектурных документов
```
docs/architecture/
├── 01-domain-objects.md
├── 02-etl-layers.md
├── 03-data-flow.md
├── 04-duplication-reduction.md
├── 05-extending-bioetl.md      # было 04-
├── 06-physical-layout.md       # было 05-
├── 07-cleanup-policy.md        # было 05-
└── 08-architecture-diagrams.md # было 06-
```

---

## 4. Фаза: Диаграммы

### 4.1. Аудит диаграмм

Для каждой диаграммы в `06-architecture-diagrams.md`:

| ID | Название | Текущий формат | Целевой формат |
|----|----------|----------------|----------------|
| D1 | High-Level Architecture | ASCII | Mermaid flowchart |
| D2 | Medallion Architecture | ASCII | Mermaid flowchart |
| D3 | Pipeline Sequence | ASCII | Mermaid sequenceDiagram |
| D4 | Circuit Breaker FSM | ASCII | Mermaid stateDiagram |
| D5 | DQ Error Routing | ASCII | Mermaid flowchart |
| D6 | Locking Sequence | ASCII | Mermaid sequenceDiagram |
| D7 | Class Diagram | ASCII | Mermaid classDiagram |
| D8 | Deployment | ASCII | Mermaid flowchart |

### 4.2. Конвертация в Mermaid (SHOULD)

**Шаблон**:
```mermaid
---
title: 
---

    %% Автогенерация: docs/architecture/diagrams/.mermaid
    %% Sync: RULES.md v5.0
    ...
```

**Файловая структура**:
```
docs/architecture/diagrams/
├── 00-diagramming-policy.md
├── 01-high-level.mermaid
├── 02-medallion.mermaid
├── 03-pipeline-sequence.mermaid
├── 04-circuit-breaker.mermaid
├── 05-dq-routing.mermaid
├── 06-locking.mermaid
├── 07-classes.mermaid
└── 08-deployment.mermaid
```

### 4.3. Интеграция с документами

Заменить ASCII-блоки на включения:
```markdown
## 1. High-Level Architecture

![High-Level Architecture](diagrams/01-high-level.mermaid)



Текстовое описание
...

```

---

## 5. Фаза: Добавление недостающего

### 5.1. Gap-анализ (сравнение с RULES.md v5.0)

| Раздел RULES.md | Документ | Статус |
|-----------------|----------|--------|
| §1 Архитектура | 02-etl-layers.md | ✓ |
| §2 Medallion | 03-data-flow.md | ✓ |
| §3 Observability | — | **MISSING** |
| §5.5 DR | runbooks/ | Частично |
| §7 Schema Evolution | — | **MISSING** |
| App C Runbook | runbooks/ | Проверить полноту |

### 5.2. Недостающие документы (SHOULD)

| Файл | Содержание |
|------|------------|
| `docs/guides/observability.md` | Логи, метрики, алерты (§3.2–3.4) |
| `docs/guides/schema-evolution.md` | Миграции, deprecation workflow (§7.1, App E) |
| `docs/runbooks/dr-complete.md` | Консолидированный DR playbook (§5.5) |

---

## 6. Валидация

### 6.1. Чек-лист после обновления

- [ ] Все файлы имеют `*Aligned with RULES.md v5.0*` или `*Синхронизировано с RULES.md v5.0*`
- [ ] Нет конфликтов нумерации `NN-`
- [ ] Все cross-refs валидны: `grep -r "\[.*\](.*\.md)" docs/ | while read l; do ...`
- [ ] Диаграммы рендерятся в Mermaid Live Editor
- [ ] `docs/00-map.md` (если есть) актуален
- [ ] CHANGELOG.md обновлён с описанием doc changes

### 6.2. Автоматизация (MAY)
```python
# scripts/validate_docs.py
def check_sync_header(path: Path) -> bool:
    """Проверка наличия sync header."""
    ...

def check_broken_links(docs_dir: Path) -> list[str]:
    """Поиск битых ссылок."""
    ...

def check_mermaid_syntax(path: Path) -> bool:
    """Валидация Mermaid синтаксиса."""
    ...
```

---

## 7. Execution Order

1. **Инвентаризация** → таблица всех документов
2. **Удаление** → git rm obsolete files
3. **Перенумерация** → git mv с обновлением ссылок
4. **Консолидация** → merge duplicate content
5. **Диаграммы** → конвертация ASCII → Mermaid
6. **Gap-fill** → создание недостающих документов
7. **Валидация** → чек-лист
8. **Commit** → atomic commit с описанием изменений

---

## Constraints

- **Не удалять** без проверки входящих ссылок
- **Не менять** семантику контента при оптимизации
- **Сохранять** RFC 2119 терминологию (MUST/SHOULD/MAY)
- **Фиксировать** все удаления/перемещения в CHANGELOG.md