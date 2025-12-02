# /benchmark-pagination

**Goal:** Сравнить стратегии пагинации (offset/cursor/идемпотентные ключи) по пропускной способности и p95.


**Inputs**

- `--source NAME` (required): источник
- `--limit N` (optional)
- `--runs M` (optional): количество повторов


**Steps**

1) Запуск каждой стратегии на одном и том же подмножестве
2) Сбор p95/throughput/error rate
3) Сформировать рекомендацию по умолчанию


**Constraints**

- Стабильный seed, единые окна времени
- Повторяемость измерений


**Outputs**

- `reports/benchmark/pagination_<source>.md`
- `reports/benchmark/pagination_<source>.json`


**Exit criteria**

- Есть сводка p50/p95 и рекомендация

