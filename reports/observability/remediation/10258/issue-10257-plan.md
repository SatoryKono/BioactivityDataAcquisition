# File plan


| Файл | Назначение изменения |
| --- | --- |
| `grafana/dashboards/bioetl-control-plane-v1.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-overview-v2.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-runtime.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-provider-health-v2.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-dq-v2.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-incident-v1.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `grafana/dashboards/bioetl-run-explorer-v1.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `scripts/ops/observability/grafana/render_nav_bus.py` | Изменять общую навигацию через канонический генератор; затем синхронно обновить семь dashboard JSON. |
| `scripts/ops/observability/grafana/dashboard_context_links.py` | Сохранить сериализацию фильтров и времени; явно обозначить целевой dashboard/сброс scope, если потребуется. |
| `docs/03-guides/dashboards/design-system.md` | Уточнить единый шаблон статусов и навигации после принятия решения; при изменении локальных ссылок обновить documentation inventory. |
| `tests/integration/test_dashboard_operator_readability.py` | Проверить читаемость подписей/времени и соответствующий регрессионный сценарий. |
| `tests/integration/test_dashboard_first_window_noscroll.py` | Сохранить обязательный first-window no-scroll контракт; не ослаблять budgets. |
| `tests/integration/test_dashboard_visual_semantics.py` | Проверить применимые правила отображения состояния; для семантического изменения добавить различающие случаи. |


# Title
[P3][Grafana][VIS-20260908] Унифицировать оформление статусов и интервалы навигации
