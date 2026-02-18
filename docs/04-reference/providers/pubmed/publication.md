# Пайплайн: PubMed Publication

**Имя пайплайна:** `pubmed_publication`
**Провайдер:** `pubmed`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает метаданные научных публикаций из API PubMed (NCBI E-utilities). Используется для обогащения биоактивных данных ссылками на первоисточники.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `pmid` | `str` | PubMed ID (уникальный) |
| `doi` | `str` | Digital Object Identifier |
| `pmc_id` | `str` | PubMed Central ID |

### Метаданные статьи

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название статьи |
| `abstract` | `str` | Аннотация |
| `authors` | `list[str]` | Список авторов |
| `journal_title` | `str` | Название журнала |
| `publication_date` | `str` | Дата публикации |
| `volume` | `str` | Том журнала |
| `issue` | `str` | Выпуск |
| `pages` | `str` | Страницы |

### Авторы и аффилиации

| Поле | Тип | Описание |
|------|-----|----------|
| `author_keys` | `str \| None` | Нормализованные ключи авторов в формате `Surname_F`, разделённые `\|` |
| `affiliation_list` | `str \| None` | JSON-массив уникальных аффилиаций |
| `authors_with_affiliations` | `str \| None` | JSON-массив: автор → аффилиации |
| `affiliation_structured` | `str \| None` | JSON-массив с ROR/GRID идентификаторами |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `publication_class` | `str` | Класс публикации: EXP, REV, PEER |
| `publication_subclass` | `str \| None` | Подкласс (L2): ~16 групп |
| `publication_type_unified` | `str \| None` | Унифицированный тип (L3): 214 значений |
| `mesh_terms` | `list[str]` | MeSH термины |
| `keywords` | `list[str]` | Ключевые слова |
| `publication_types` | `list[str]` | Типы публикации |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py`

### Парсинг XML

PubMed API возвращает данные в XML формате. Трансформер использует `xml_utils.py` для парсинга.

### Entity ID

```python
entity_id = f"pubmed:{pmid}"
```

---

## 4. Особенности

### Rate Limiting

PubMed API имеет строгие лимиты:
- Без API key: 3 запроса/сек
- С API key: 10 запросов/сек

### Рекомендации

1. Используйте API key для production
2. Устанавливайте `limit` при тестировании
3. Используйте `--dry-run` для проверки конфигурации

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run pubmed_publication

# С ограничением
bioetl run pubmed_publication --limit 100

# Полная перезагрузка
bioetl run pubmed_publication --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/pubmed/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/pubmed/transformer.py` |
| XML Utils | `src/bioetl/application/pipelines/pubmed/xml_utils.py` |

---

*Последнее обновление: 2026-02-16*
