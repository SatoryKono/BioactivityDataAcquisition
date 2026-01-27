# Пайплайн: ChEMBL Publication

**Имя пайплайна:** `chembl_publication`
**Провайдер:** `chembl`
**Сущность:** `publication`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о научных публикациях из API ChEMBL. Публикации связывают биоактивные данные с их первоисточниками (статьи, патенты).

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `document_chembl_id` | `str` | Уникальный ChEMBL ID публикации |
| `pubmed_id` | `int` | PubMed ID (если есть) |
| `doi` | `str` | Digital Object Identifier |
| `patent_id` | `str` | ID патента (если применимо) |

### Метаданные публикации

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | `str` | Название публикации |
| `authors` | `str` | Авторы |
| `journal` | `str` | Название журнала |
| `year` | `int` | Год публикации |
| `volume` | `str` | Том |
| `issue` | `str` | Выпуск |
| `first_page` | `str` | Первая страница |
| `last_page` | `str` | Последняя страница |

### Классификация

| Поле | Тип | Описание |
|------|-----|----------|
| `doc_type` | `str` | Тип публикации (PUBLICATION, PATENT) |
| `src_id` | `int` | ID источника данных |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/publication_transformer.py`

### Entity ID

```python
entity_id = f"chembl:{document_chembl_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`document_chembl_id`** — обязательное
2. **`doc_type`** — должен быть PUBLICATION или PATENT

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_publication

# С ограничением
bioetl run chembl_publication --limit 1000
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/publication.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/publication_transformer.py` |
| Пайплайн | `src/bioetl/application/pipelines/chembl/publication.py` |

---

*Последнее обновление: 2025-12-27*
