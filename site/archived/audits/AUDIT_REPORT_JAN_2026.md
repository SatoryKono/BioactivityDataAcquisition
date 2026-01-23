# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-07
**Ветка**: main
**Автор**: Jules (Agent)

## Executive Summary

В ходе систематического анализа кодовой базы BioETL (версия 5.0.6) были выявлены ключевые зоны дублирования логики в слое трансформации данных. Анализ охватил 4 основных провайдера (ChEMBL, PubMed, OpenAlex, Semantic Scholar).

**Основные находки:**
1.  **Дублирование логики экстракции публикаций**: OpenAlex и Semantic Scholar используют идентичные паттерны для извлечения авторов, информации о журналах и Open Access статусов, но реализуют их независимо в `extractors.py`.
2.  **Отсутствие наследования в PubMed**: Пайплайн PubMed не использует `BasePublicationTransformer`, дублируя ~40 LOC шаблонной логики трансформации (вычисление хешей, ID, валидация).
3.  **Бойлерплейт в `__init__` трансформеров**: Множественные классы трансформеров дублируют сигнатуру `__init__` только для передачи аргументов в `super()`.

**Потенциал оптимизации:**
-   Сокращение кодовой базы: ~150-200 LOC.
-   Унификация логики обработки авторов (нормализация имен) и дат.
-   Снижение когнитивной нагрузки за счет стандартизации `PubMed` под `BasePublicationTransformer`.

---

## 1. Карты зависимостей

### 1.1 Extractors (OpenAlex & SemanticScholar)

Эти модули содержат чистые функции, не зависящие от I/O, что делает их идеальными кандидатами для объединения.

**OpenAlex Extractors (`src/bioetl/application/pipelines/openalex/extractors.py`)**
-   **Импорты**: `typing.Any`
-   **Экспортирует**: `extract_authors`, `extract_journal_info`, `extract_open_access_info`, `extract_doi`, `reconstruct_abstract`
-   **Пользователи**: `OpenAlexPublicationTransformer`

**SemanticScholar Extractors (`src/bioetl/application/pipelines/semanticscholar/extractors.py`)**
-   **Импорты**: `bioetl.domain.validation.validate_year_range`
-   **Экспортирует**: `extract_authors`, `extract_journal_info`, `extract_open_access_info`, `extract_external_ids`
-   **Пользователи**: `SemanticScholarPublicationTransformer`

### 1.2 PubMed Transformer

**PubMed Transformer (`src/bioetl/application/pipelines/pubmed/transformer.py`)**
-   **Наследует**: `BaseTransformer` (вместо `BasePublicationTransformer`)
-   **Дублирует**: Логику `_transform_impl` из `BasePublicationTransformer` (валидация ID, генерация `entity_id`, вычисление `content_hash`).
-   **Зависимости**: `xml.etree.ElementTree`, локальные экстракторы (`AuthorExtractor` и др.).

---

## 2. Верифицированные дублирования

### 2.1 Логика обработки авторов (`extract_authors`)

Оба провайдера получают списки авторов и извлекают имена. Логика форматирования и очистки дублируется или имеет незначительные отличия, которые можно параметризовать.

#### Текущее состояние

**OpenAlex:**
```python
def extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    # ... цикл по authorships ...
    # name = author.get("display_name")
    # ... strip() ...
    return authors
```

**SemanticScholar:**
```python
def extract_authors(authors: list[dict[str, Any]] | None) -> list[str]:
    # ... проверка на None ...
    # name = author.get("name")
    # ...
    return result
```

**PubMed (`AuthorExtractor`):**
Имеет более сложную логику (фамилия + инициалы), но результат тот же — список строк.

#### Предлагаемое решение
Создать `bioetl.domain.normalization.normalize_author_list` или `bioetl.application.pipelines.common.extractors.extract_author_names`, принимающую список словарей и ключ поля имени.

```python
# src/bioetl/application/pipelines/common/extractors.py

def extract_author_names(
    items: list[dict[str, Any]] | None,
    name_field: str = "name",
    nested_field: str | None = None
) -> list[str]:
    """Универсальный экстрактор имен авторов."""
    if not items:
        return []

    authors = []
    for item in items:
        target = item.get(nested_field) if nested_field else item
        if not isinstance(target, dict):
            continue

        name = target.get(name_field)
        if name and isinstance(name, str):
            authors.append(name.strip())

    return authors
```

### 2.2 Бойлерплейт трансформации в PubMed

`PubMedPublicationTransformer` реализует метод `_transform_impl` практически идентично `BasePublicationTransformer`, но с добавлением обработки `ET.ParseError`.

#### Текущее состояние
```python
# PubMedPublicationTransformer
async def _transform_impl(self, context, record, index):
    # ... try/except XML parsing ...
    # ... (Дублирование) вычисление entity_id ...
    # ... (Дублирование) вычисление content_hash ...
    # ... (Дублирование) создание сущности ...
```

#### Предлагаемое решение
Наследовать `BasePublicationTransformer`. Переопределить `_extract_business_data` для парсинга XML. `BasePublicationTransformer` ожидает, что `_extract_business_data` вернет dict.

**План миграции:**
1.  Адаптировать `PubMedPublicationTransformer` для наследования от `BasePublicationTransformer`.
2.  Реализовать `_extract_business_data` так, чтобы она инкапсулировала парсинг XML и возвращала словарь.
3.  Обработку `ET.ParseError` перенести внутрь `_extract_business_data` (возвращать пустой dict или выбрасывать специфичное исключение, которое `BasePublicationTransformer` может обработать, если добавить хук, либо оставить `try/except` в переопределенном `_transform_impl`, вызывая `super()._transform_impl` только после парсинга).
    *   *Уточнение*: `BasePublicationTransformer._transform_impl` вызывает `_extract_business_data` сразу. Лучше переопределить `_extract_business_data`, а ошибку парсинга обрабатывать внутри, возвращая `{"pmid": ...}` с пустыми полями или `None` (требует поддержки `None` в `BaseTransformer`).
    *   *Альтернатива*: Оставить `_transform_impl` в PubMed, но использовать миксины/утилиты для ID и хешей. Но лучше всё же использовать наследование, так как PubMed — это публикация.

---

## 3. Матрица приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет |
|---|-----------|--------|------------|-----|-----------|
| 1 | **PubMed -> BasePublicationTransformer** | High | Medium | ~50 | **P1** |
| 2 | **Common Extractors (Authors/Journal)** | Medium | Low | ~40 | **P2** |
| 3 | **Validation Wrappers (SemanticScholar)** | Low | Low | ~10 | **P3** |
| 4 | **Transformer `__init__` removal** | Low | Low | ~30 | **P3** |

---

## 4. План рефакторинга по фазам

### Фаза 1 (P1): Унификация пайплайна PubMed
**Цель**: Привести PubMed к единому архитектурному стилю с другими пайплайнами публикаций.
1.  Создать тесты-снэпшоты для текущего вывода `PubMedPublicationTransformer`.
2.  Изменить наследование на `BasePublicationTransformer`.
3.  Рефакторить `_extract_business_data` для возврата плоского словаря из XML.
4.  Проверить, что `ET.ParseError` корректно обрабатывается (возможно, через переопределение `_pre_extract_validation` для предварительного парсинга XML).

### Фаза 2 (P2): Выделение общих экстракторов
**Цель**: Убрать дублирование в `OpenAlex` и `SemanticScholar`.
1.  Создать `src/bioetl/application/pipelines/common/extractors.py`.
2.  Перенести туда универсальную логику (`extract_author_names`, `normalize_journal_info`).
3.  Обновить импорты в `openalex/transformer.py` и `semanticscholar/transformer.py`.
4.  Удалить локальные `extractors.py` или оставить там только специфичную логику.

### Фаза 3 (P3): Очистка технического долга
**Цель**: Микро-оптимизации.
1.  Удалить избыточные `__init__` в трансформерах ChEMBL (если они полностью повторяют родительский).
2.  Заменить обертки валидации в Semantic Scholar прямыми вызовами `domain.validation`.

## 5. Чеклист валидации

- [ ] `pytest tests/unit/application/pipelines/pubmed/` (без регрессии)
- [ ] `pytest tests/unit/application/pipelines/openalex/`
- [ ] `pytest tests/unit/application/pipelines/semanticscholar/`
- [ ] `mypy src/bioetl/ --strict`
- [ ] Coverage > 95% для новых общих модулей.
