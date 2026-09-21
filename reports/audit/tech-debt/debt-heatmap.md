# Debt heatmap

| Зона | P1 | P2 | P3 |
| --- | --- | --- | --- |
| architecture (memory/tooling) | TD-001 | TD-003, TD-004 | |
| dependencies | TD-002 | | |
| code (src/bioetl) | | | TD-005, TD-008 |
| security/tests | | | TD-006, TD-007, TD-009 |

Горячие точки: `src/memory/graph/sync_pkg/` (размер), allowlist циклов (30), холдбэки мажоров.
Холодные зоны: `src/bioetl` (0 TODO, топ-модуль 441 строка), конфиги (дрейф 0).
