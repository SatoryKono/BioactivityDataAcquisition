# GitHub Billing Financial Analysis
## Ожидание данных
Эта документация описывает процесс сбора и анализа финансовой информации (GitHub Billing) согласно issue #12351.
В настоящее время выгрузка ожидается от участника с соответствующими правами (`billing-доступ`).
## Периоды анализа
- Baseline: `2026-09-01..2026-09-30` (ОЖИДАЕТСЯ)
- After-период: `2026-10-01..2026-10-19` (ОЖИДАЕТСЯ)
Данные периоды должны быть выгружены без изменений фильтров или параметров тарификации (Copilot/LFS).
## Схема выгрузки
Для атрибуции по workflow нужен Detailed usage report из веб-интерфейса GitHub.
Сводный отчёт (Summarized usage report) не содержит `workflow_path`, и валидатор его отклоняет.
Столбец `workflow_path` обязателен; в отдельной строке он может быть пустым.
Выгрузка должна представлять собой CSV-файл с обязательными полями:
- `date`
- `product`
- `sku`
- `repository`
- `workflow_path`
- `quantity`
- `unit_type`
- `gross_amount`
- `discount_amount`
- `net_amount`
- `currency`
`currency` обязателен в каждой строке. Отсутствие столбца не подставляется как USD.
Денежные поля `gross_amount`, `discount_amount` и `net_amount` читаются как `Decimal`.
`float` для этих полей отклоняется.
Для каждой строки должно выполняться `gross_amount - discount_amount = net_amount`.
Повторяющиеся имена столбцов и лишние ячейки в строке отклоняются.
Пустой файл и CSV только с заголовком отклоняются: это не нулевые расходы.
`calculate_totals` и `extract_workflow_attribution` суммируют строки только когда валюта
каждой строки совпадает с явной валютой отчёта.
Расходы Actions на runner попадают в `actions_compute`, если SKU содержит `compute`
или официальное имя runner (`Actions Linux`, `Actions Windows`, `Actions macOS`).
SKU со `storage` в эту категорию не входит.
`Actions storage` и `Packages storage` попадают в `shared_storage`.
`Actions cache storage` и `Actions custom image storage` в этот пул не входят.
Атрибуция workflow использует пару `(repository, workflow_path)`. Одинаковый путь
workflow в разных репозиториях учитывается раздельно. Пустой `repository` не
смешивается с названным репозиторием.
Для программного валидатора и обработки этих данных смотрите:
- `scripts/engineering/finances/github_billing_schema.py`
- `scripts/engineering/finances/github_billing_validator.py`
- `scripts/engineering/finances/github_billing_pipeline.py`
## Конфиденциальность
Финансовые строки, персональные сведения об оплате и сама выгрузка НЕ ДОЛЖНЫ быть опубликованы в public issue, PR, общедоступном artifact или вместе с техническим отчётом.
Разрешена публикация только согласованной обезличенной сводки/статуса.
