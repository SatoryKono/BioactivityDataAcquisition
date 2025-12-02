# /data-dictionary-sync

**Goal:** Синхронизировать словарь данных (колонки, типы, nullable, описания) из схем/артефактов в docs/.


**Inputs**

- `--artifacts PATH|GLOB` (optional)
- `--schemas PATH|GLOB` (optional)


**Steps**

1) Извлечь метаданные колонок
2) Собрать таблицы с описаниями и примерами
3) Обновить docs/ и README-ссылки


**Constraints**

- Стандартизированный формат описаний


**Outputs**

- `docs/data-dictionary.md`


**Exit criteria**

- Документ сгенерирован, не нарушены ссылки

