# File plan


| Файл | Назначение изменения |
| --- | --- |
| `grafana/dashboards/bioetl-control-plane-v1.json` | После проверки runtime/source parity применить перечисленные выше изменения панелей; использовать существующий генератор/владеющий helper, если он формирует этот JSON. |
| `tests/integration/test_dashboard_operator_readability.py` | Проверить читаемость подписей/времени и соответствующий регрессионный сценарий. |
| `tests/integration/test_dashboard_first_window_noscroll.py` | Сохранить обязательный first-window no-scroll контракт; не ослаблять budgets. |
| `tests/integration/test_dashboard_visual_semantics.py` | Проверить применимые правила отображения состояния; для семантического изменения добавить различающие случаи. |


# Title
[P2][Grafana][VIS-20260908] Сделать replay anchors читаемыми и сократить повторную identity evidence
