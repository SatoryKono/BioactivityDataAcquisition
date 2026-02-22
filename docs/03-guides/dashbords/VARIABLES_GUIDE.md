# Variables для дашбордов v2

## ✅ Добавлены переменные фильтрации

Все три дашборда v2 теперь имеют открытые переменные для фильтрации:

| Переменная | Определение | Тип | Multi | Include All |
|-----------|-----------|------|-------|-------------|
| **pipeline** | `label_values(bioetl_records_processed_total, pipeline)` | query | ✅ | ✅ |
| **run_id** | `label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_id)` | query | ✅ | ✅ |

---

## 📊 Структура переменных

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

### Run ID Variable

```
Name: run_id
Type: Query (Prometheus)
Definition: label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_id)
Multi: YES (можно выбрать несколько)
Include All: YES (опция "All")
Refresh: On dashboard load (1)
Sort: Alphabetical (1)
Depends on: $pipeline
```

**Возвращает:** Все run_id'ы для выбранного pipeline

---

## 🎯 Как это работает

### Работа фильтрации

1. **Пользователь выбирает Pipeline**
   - Например: `uniprot`

2. **Run ID variable обновляется**
   - PromQL: `label_values(bioetl_records_processed_total{pipeline=~"uniprot"}, run_id)`
   - Возвращает только run_id'ы для uniprot

3. **Все графики используют оба фильтра**
   - PromQL в панелях: `bioetl_records_processed_total{pipeline=~"$pipeline", run_id=~"$run_id"}`

4. **Дашборд обновляется**
   - Графики показывают только выбранные данные

---

## 📈 Примеры использования

### Пример 1: Выбрать конкретный pipeline и run

```
Pipeline: uniprot
Run ID: run-492157

Результат: Дашборд показывает только данные для uniprot:run-492157
```

### Пример 2: Выбрать все run'ы одного pipeline

```
Pipeline: pubmed
Run ID: All

Результат: Дашборд показывает все run'ы PubMed (объединенные графики)
```

### Пример 3: Выбрать все pipeline'ы

```
Pipeline: All
Run ID: All

Результат: Дашборд показывает все данные со всех pipeline'ов
```

### Пример 4: Сравнить несколько pipeline'ов

```
Pipeline: uniprot, pubmed, pubchem
Run ID: run-492157

Результат: Дашборд показывает данные для трех pipeline'ов в одном run
```

---

## 🔧 PromQL запросы в панелях

Графики используют переменные в PromQL:

**Было (без фильтрации):**
```promql
bioetl_records_processed_total{run_id=~"$latest_run_id"}
```

**Стало (с фильтрацией):**
```promql
bioetl_records_processed_total{pipeline=~"$pipeline", run_id=~"$run_id"}
```

---

## 📊 Дашборды с переменными

### BioETL Data Quality v2
- URL: http://localhost:3000/d/bioetl-dq-v2
- Переменные: Pipeline, Run ID
- Показывает: Data Flow, Quality Score, Source/Clean Records

### BioETL Overview v2
- URL: http://localhost:3000/d/bioetl-overview-v2
- Переменные: Pipeline, Run ID
- Показывает: Processing Pipeline, Stage Distribution, Quality

### BioETL Provider Health v2
- URL: http://localhost:3000/d/bioetl-provider-health-v2
- Переменные: Pipeline, Run ID
- Показывает: Response Time, Error Rate, Provider Latencies

---

## 💡 Советы

### Совет 1: Быстрая фильтрация
```
1. Выберите Pipeline из dropdown
2. Run ID автоматически обновится
3. Выберите нужный Run ID
4. Графики обновятся
```

### Совет 2: Сравнение данных
```
1. Откройте дашборд в двух tabs
2. Tab 1: Pipeline=uniprot, Run ID=run-492157
3. Tab 2: Pipeline=uniprot, Run ID=run-492156
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
Run ID variable
    ↓ (фильтр)
Все графики и панели
```

При изменении Pipeline → Run ID автоматически обновляется
При изменении Run ID → Все графики обновляются

---

## ✨ Достоинства

✅ **Динамическая фильтрация** — выбирайте нужные данные  
✅ **Зависимые переменные** — Run ID фильтруется по Pipeline  
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

update_dashboards_vars.py (скрипт для обновления)
```

---

**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready
