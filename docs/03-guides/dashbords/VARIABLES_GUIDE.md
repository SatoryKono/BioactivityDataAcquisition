# Variables для дашбордов v2

## ✅ Переменные фильтрации

### Data Quality v2 / Overview v2 / Simple

| Переменная | Определение | Тип | Multi | Include All | Hidden |
|-----------|-----------|------|-------|-------------|--------|
| **pipeline** | `label_values(bioetl_records_processed_total, pipeline)` | query | ✅ | ✅ | Нет |
| **run_type** | `label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)` | query | ✅ | ✅ | Нет |
| **execution** | (зависит от pipeline) | query | ❌ | ❌ | ✅ (hide: 2) |

### Provider Health v2

| Переменная | Определение | Тип | Multi | Include All | Hidden |
|-----------|-----------|------|-------|-------------|--------|
| **provider** | `label_values(bioetl_health_check_latency_ms_bucket, provider)` | query | ✅ | ✅ | Нет |

---

## 📊 Описание переменных

### Pipeline Variable

```
Name: pipeline
Type: Query (Prometheus)
Definition: label_values(bioetl_records_processed_total, pipeline)
Multi: YES (можно выбрать несколько)
Include All: YES (опция "All")
Refresh: On dashboard load (1)
Sort: Alphabetical (1)
```

**Возвращает:** uniprot, pubmed, pubchem, chembl

### Run Type Variable

```
Name: run_type
Type: Query (Prometheus)
Definition: label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)
Multi: YES (можно выбрать несколько)
Include All: YES (опция "All")
Refresh: On dashboard load (1)
Sort: Alphabetical (1)
Depends on: $pipeline
```

**Возвращает:** incremental, backfill, rebuild

### Execution Variable (скрытая)

```
Name: execution
Type: Query (Prometheus)
Hide: 2 (полностью скрыта)
Multi: NO (single value)
Refresh: On dashboard load (1)
Depends on: $pipeline
```

**Назначение:** Внутренняя переменная для фильтрации по конкретному запуску

### Provider Variable (только Provider Health v2)

```
Name: provider
Type: Query (Prometheus)
Definition: label_values(bioetl_health_check_latency_ms_bucket, provider)
Multi: YES (можно выбрать несколько)
Include All: YES (опция "All")
```

**Возвращает:** uniprot, pubmed, pubchem, chembl

---

## 🎯 Как это работает

### Работа фильтрации (DQ v2 / Overview v2)

1. **Пользователь выбирает Pipeline**
   - Например: `uniprot`

2. **Run Type variable обновляется**
   - PromQL: `label_values(bioetl_records_processed_total{pipeline=~"uniprot"}, run_type)`
   - Возвращает только run_type'ы для uniprot

3. **Все графики используют оба фильтра**
   - PromQL в панелях: `bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}`

4. **Дашборд обновляется**
   - Графики показывают только выбранные данные

### Работа фильтрации (Provider Health v2)

1. **Пользователь выбирает Provider**
   - Например: `chembl`

2. **Все графики фильтруются по provider**
   - PromQL: `histogram_quantile(0.95, bioetl_health_check_latency_ms_bucket{provider=~"$provider"})`

---

## 📈 Примеры использования

### Пример 1: Выбрать конкретный pipeline и run type

```
Pipeline: uniprot
Run Type: incremental

Результат: Дашборд показывает только incremental данные для uniprot
```

### Пример 2: Выбрать все run type'ы одного pipeline

```
Pipeline: pubmed
Run Type: All

Результат: Дашборд показывает все типы запусков PubMed (объединенные графики)
```

### Пример 3: Выбрать все pipeline'ы

```
Pipeline: All
Run Type: All

Результат: Дашборд показывает все данные со всех pipeline'ов
```

### Пример 4: Сравнить несколько pipeline'ов

```
Pipeline: uniprot, pubmed, pubchem
Run Type: incremental

Результат: Дашборд показывает incremental данные для трех pipeline'ов
```

---

## 🔧 PromQL запросы в панелях

Графики используют переменные в PromQL:

**PromQL с фильтрацией:**
```promql
bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}
```

---

## 📊 Дашборды с переменными

### BioETL Data Quality v2
- URL: http://localhost:3000/d/bioetl-dq-v2
- Переменные: Pipeline, Run Type, Execution (hidden)
- Показывает: Data Flow, Quality Score, Source/Clean Records

### BioETL Overview v2
- URL: http://localhost:3000/d/bioetl-overview-v2
- Переменные: Pipeline, Run Type, Execution (hidden)
- Показывает: Processing Pipeline, Stage Distribution, Quality

### BioETL Provider Health v2
- URL: http://localhost:3000/d/bioetl-provider-health-v2
- Переменные: Provider
- Показывает: Response Time, Health Check Status, Provider Latencies

---

## 💡 Советы

### Совет 1: Быстрая фильтрация
```
1. Выберите Pipeline из dropdown
2. Run Type автоматически обновится
3. Выберите нужный Run Type
4. Графики обновятся
```

### Совет 2: Сравнение данных
```
1. Откройте дашборд в двух tabs
2. Tab 1: Pipeline=uniprot, Run Type=incremental
3. Tab 2: Pipeline=uniprot, Run Type=backfill
4. Сравнивайте рядом
```

### Совет 3: Экспорт с фильтрами
```
1. Выберите нужные фильтры
2. Dashboard → Share → Copy dashboard URL
3. URL сохранит ваши фильтры
4. Поделитесь с коллегой
```

---

## 🎓 Зависимости переменных

```
Pipeline variable
    ↓ (фильтр)
Run Type variable
    ↓ (фильтр)
Все графики и панели
```

При изменении Pipeline → Run Type автоматически обновляется
При изменении Run Type → Все графики обновляются

---

## ✨ Достоинства

✅ **Динамическая фильтрация** — выбирайте нужные данные  
✅ **Зависимые переменные** — Run Type фильтруется по Pipeline  
✅ **Multi-select** — можно выбрать несколько значений  
✅ **Include All** — быстро выбрать все  
✅ **URL сохраняет фильтры** — можно поделиться ссылкой  

---

## 📄 Файлы, которые изменились

```
grafana/dashboards/
├── bioetl-dq-v2.json (updated)
├── bioetl-overview-v2.json (updated)
└── bioetl-provider-health-v2.json (updated)

```

---

**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready
