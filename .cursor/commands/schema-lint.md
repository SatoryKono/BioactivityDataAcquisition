# /schema-lint

**Goal:** Проверить схемы на консистентность (nullable, enum, диапазоны, типы).


**Inputs**

- `--schemas PATH|GLOB` (required)


**Steps**

1) Считать схемы
2) Проверить правила и пересечения
3) Сформировать список ошибок и предупреждений


**Constraints**

- Никаких разрывов контрактов без миграций


**Outputs**

- `reports/schema/lint.md`


**Exit criteria**

- Ошибки устранены или задокументированы

