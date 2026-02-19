# Аудит и план консолидации codex/* веток (документация диаграмм)

*Дата: 2026-02-17 (rev.2) | Автор: claude/audit-doc-branches*

---

## 1. Общая картина

Всего 12 веток (одна codex-ветка дублируется в списке) — **documentation-only**,
затрагивают исключительно `docs/02-architecture/`. Каждая ветка содержит ровно 1 коммит,
создана 2026-02-17.

| # | Ветка | Файлов | +/- | Суть изменений |
|---|-------|--------|-----|----------------|
| 1 | `codex/update-python-script-instructions-in-documentation` | 2 | +137/-68 | Shell-рендерер: CLI-флаги, env bash, уменьшенные размеры |
| 2 | `codex/update-render-diagrams.sh-script` | 1 | +70/-59 | Shell-рендерер: поддержка .mermaid+.mermaid, png/ выход, mapfile |
| 3 | `codex/update-diagram-overview-table` | 1 | +76/-52 | diagrams-index: добавление #12 (AWS, historical), скрипт валидации |
| 4 | `codex/update-architecture-documentation-components` | 1 | +53/-52 | diagrams-index: косметическое форматирование, пути к исходникам в Key Params |
| 5 | `codex/establish-diagram-structure-and-update-documentation` | 48 | +562/-510 | **Структурная**: перенос 25 .mermaid → mermaid/, создание png/, обновление 11 docs |
| 6 | `codex/update-diagram-catalog-for-500-candidates` | 1 | +555/-0 | Новый файл: diagram-catalog-500.md (формат D-001, ссылки на src/) |
| 7 | `codex/rename-deployment-file-and-update-references` | 3 | +71/-63 | Переименование #12: AWS → local-deployment, ADR-010 |
| 8 | `codex/evaluate-and-rank-candidate-diagrams` | 1 | +106/-105 | top-50: новые 5 критериев с взвешенной формулой (0.30*AI+...) |
| 9 | `codex/create-diagram-catalog-documentation` | 1 | +557/-0 | Новый файл: diagram-catalog-500.md (формат DC-001, дедупликация) |
| 10 | `codex/update-diagrams-with-new-evaluation-criteria` | 1 | +104/-99 | top-50: новые критерии, равные веса, 7 диаграмм с оценкой 10.0 |
| 11 | `codex/create-and-update-architecture-diagrams-documentation` | 4 | +702/-162 | Комбинированная: catalog-500 + top-25-report + top-50 ревизия + index |
| **12** | **`claude/document-bioetl-architecture-3SljB`** | **1** | **+691/-0** | **Новый файл: 500-diagram-proposals.md (15 категорий, TOP-25, типы диаграмм)** |

### Группы по merge-base

- **Группа A** (6 codex-веток, merge-base `d23fe5c3`, 2 коммита позади main): ветки 1–5, 11
- **Группа B** (5 codex-веток, merge-base `b742c985`, актуальны с main): ветки 6–10
- **Группа C** (1 claude-ветка, merge-base `b742c985`, 3 коммита позади main): ветка 12

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

### 2.3. `render-diagrams.sh` — 3 ветки (СРЕДНИЙ)

| Ветка | MERMAID-DIR | OUTPUT-DIR | Расширения | CLI-флаги |
|-------|-------------|------------|------------|-----------|
| #1 update-python-script | `$SCRIPT-DIR` | images/ | .mermaid | Да (полные) |
| #2 update-render-diagrams | `$SCRIPT-DIR` | png/ | .mermaid + .mermaid | Нет |
| #5 establish-diagram | `$SCRIPT-DIR/mermaid` | png/ | .mermaid | Нет |

**Вердикт**: Ветка #5 определяет каноническую структуру (mermaid/ → png/), #1 добавляет CLI-гибкость, #2 — совместимость с .mermaid.

### 2.4. Каталог 500 диаграмм — 4 ветки (НОВЫЙ ФАЙЛ × 2 имени)

Четыре ветки создают файл-каталог с предложениями по 500 диаграммам.
Три используют имя `diagram-catalog-500.md`, одна — `500-diagram-proposals.md`.

| Ветка | Файл | ID формат | Колонки | Типы | Категории | Сущности | Особенности |
|-------|------|-----------|---------|------|-----------|----------|-------------|
| #6 update-catalog-500 | `diagram-catalog-500.md` | D-001 | 7 (с назв.) | 3 | 10 блоков (рус.) | Пути к src/ файлам | — |
| #9 create-catalog-doc | `diagram-catalog-500.md` | DC-001 | 7 (с назв.) | 5 | 10 тематических (англ.) | Названия слоёв | Дедупликация 80%+ |
| #11 create-and-update | `diagram-catalog-500.md` | D001 | 6 (без назв.) | 10 | 2 (плоский список) | Имена классов | Минимальная структура |
| **#12 document-bioetl** | **`500-diagram-proposals.md`** | **1–500** | **4 (#, Name, Type, Desc)** | **10** | **15 (англ.)** | **Mermaid-типы + описания** | **TOP-25 приоритет, список 34 excluded, стат. распределение** |

**Вердикт**: Ветка #12 значительно качественнее остальных:
- Явный список 34 существующих диаграмм, исключённых из дубликации
- 15 категорий (vs 10/10/2) — наиболее гранулярная декомпозиция
- Статистика распределения типов диаграмм (flowchart 51.6%, classDiagram 18.8%, ...)
- Встроенный TOP-25 с обоснованием приоритетов
- 691 строка контента vs 555/557/519

Однако #6 имеет уникальное преимущество — прямые ссылки на `src/bioetl/` файлы.

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
- **Ветка #12** (`claude/document-bioetl-architecture-3SljB`) концептуально поглощает:
  - #6, #9, #11 (каталог 500 диаграмм) — но под другим именем файла и с иным форматом
  - Содержит встроенный TOP-25, частично пересекающийся с функцией top-50-diagrams.md

### Взаимоисключающие ветки
- **#8 vs #10 vs #11**: три конкурирующих методологии оценки top-50
- **#6 vs #9 vs #11 vs #12**: четыре конкурирующих каталога 500 диаграмм
- **#1 vs #2**: два конкурирующих подхода к render-diagrams.sh

---

## 4. Рекомендованные решения (выбор winner)

### 4.1. Структура каталога диаграмм
**Winner: Ветка #5** (`establish-diagram-structure`)

Обоснование: Единственная ветка, которая создаёт каноническую структуру
mermaid/ + png/ и обновляет все 11 документов с кросс-ссылками.
Все остальные ветки должны адаптироваться к этой структуре.

### 4.2. Скрипт рендеринга
**Winner: Комбинация #5 (структура) + #1 (CLI-флаги) + #2 (.mermaid совместимость)**

- Базовая структура: `mermaid/` → `png/` из #5
- CLI-интерфейс: `--width`, `--height`, `--scale` и т.д. из #1
- Расширения: поддержка `.mermaid` + `.mermaid` из #2
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

### 4.5. Каталог 500 диаграмм
**Winner: Ветка #12** (`claude/document-bioetl-architecture-3SljB`)
с дополнением src/-ссылок из **#6**

Обоснование:
- 15 категорий — наиболее гранулярная и осмысленная декомпозиция
- Явный exclude-список 34 существующих диаграмм — защита от дубликации
- Статистика распределения типов — помогает балансировать каталог
- Встроенный TOP-25 с обоснованием — готовый план реализации
- 691 строка качественного контента (больше всех вариантов)

Из ветки #6 стоит взять:
- Ссылки на конкретные файлы `src/bioetl/` в колонке сущностей
- Формат идентификаторов D-001 (со стабильным дефисным разделителем)

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
         → Конфликт: diagrams-index.md, top-50, render-diagrams.sh, 00-overview

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

Шаг 2.2: Cherry-pick из #12 (document-bioetl-architecture) в main
         → Новый файл 500-diagram-proposals.md, чистое добавление
         → Конфликтов нет (файл не существует на main)
         → POST-MERGE: обогатить src/bioetl/ ссылками из #6

Шаг 2.3: Cherry-pick из #3 (update-diagram-overview) — только скрипт валидации
         → Добавить в diagrams-index.md секцию проверки актуальности индекса
```

### Фаза 3: Скрипт рендеринга (после Фазы 1)

```
Шаг 3.1: Ручное объединение #1 + #2 в render-diagrams.sh
         → Базовые пути: mermaid/ → png/ (из #5, уже в main)
         → CLI-флаги из #1
         → Поддержка .mermaid + .mermaid из #2
         → Shebang и safety из #1
```

### Фаза 4: Отбрасываемые ветки

| Ветка | Решение | Причина |
|-------|---------|---------|
| #4 `update-architecture-documentation-components` | **CLOSE** | Косметика, полностью перезаписана #5 |
| #6 `update-diagram-catalog-for-500-candidates` | **PARTIAL** | Каталог уступает #12, но src/-ссылки полезны как дополнение |
| #9 `create-diagram-catalog-documentation` | **CLOSE** | Дубль каталога с менее полезным форматом (DC-001, без src/-путей) |
| #10 `update-diagrams-with-new-evaluation-criteria` | **CLOSE** | Конкурент #8 с завышенными баллами (7×10.0) |
| #11 `create-and-update-architecture-diagrams-documentation` | **CLOSE** | Супер-ветка, но каждая из её частей лучше представлена в специализированных ветках |

---

## 6. Итоговая таблица действий

| Ветка | Действие | Фаза |
|-------|----------|------|
| #5 establish-diagram-structure | **MERGE** (целиком) | 1.1 |
| #7 rename-deployment | **MERGE** (с адаптацией путей) | 1.2 |
| #8 evaluate-and-rank | **CHERRY-PICK** (top-50 обновление) | 2.1 |
| **#12 document-bioetl-architecture** | **MERGE** (каталог 500 диаграмм) | **2.2** |
| #6 update-catalog-500 | **PARTIAL PICK** (src/-ссылки → дополнить #12) | 2.2+ |
| #3 update-diagram-overview | **PARTIAL PICK** (только скрипт валидации) | 2.3 |
| #1 update-python-script-instructions | **PARTIAL PICK** (CLI-флаги для render-diagrams.sh) | 3.1 |
| #2 update-render-diagrams.sh | **PARTIAL PICK** (.mermaid совместимость) | 3.1 |
| #4 update-architecture-documentation | **CLOSE** (поглощена #5) | — |
| #9 create-diagram-catalog-doc | **CLOSE** (дубль, уступает #12) | — |
| #10 update-eval-criteria | **CLOSE** (конкурент #8, проигрывает) | — |
| #11 create-and-update-arch-diagrams | **CLOSE** (разобрана на части) | — |

---

## 7. Ожидаемые конфликты и их разрешение

### При merge #5:
- `diagrams-index.md`: принять версию #5 целиком (перестройка)
- `top-50-diagrams.md`: принять форматирование #5
- `render-diagrams.sh`: принять пути #5
- `00-overview.md`: принять пути #5

### При merge #7 (после #5):
- `diagrams-index.md`: добавить строку #12 как `mermaid/12-local-deployment-architecture.mermaid`
  с ссылкой на `png/12-local-deployment-architecture.png`
- `00-overview.md`: обновить ссылку на переименованный файл в mermaid/

### При cherry-pick #8 (после #5):
- `top-50-diagrams.md`: применить новую методологию поверх форматирования #5

### При merge #12:
- Конфликтов нет — добавляет новый файл `500-diagram-proposals.md`
- POST-MERGE: обогатить сущности ссылками на `src/bioetl/` из #6

---

## 8. Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Битые ссылки после переноса в mermaid/ | Высокая | #5 обновляет 11 docs, но проверить grep-ом |
| Расхождение top-50 оценок с каталогом-500 | Средняя | Провести cross-check ID |
| Два файла-каталога (500-diagram-proposals.md + diagram-catalog-500.md) | Низкая | Принять только #12; src/-ссылки из #6 перенести в #12 |
| TOP-25 в #12 vs top-50-diagrams.md (#8) — дублирование приоритетов | Средняя | Чётко разграничить: top-50 = рейтинг существующих, catalog = roadmap новых |
| render-diagrams.sh не работает с новыми путями | Средняя | Тестировать на реальных .mermaid файлах |
| Потеря полезного контента из #5 (удалённые секции) | Низкая | Секции Options 1-4 и Style — устаревшие инструкции |
