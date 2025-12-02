# /migrate-cursorrules-to-mdc

**Goal:** Разложить legacy `.cursorrules` в тематические `.mdc` под `.cursor/rules/`.

**Steps**

1) Разбить монолит по темам: core/style/logging/io/schemas/cli/tests/docs/secrets/pipelines.
2) Создать файлы `.mdc` и заполнить фронт-маттер (description, globs/alwaysApply).
3) Проверить видимость правил в Cursor, затем удалить легаси-файл.


**Outputs**

- Набор `.mdc`
- Инструкции проверки и удаления легаси

