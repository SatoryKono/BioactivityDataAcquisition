# /validate-config

**Goal:** Провалидировать YAML-конфиги по JSONSchema/Pydantic и найти неиспользуемые ключи.


**Inputs**

- `--configs PATH|GLOB` (required)


**Steps**

1) Пройтись по конфигам, провалидировать схему
2) Сравнить ключи с реально используемыми в коде
3) Сформировать список проблем и автопатчи (если безопасно)


**Constraints**

- Только безопасные автопатчи
- Изменения документировать в CHANGELOG/DEPRECATIONS


**Outputs**

- `reports/config/validation.md`


**Exit criteria**

- Все конфиги валидны либо представлены конкретные нарушения

