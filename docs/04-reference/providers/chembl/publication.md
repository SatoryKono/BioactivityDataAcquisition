# Пайплайн: ChEMBL Publication

**Имя пайплайна:** `chembl_publication`
**Провайдер:** `chembl`
**Сущность:** `publication`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о научных публикациях из API ChEMBL. Публикации связывают биоактивные данные с их первоисточниками (статьи, патенты).

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `publication_id` | `str` | Уникальный ChEMBL ID публикации |
| `publication_pmid` | `str` | PubMed ID (если есть) |
| `publication_doi` | `str` | Digital Object Identifier |
| `publication_pmc_id` | `str` | PubMed Central ID (если есть) |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название публикации |
| `authors` | `str` | Авторы |
| `journal` | `str` | Название журнала |
| `publication_year` | `int` | Год публикации |
| `volume` | `str` | Том |
| `issue` | `str` | Выпуск |
| `page_first` | `str` | Первая страница |
| `page_last` | `str` | Последняя страница |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `publication_type` | `str` | Тип публикации (`journal-article`, `book`, `dataset`, `patent`) |
| `src_id` | `int` | ID источника данных |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{publication_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`publication_id`** — обязательное
2. **`publication_type`** — должен быть одним из канонических типов (`journal-article`, `book`, `dataset`, `patent`)

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_publication

# С ограничением
bioetl run --pipeline chembl_publication --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/publication.py` |

---

*Последнее обновление: 2026-03-03*
