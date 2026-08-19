# Итерация 3 — unit regression path

`surface_score: 1/3`.

Канонический `unit-fast` стабильно падал на устаревшем ожидании CLI. Runtime уже корректно применял `source_scope=current_run`; test ожидал прежний fail-closed contract. `TEST-SYS-003` исправлен проверкой фактически переданного `WorkflowConfig`.
