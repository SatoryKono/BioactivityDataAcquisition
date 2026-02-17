# Аудит и план консолидации codex/* веток (документация диаграмм)

*Дата: 2026-02-17 | Автор: claude/audit-doc-branches*

---

## 1. Общая картина

Все 11 веток (одна дублируется) — **documentation-only**, затрагивают исключительно
`docs/02-architecture/`. Каждая ветка содержит ровно 1 коммит, создана 2026-02-17.

| # | Ветка | Файлов | +/- | Суть изменений |
|---|-------|--------|-----|----------------|
| 1 | `update-python-script-instructions-in-documentation` | 2 | +137/-68 | Shell-рендерер: CLI-флаги, env bash, уменьшенные размеры |
| 2 | `update-render_diagrams.sh-script` | 1 | +70/-59 | Shell-рендерер: поддержка .mermaid+.mmd, png/ выход, mapfile |
| 3 | `update-diagram-overview-table` | 1 | +76/-52 | diagrams-index: добавление #12 (AWS, historical), скрипт валидации |
| 4 | `update-architecture-documentation-components` | 1 | +53/-52 | diagrams-index: косметическое форматирование, пути к исходникам в Key Params |
| 5 | `establish-diagram-structure-and-update-documentation` | 48 | +562/-510 | **Структурная**: перенос 25 .mermaid → mermaid/, создание png/, обновление 11 docs |
| 6 | `update-diagram-catalog-for-500-candidates` | 1 | +555/-0 | Новый файл: diagram-catalog-500.md (формат D-001, ссылки на src/) |
| 7 | `rename-deployment-file-and-update-references` | 3 | +71/-63 | Переименование #12: AWS → local-deployment, ADR-010 |
| 8 | `evaluate-and-rank-candidate-diagrams` | 1 | +106/-105 | top-50: новые 5 критериев с взвешенной формулой (0.30*AI+...) |
| 9 | `create-diagram-catalog-documentation` | 1 | +557/-0 | Новый файл: diagram-catalog-500.md (формат DC-001, дедупликация) |
| 10 | `update-diagrams-with-new-evaluation-criteria` | 1 | +104/-99 | top-50: новые критерии, равные веса, 7 диаграмм с оценкой 10.0 |
| 11 | `create-and-update-architecture-diagrams-documentation` | 4 | +702/-162 | Комбинированная: catalog-500 + top-25-report + top-50 ревизия + index |

### Группы по merge-base

- **Группа A** (6 веток, merge-base `d23fe5c3`, 2 коммита позади main): ветки 1–5, 11
- **Группа B** (5 веток, merge-base `b742c985`, актуальны с main): ветки 6–10

---

## 2. Карта конфликтов

5 файлов модифицируются несколькими ветками:

### 2.1. `diagrams-index.md` — 6 веток (КРИТИЧЕСКИЙ)

| Ветка | Изменения |
|-------|-----------|
| #1 update-python-script | Shell-инструкции вместо Python |
| #3 update-diagram-overview | +диаграмма #12 (AWS historical), скрипт валидации |
| #4 update-arch-components | Форматирование таблицы, пути в Key Params |
| #5 establish-diagram-structure | **Полная перестройка**: удаление секций Options 1-4, Style, Key Params; ссылки на mermaid/png |
| #7 rename-deployment | +диаграмма #12 (local-deployment), секция Deprecated |
| #11 create-and-update | Косметическое форматирование |

**Вердикт**: Ветка #5 наиболее деструктивна (удаляет крупные секции). Остальные частично совместимы между собой, но не с #5.

### 2.2. `top-50-diagrams.md` — 4 ветки (ВЫСОКИЙ)

| Ветка | Методология | Формула |
|-------|-------------|---------|
| #5 establish-diagram | Без изменений (переформатирование) | Оригинальная |
| #8 evaluate-and-rank | 5 новых критериев | 0.30*AI + 0.25*CC + 0.20*CR + 0.15*OV + 0.10*OB |
| #10 update-eval-criteria | 5 новых критериев | (AI+CC+CR+OV+OB)/5 (равные веса) |
| #11 create-and-update | Оригинальные 5 критериев, v2.0 | Оригинальная, с прозрачными баллами |

**Вердикт**: Три конкурирующих подхода к оценке. Нужен выбор одного.

### 2.3. `render_diagrams.sh` — 3 ветки (СРЕДНИЙ)

| Ветка | MERMAID_DIR | OUTPUT_DIR | Расширения | CLI-флаги |
|-------|-------------|------------|------------|-----------|
| #1 update-python-script | `$SCRIPT_DIR` | images/ | .mermaid | Да (полные) |
| #2 update-render_diagrams | `$SCRIPT_DIR` | png/ | .mermaid + .mmd | Нет |
| #5 establish-diagram | `$SCRIPT_DIR/mermaid` | png/ | .mermaid | Нет |

**Вердикт**: Ветка #5 определяет каноническую структуру (mermaid/ → png/), #1 добавляет CLI-гибкость, #2 — совместимость с .mmd.

### 2.4. `diagram-catalog-500.md` — 3 ветки (НОВЫЙ ФАЙЛ)

| Ветка | ID формат | Колонки | Типы диаграмм | Сущности |
|-------|-----------|---------|---------------|----------|
| #6 update-catalog-500 | D-001 | 7 (с названием) | 3 | Пути к src/ файлам |
| #9 create-catalog-doc | DC-001 | 7 (с названием) | 5 | Названия слоёв |
| #11 create-and-update | D001 | 6 (без названия) | 10 | Имена классов |

**Вердикт**: Три варианта одного файла. Ветка #11 наиболее компактна и разнообразна по типам, но #6 имеет самые точные ссылки на исходный код.

### 2.5. `00-overview.md` — 2 ветки (НИЗКИЙ)

| Ветка | Изменения |
|-------|-----------|
| #5 establish-diagram | Обновление путей к mermaid/ |
| #7 rename-deployment | Переименование ссылки на deployment-диаграмму |

**Вердикт**: Неконфликтные изменения в разных частях файла. Легко объединяются.

---

## 3. Дубликаты и поглощения

### Полные дубликаты
- **Ветка #7 `rename-deployment-file-and-update-references`** указана в списке дважды → одна ветка

### Поглощения (superset ← subset)
- **Ветка #11** (`create-and-update-architecture-diagrams-documentation`) частично поглощает:
  - #8 и #10 (изменения в top-50-diagrams.md)
  - #6 и #9 (создание diagram-catalog-500.md)
  - Однако #11 использует ДРУГОЙ подход к оценке и другой формат каталога

### Взаимоисключающие ветки
- **#8 vs #10 vs #11**: три конкурирующих методологии оценки top-50
- **#6 vs #9 vs #11**: три конкурирующих формата catalog-500
- **#1 vs #2**: два конкурирующих подхода к render_diagrams.sh

---

## 4. Рекомендованные решения (выбор winner)

### 4.1. Структура каталога диаграмм
**Winner: Ветка #5** (`establish-diagram-structure`)

Обоснование: Единственная ветка, которая создаёт каноническую структуру
mermaid/ + png/ и обновляет все 11 документов с кросс-ссылками.
Все остальные ветки должны адаптироваться к этой структуре.

### 4.2. Скрипт рендеринга
**Winner: Комбинация #5 (структура) + #1 (CLI-флаги) + #2 (.mmd совместимость)**

- Базовая структура: `mermaid/` → `png/` из #5
- CLI-интерфейс: `--width`, `--height`, `--scale` и т.д. из #1
- Расширения: поддержка `.mermaid` + `.mmd` из #2
- Shebang: `#!/usr/bin/env bash` из #1
- Shell safety: `set -euo pipefail` из #1

### 4.3. diagrams-index.md
**Winner: Ветка #5 (база) + cherry-pick из #3 и #7**

- Базовая версия: #5 (новая структура, ссылки на mermaid/ и png/)
- Из #3: скрипт валидации актуальности индекса
- Из #7: переименование #12 в `local-deployment-architecture` + ADR-010 + секция Deprecated
- Из #4: пути к исходникам в Key Params → **отбросить** (секция Key Params удалена в #5)

### 4.4. top-50-diagrams.md
**Winner: Ветка #8** (`evaluate-and-rank-candidate-diagrams`)

Обоснование:
- Взвешенная формула (#8) лучше равных весов (#10), т.к. Architecture Impact
  объективно важнее Onboarding Value
- Оригинальная формула в #11 менее прозрачна (нет per-criterion scores)
- #10 даёт 7 диаграмм с идеальной оценкой 10.0 — явно завышенные баллы
- Форматирование из #5 можно применить отдельно

### 4.5. diagram-catalog-500.md
**Winner: Ветка #6** (`update-diagram-catalog-for-500-candidates`)

Обоснование:
- Содержит ссылки на конкретные файлы `src/bioetl/` — наиболее полезно
  для разработчиков
- Формат D-001 удобнее для сортировки, чем DC-001 или D001
- Имеет колонку "название" — важно для каталога из 500 записей
- Можно дополнить разнообразием типов диаграмм из #11

### 4.6. Переименование deployment-диаграммы
**Winner: Ветка #7** (`rename-deployment-file-and-update-references`)

Обоснование: ADR-010 Local-Only — каноническое решение проекта.
AWS-название — legacy, должно быть deprecated.

---

## 5. План консолидации (порядок слияния)

### Фаза 1: Структурная база (КРИТИЧЕСКИЙ ПУТЬ)

```
Шаг 1.1: Merge ветки #5 (establish-diagram-structure) в main
         → Устанавливает mermaid/ + png/ структуру
         → Обновляет все 11 документов
         → Конфликт: diagrams-index.md, top-50, render_diagrams.sh, 00-overview

Шаг 1.2: Merge ветки #7 (rename-deployment) в main
         → Переименование #12: AWS → local-deployment
         → Ручное разрешение конфликта в diagrams-index.md и 00-overview.md
         → ВАЖНО: файл .mermaid нужно переместить в mermaid/ (адаптация к #5)
```

### Фаза 2: Контент (после Фазы 1)

```
Шаг 2.1: Cherry-pick из #8 (evaluate-and-rank) в main
         → Новая методология top-50
         → Ручное разрешение: пути в top-50 могут отличаться после #5
         → Сохранить форматирование из #5

Шаг 2.2: Cherry-pick из #6 (diagram-catalog-500) в main
         → Новый файл, чистое добавление
         → Конфликтов нет (файл не существует на main после #5)

Шаг 2.3: Cherry-pick из #3 (update-diagram-overview) — только скрипт валидации
         → Добавить в diagrams-index.md секцию проверки актуальности индекса
```

### Фаза 3: Скрипт рендеринга (после Фазы 1)

```
Шаг 3.1: Ручное объединение #1 + #2 в render_diagrams.sh
         → Базовые пути: mermaid/ → png/ (из #5, уже в main)
         → CLI-флаги из #1
         → Поддержка .mermaid + .mmd из #2
         → Shebang и safety из #1
```

### Фаза 4: Отбрасываемые ветки

| Ветка | Решение | Причина |
|-------|---------|---------|
| #4 `update-architecture-documentation-components` | **ОТБРОСИТЬ** | Косметика, полностью перезаписана #5 |
| #9 `create-diagram-catalog-documentation` | **ОТБРОСИТЬ** | Дубль #6 с менее полезным форматом (DC-001, без src/-путей) |
| #10 `update-diagrams-with-new-evaluation-criteria` | **ОТБРОСИТЬ** | Конкурент #8 с завышенными баллами (7×10.0) |
| #11 `create-and-update-architecture-diagrams-documentation` | **ОТБРОСИТЬ** | Супер-ветка, но каждая из её частей лучше представлена в специализированных ветках |

---

## 6. Итоговая таблица действий

| Ветка | Действие | Фаза |
|-------|----------|------|
| #5 establish-diagram-structure | **MERGE** (целиком) | 1.1 |
| #7 rename-deployment | **MERGE** (с адаптацией путей) | 1.2 |
| #8 evaluate-and-rank | **CHERRY-PICK** (top-50 обновление) | 2.1 |
| #6 update-catalog-500 | **CHERRY-PICK** (новый файл) | 2.2 |
| #3 update-diagram-overview | **PARTIAL PICK** (только скрипт валидации) | 2.3 |
| #1 update-python-script-instructions | **PARTIAL PICK** (CLI-флаги для render_diagrams.sh) | 3.1 |
| #2 update-render_diagrams.sh | **PARTIAL PICK** (.mmd совместимость) | 3.1 |
| #4 update-architecture-documentation | **CLOSE** (поглощена #5) | — |
| #9 create-diagram-catalog-doc | **CLOSE** (дубль #6) | — |
| #10 update-eval-criteria | **CLOSE** (конкурент #8, проигрывает) | — |
| #11 create-and-update-arch-diagrams | **CLOSE** (разобрана на части) | — |

---

## 7. Ожидаемые конфликты и их разрешение

### При merge #5:
- `diagrams-index.md`: принять версию #5 целиком (перестройка)
- `top-50-diagrams.md`: принять форматирование #5
- `render_diagrams.sh`: принять пути #5
- `00-overview.md`: принять пути #5

### При merge #7 (после #5):
- `diagrams-index.md`: добавить строку #12 как `mermaid/12-local-deployment-architecture.mermaid`
  с ссылкой на `png/12-local-deployment-architecture.png`
- `00-overview.md`: обновить ссылку на переименованный файл в mermaid/

### При cherry-pick #8 (после #5):
- `top-50-diagrams.md`: применить новую методологию поверх форматирования #5

### При cherry-pick #6:
- Конфликтов нет — чистое добавление нового файла

---

## 8. Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Битые ссылки после переноса в mermaid/ | Высокая | #5 обновляет 11 docs, но проверить grep-ом |
| Расхождение top-50 оценок с каталогом-500 | Средняя | Провести cross-check ID |
| render_diagrams.sh не работает с новыми путями | Средняя | Тестировать на реальных .mermaid файлах |
| Потеря полезного контента из #5 (удалённые секции) | Низкая | Секции Options 1-4 и Style — устаревшие инструкции |
