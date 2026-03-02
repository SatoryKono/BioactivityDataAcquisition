# Semantic Scholar Publication Pipeline — Verification Report

> **Status:** Historical verification artifact (non-normative).
> Use this report as dated evidence only; current policy source of truth is `docs/00-project/RULES.md` and active ADRs.

*Дата верификации: 2026-01-25*
*Дата реализации: 2026-01-25*
*Версия pipeline: 1.2.0*
*Верификатор: Claude AI*

---

## 1. Сводка

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| **Paper ID валидация** | ✅ Реализовано | 40-char hex, схема + Value Object |
| **External IDs извлечение** | ✅ Реализовано | DOI, PubMed, ArXiv, CorpusId, MAG, DBLP, ACL |
| **TLDR извлечение** | ✅ Реализовано | Корректно обрабатывает nested structure |
| **Authors извлечение** | ✅ Реализовано | Whitespace-only имена фильтруются, names stripped |
| **Journal/Venue приоритет** | ✅ Реализовано | journal.name → venue fallback |
| **Open Access info** | ✅ Реализовано | oa-status нормализуется к lowercase |
| **Fields of Study** | ✅ Реализовано | null/empty элементы фильтруются |
| **Citation counts** | ✅ Реализовано | citationCount + influentialCitationCount |
| **Year валидация** | ✅ Реализовано | min-year=1500 для исторических публикаций |
| **Lookup metadata** | ✅ Реализовано | -lookup-method, -original-id |

**Общий статус:** 149/149 тестов проходят. Все найденные проблемы исправлены.

---

## 2. Детальный Анализ

### 2.1. Paper ID Validation

**Файлы:**
- `extractors.py:120` — не валидирует формат
- `transformer.py:169` — только проверяет наличие
- `publication.py:43-47` — Pandera схема с regex `^[a-f0-9]{40}$`
- `academic-ids.py:82-126` — SemanticScholarId Value Object

**Поведение:**
- Отсутствующий paper-id → record skipped (✅)
- Невалидный формат (не 40-char hex) → проходит transformer, отклоняется схемой (✅)

---

### 2.2. External IDs Extraction ✅ ИСПРАВЛЕНО

**Файл:** `extractors.py:19-46`

| API ключ | Извлекается? | Python ключ |
|----------|-------------|-------------|
| DOI | ✅ | `doi` |
| PubMed | ✅ | `pmid` |
| PMCID | ✅ | `pmcid` |
| PubMedCentral | ✅ (fallback) | `pmcid` |
| ArXiv | ✅ | `arxiv` |
| CorpusId | ✅ | `corpus-id` |
| MAG | ✅ | `mag` |
| **DBLP** | ✅ | `dblp` |
| ACL | ✅ | `acl` |

**Исправление:** Добавлено `"dblp": external-ids.get("DBLP")`.

---

### 2.3. TLDR Extraction

**Файл:** `extractors.py:193-210`

**Тестовое покрытие:**
- `tldr: null` → `None` ✅
- `tldr: {}` → `None` ✅
- `tldr.text: null` → `None` ✅
- `tldr.text: ""` → `""` (пустая строка проходит)
- `tldr.text: "valid"` → `"valid"` ✅

**Статус:** Полностью реализовано.

---

### 2.4. Authors Extraction ✅ ИСПРАВЛЕНО

**Файл:** `extractors.py:49-76`

**Исправление:**
```python
# Было:
if name:
    result.append(name)

# Стало:
if name and name.strip():
    result.append(name.strip())
```

**Поведение:**
- Whitespace-only имена (`"   "`) → фильтруются ✅
- Empty string (`""`) → фильтруются ✅
- None → фильтруются ✅
- Имена с whitespace → stripped ✅

---

### 2.5. Journal/Venue Priority

**Файл:** `extractors.py:79-108`

**Поведение:**
1. `journal.name` присутствует → используется `journal.name` ✅
2. `journal.name` пустой/None, `venue` присутствует → используется `venue` ✅
3. `journal` None → используется `venue` ✅

**Статус:** Полностью реализовано.

---

### 2.6. Open Access Information

**Файл:** `extractors.py:111-191`

**OA Status нормализация:**
| Input | Output |
|-------|--------|
| `"GOLD"` | `"gold"` ✅ |
| `"Green"` | `"green"` ✅ |
| `"unknown"` | `None` ✅ |
| `None` | `None` ✅ |
| `"  GOLD  "` | `"gold"` ✅ (whitespace trimmed) |

**Статус:** Полностью реализовано.

---

### 2.7. Fields of Study ✅ ИСПРАВЛЕНО

**Файл:** `extractors.py:213-237`

**Исправление:**
```python
# Было:
return fields-of-study[:max-count]

# Стало:
return [f for f in fields-of-study if f and isinstance(f, str)][:max-count]
```

**Поведение:**
- None элементы → фильтруются ✅
- Пустые строки → фильтруются ✅
- Фильтрация применяется перед max-count ✅

---

### 2.8. Citation/Reference Counts ✅ ИСПРАВЛЕНО

**Файлы:**
- `transformer.py:195-197` — извлекает `citationCount`, `referenceCount`, `influentialCitationCount`
- `publication.py:102-117` — валидация `ge=0` с `pd.Int64Dtype` для nullable integers

**Добавленное поле:** `influential-citation-count`
- Entity: `semanticscholar.py:78`
- Schema: `publication.py:113-117`
- Transformer: `transformer.py:197`

---

### 2.9. Year Validation

**Файл:** `extractors.py:240-256`

**Конфигурация:** `ValidationConfig(min-publication-year=1500)`

**Статус:** Полностью реализовано.

---

### 2.10. Lookup Metadata

**Файлы:**
- `adapter.py:239,274` — устанавливает `-lookup-method: "doi"`
- `fallback.py:219-220` — устанавливает `-lookup-method: "title-fallback"`, `-original-id`
- `transformer.py:168-169` — передаёт metadata без модификации

**Статус:** Полностью реализовано.

---

## 3. Тестовое Покрытие

| Тестовый файл | Тестов | Статус |
|---------------|--------|--------|
| `test-extractors.py` | 53 | ✅ Pass |
| `test-transformer.py` | 47 | ✅ Pass |
| `test-publication-schema.py` | 49 | ✅ Pass |
| **Итого** | **149** | **✅ Pass** |

---

## 4. Реализованные Исправления

### 4.1. Критичные (исправлено)

1. ✅ **Authors whitespace filtering** (`extractors.py:69-70`):
   - Whitespace-only имена теперь фильтруются
   - Имена теперь stripped

2. ✅ **Fields of Study filtering** (`extractors.py:234`):
   - None и пустые строки фильтруются
   - Фильтрация применяется перед max-count

### 4.2. Желательные (исправлено)

3. ✅ **DBLP extraction** (`extractors.py:44`):
   - Добавлено `"dblp": external-ids.get("DBLP")`

4. ✅ **influentialCitationCount** (`transformer.py:197`, `publication.py:113-117`):
   - Добавлено извлечение в transformer
   - Добавлено поле в схему с `pd.Int64Dtype` для nullable integer

---

## 5. Архитектурное Соответствие

| Требование | Соответствие |
|------------|--------------|
| Ports & Adapters | ✅ adapter в infrastructure, transformer в application |
| DI | ✅ pii-hasher, data-normalizer инжектируются |
| Value Objects | ✅ DOI, PubMedId, PublicationYear |
| Template Method | ✅ BasePublicationTransformer |
| Pandera Schema | ✅ SemanticScholarPublicationSchema |

---

## 6. Заключение

Semantic Scholar Publication Pipeline **полностью реализован** и соответствует всем требованиям:

- ✅ Все 10 аспектов верификации — реализованы
- ✅ Все 4 найденные проблемы — исправлены
- ✅ 149 тестов проходят
- ✅ Lint и mypy проверки проходят

**Коммиты:**
1. `a29023c` — docs: add Semantic Scholar pipeline verification report
2. `e103fc2` — feat(semanticscholar): implement verification findings
