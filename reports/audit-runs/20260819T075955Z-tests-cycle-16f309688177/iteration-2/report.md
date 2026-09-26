# Итерация 2 — test-governance budgets

`surface_score: 1/3`.

Collector drift выявил четыре markerless functions, oversized Grafana test regression и repo-backed tests в неправильном lane. Findings `TEST-SYS-002` и `TEST-SYS-011` закрыты без роста budgets: markers добавлены, test split уменьшил исходный файл до 1680 строк, файловые контракты вынесены в `tests/unit/repo_backed/`.
