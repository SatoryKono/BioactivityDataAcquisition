# /golden-regenerate

**Goal:** Регенерировать golden-наборы после одобренных изменений.


**Inputs**

- `--target PATH|GLOB` (required)
- `--approve` (required): жесткое подтверждение


**Steps**

1) Собрать новые артефакты
2) Сравнить с текущими golden
3) При `--approve` заменить и зафиксировать хеши


**Constraints**

- Без `--approve` никаких перезаписей


**Outputs**

- `golden/*` обновлены и задокументированы


**Exit criteria**

- История изменений отражена и проверена в CI

