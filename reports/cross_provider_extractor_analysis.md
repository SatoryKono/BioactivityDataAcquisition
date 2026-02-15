# Cross-provider анализ `extract_*` функций (publication providers)

## Scope

Сравнение реализаций по строкам матрицы для function-based провайдеров (`openalex`, `semanticscholar`, `crossref`) + комментарий по `pubmed` class-based подходу.

Классы:

- **IDENTICAL** — тела совпадают (допускаются только разные имена переменных)
- **SIMILAR_STRUCTURE** — общий алгоритм совпадает, но различаются ключи/вложенность/нормализация
- **DIFFERENT** — различается логика, входная модель или выходной контракт

______________________________________________________________________

## 1) `extract_authors`

### Реализации

- **OpenAlex**: принимает `authorships: list[dict]`, идёт по `authorship['author']['display_name']`, trim, пропускает не-dict/пустые.
- **Semantic Scholar**: принимает `authors: list[dict] | None`, берёт `author['name']`, trim, фильтрует пустые.
- **CrossRef**: принимает весь `publication: dict`, идёт по `publication['author']`, собирает имя из `given + family`, fallback на `family`, `given`, затем org `name`.

### Классификация

- **OpenAlex ↔ Semantic Scholar**: **SIMILAR_STRUCTURE**
- **Любая пара с CrossRef**: **DIFFERENT**

### Почему

- OA и S2 используют один и тот же шаблон «итерация по списку → безопасный доступ → trim → append», но разные пути к имени (nested vs flat).
- CrossRef не просто достаёт поле, а **конструирует** имя из нескольких атрибутов и поддерживает организационных авторов.

### Потенциал шаблона

- Можно вынести параметризуемый helper в `common/extractors.py` (по сути уже есть `extract_author_names`) для OA/S2.
- Для CrossRef — оставить provider-specific (сложная сборка имени).

______________________________________________________________________

## 2) `extract_author_orcids`

### Реализации

- **OpenAlex**: вход `authorships`, берёт `author.orcid` (fallback `author.ormolecule_id`), нормализует URL→ID, валидирует regex ORCID, сохраняет позиционность через `""` placeholder.
- **Semantic Scholar**: вход `authors | None`, берёт `author.externalIds.ORCID`, trim, сохраняет позиционность через `""` placeholder.
- **CrossRef**: вход `publication`, берёт `author.ORCID`, нормализует префиксы URL, базовая валидация формата, **авторов без ORCID не добавляет** (без placeholder).

### Классификация

- **OpenAlex ↔ Semantic Scholar**: **SIMILAR_STRUCTURE**
- **Любая пара с CrossRef**: **DIFFERENT**

### Почему

- OA/S2: одинаковая идея «1 выход на 1 автора» + placeholder `""`.
- CrossRef: другой выходной контракт (сжатый список только валидных ORCID), и другой вход (весь publication).

### Потенциал шаблона

- Реализуем общий шаблон с параметрами:
  - путь к ORCID,
  - функция нормализации,
  - режим `preserve_positions: bool`.
- Тогда OA/S2 используют `preserve_positions=True`, CrossRef — `False`.

______________________________________________________________________

## 3) `extract_affiliations`

### Реализации

- **OpenAlex**: из `authorships[*].institutions[*].display_name`, уникализация через set, sort.
- **Semantic Scholar**: из `authors[*].affiliations[*]` (строки), уникализация через set, sort.
- **CrossRef**: из `publication['author'][*].affiliation[*]`, где affiliation элемент может быть dict(`name`) или str; уникализация + sort.

### Классификация

- **OpenAlex ↔ Semantic Scholar**: **SIMILAR_STRUCTURE**
- **Пары с CrossRef**: **SIMILAR_STRUCTURE** (не DIFFERENT)

### Почему

Алгоритм во всех трёх случаях один и тот же: пройти вложенный список, безопасно извлечь значение, очистить, добавить в `set`, вернуть `sorted(list)`.
Отличия только в схеме ответа API и типах узлов (`dict`/`str`).

### Потенциал шаблона

- Высокий: generic helper уровня `extract_unique_strings_from_nested(...)` c параметрами:
  - путь до outer list,
  - путь до inner list,
  - extractor элемента inner-list (dict key/identity),
  - `normalize=str.strip`.

______________________________________________________________________

## 4) `extract_journal_info`

### Реализации

- **OpenAlex**: вход `primary_location`, читает `source.display_name`, `source.issn_l`, `source.host_organization_name`.
- **Semantic Scholar**: вход (`journal`, `venue`), плюс парсинг `volume/issue` и `pages` через отдельные функции (`parse_volume_issue`, `parse_page_range`), добавляет `page_first/page_last`.
- **CrossRef**: вход `publication`, берёт `container-title` (первый элемент), `ISSN`, `publisher`.

### Классификация

- **Все пары**: **DIFFERENT**

### Почему

Не только разные ключи, но и разный **контракт результата**:

- OA: 3 поля,
- CR: 3 поля (другое представление ISSN),
- S2: расширенный набор с volume/issue/page parsing.

### Потенциал шаблона

- Общий helper возможен только низкоуровневый (safe-get / first-string), но не единый high-level extractor.

______________________________________________________________________

## 5) `extract_external_ids`

### Реализации

- **OpenAlex**: вход `ids` dict, нормализует PMID через VO `PubMedId`, PMCID из `pmcid|pmmolecule_id`, MAG в строку; возвращает фиксированный dict ключей.
- **Semantic Scholar**: вход `external_ids` dict, прямой маппинг ключей (`DOI`, `PubMed`, `CorpusId`, `MAG`, ...), возврат словаря без валидации/VO.
- **CrossRef**: эквивалентной функции в текущем модуле нет.
- **PubMed (class-based)**: роль external-id extraction распределена в `IdentifierExtractor` (`extract_doi`, `extract_pmc_id`, `extract_elocation_ids`, `extract_pii`, `extract_mid`, `extract_publisher_id`) по XML.

### Классификация

- **OpenAlex ↔ Semantic Scholar**: **SIMILAR_STRUCTURE**
- **С участием CrossRef**: **DIFFERENT** (функция отсутствует)
- **С участием PubMed**: **DIFFERENT** (класс/методы + XML)

### Потенциал шаблона

- Для OA/S2 можно вынести mapping-driven extractor в `common`:
  - map source-key → target-key,
  - optional normalizer per key (VO/strip/cast),
  - fallback chains для alias-ключей.

______________________________________________________________________

## 6) `extract_open_access_info`

### Реализации

- **OpenAlex**: вход `open_access` dict, возвращает только `is_oa`, `oa_status` (pass-through).
- **Semantic Scholar**: вход (`is_open_access`, `open_access_pdf`), извлекает `url`, нормализует `status`, семантически различает `False` и `None` и задаёт `closed` только при `False`.
- **CrossRef/PubMed**: одноимённой функции в матрице нет.

### Классификация

- **OpenAlex ↔ Semantic Scholar**: **DIFFERENT**

### Почему

S2 содержит дополнительную бизнес-логику нормализации и семантики статуса + дополнительное поле `url`; OA — простой перенос 2 полей.

### Потенциал шаблона

- Ограниченный: можно выделить маленький helper `normalize_oa_status`, но не общий high-level extractor.

______________________________________________________________________

## 7) `extract_author_ormolecule_ids` (legacy alias)

### Реализации

- **OpenAlex**: alias → `extract_author_orcids(authorships)`.
- **Semantic Scholar**: alias → `extract_author_orcids(authors)`.
- **CrossRef**: alias → `extract_author_orcids(publication)`.

### Классификация

- **IDENTICAL** (по сути тела одинаковые: single-line delegating wrapper).

### Почему

Логика функции не меняется между провайдерами — это просто совместимость legacy имени.

### Потенциал шаблона

- Уже фактически шаблон: единый паттерн alias-delegate.

______________________________________________________________________

## Итоговая сводка по матрице

| Функция                         | Итог                                                   |
| ------------------------------- | ------------------------------------------------------ |
| `extract_authors`               | SIMILAR_STRUCTURE (OA/S2), DIFFERENT с CrossRef        |
| `extract_author_orcids`         | SIMILAR_STRUCTURE (OA/S2), DIFFERENT с CrossRef        |
| `extract_affiliations`          | SIMILAR_STRUCTURE (все 3)                              |
| `extract_journal_info`          | DIFFERENT                                              |
| `extract_external_ids`          | SIMILAR_STRUCTURE (OA/S2), DIFFERENT с CrossRef/PubMed |
| `extract_open_access_info`      | DIFFERENT                                              |
| `extract_author_ormolecule_ids` | IDENTICAL                                              |

______________________________________________________________________

## Рекомендации по extraction шаблонам в `common/extractors.py`

### Что выносить сейчас (high value, low risk)

1. **Generic list-of-items string extractor** для OA/S2 author names (частично уже покрыто `extract_author_names`).
1. **Generic unique nested string extractor** для affiliations (поддержка inner item: dict или str).
1. **Mapping-driven external ID extractor** с per-field normalizer + fallback keys.
1. **Generic ORCID extractor** с переключателем `preserve_positions`.

### Что не стоит агрессивно унифицировать

1. **CrossRef `extract_authors`** (сборка имени + org fallback).
1. **`extract_journal_info`** (слишком разный контракт и enrichment).
1. **`extract_open_access_info`** (разная бизнес-семантика статусов).

______________________________________________________________________

## PubMed: почему class-based отличается и насколько совместим с общим шаблоном

### Ключевые отличия

- Входные данные: `xml.etree.ElementTree.Element`, а не `dict`.
- Структура извлечения: XPath-поиск (`find/findall`) и атрибуты XML (`IdType`, `EIdType`, `PubStatus`).
- Архитектура: `BaseFieldExtractor` (Template Method) с фазами `extract()` → `normalize()` + classmethod API.

### Может ли использовать общий шаблон?

- **Прямо** использовать dict-oriented helpers из `common/extractors.py` — **нет**, из-за другой модели данных.
- **Концептуально** может разделить идеи:
  - параметризуемые mapping-и (`IdType -> field` уже реализован в `IdentifierExtractor.extract_all_article_ids`),
  - общие нормализаторы строк/ID,
  - policy для fallback порядка.
- Оптимальный путь: отдельный XML-oriented `common` слой (например, `common/xml_extractors.py`) с аналогичными паттернами, но не смешивать с dict-helper API.

______________________________________________________________________

## Приоритеты рефакторинга (без изменения поведения)

1. Вынести общий extractor для affiliations (все 3 провайдера схожи).
1. Вынести ORCID helper с configurable policy (`preserve_positions`).
1. Вынести mapping-driven extractor для external IDs (OA/S2).
1. Оставить provider-specific `journal_info`, `open_access_info`, CrossRef name-composition.
