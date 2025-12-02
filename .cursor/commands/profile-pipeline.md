# /profile-pipeline

**Goal:** Собрать профили CPU/IO и выявить узкие места пайплайна.


**Inputs**

- `pipeline_cmd` (required)
- `--duration SEC` (optional)


**Steps**

1) Запустить пайплайн под профилировщиком
2) Собрать flamegraph/trace
3) Выделить top-3 bottlenecks и рекомендации


**Constraints**

- Низкая нагрузка на прод при профилировании


**Outputs**

- `reports/profile/flamegraph.svg`
- `reports/profile/summary.md`


**Exit criteria**

- Указаны конкретные точки оптимизации и ожидаемый эффект

