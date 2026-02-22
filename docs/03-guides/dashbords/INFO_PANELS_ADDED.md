# Info Panels (Pipeline, Run ID, Timestamp) добавлены!

## ✅ Что было сделано

Добавлены три информационные панели в верхнюю часть каждого дашборда v2:

### 1. Pipeline Panel
```
Показывает: Текущий выбранный pipeline
PromQL: max(label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, pipeline))
Зависит от: переменной $pipeline
```

### 2. Run ID Panel
```
Показывает: Текущий выбранный run_id
PromQL: max(label_values(bioetl_records_processed_total{pipeline=~"$pipeline", run_id=~"$run_id"}, run_id))
Зависит от: переменных $pipeline и $run_id
```

### 3. Execution Timestamp Panel
```
Показывает: Время запуска (Unix timestamp)
PromQL: max(bioetl_run_start_timestamp{pipeline=~"$pipeline", run_id=~"$run_id"})
Зависит от: переменных $pipeline и $run_id
```

---

## 📊 Структура верхней строки дашборда

```
┌─────────────────────┬──────────────────┬──────────────────────────────┐
│  Pipeline (6 cols)  │  Run ID (6 cols) │  Timestamp (12 cols)         │
├─────────────────────┴──────────────────┴──────────────────────────────┤
│                                                                         │
│                      Основные графики и метрики                        │
│                    (24 cols - во всю ширину)                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Обновленные дашборды

| Дашборд | Файл | Статус |
|---------|------|--------|
| BioETL Data Quality v2 | bioetl-dq-v2.json | ✅ Updated |
| BioETL Overview v2 | bioetl-overview-v2.json | ✅ Updated |
| BioETL Provider Health v2 | bioetl-provider-health-v2.json | ✅ Updated |

---

## 📈 Как работают info panels

### При выборе Pipeline = "uniprot"

```
Pipeline Panel: uniprot
Run ID Panel: <обновляется список run_id'ов для uniprot>
Timestamp Panel: <показывает время для выбранного run_id>
```

### При выборе Pipeline = "All"

```
Pipeline Panel: All (или последний используемый)
Run ID Panel: <показывает все run_id'ы>
Timestamp Panel: <показывает максимальное время>
```

### При выборе Run ID

```
Pipeline Panel: <остаётся неизменным>
Run ID Panel: <выбранный run_id>
Timestamp Panel: <обновляется время для этого run_id>
```

---

## 🔗 Откройте дашборды

- http://localhost:3000/d/bioetl-dq-v2
- http://localhost:3000/d/bioetl-overview-v2
- http://localhost:3000/d/bioetl-provider-health-v2

---

## ✨ Достоинства

✅ **Информация в реальном времени** — всегда видно, какие фильтры выбраны  
✅ **Динамическое обновление** — при изменении фильтров обновляется всё  
✅ **Консистентность** — все три панели работают вместе  
✅ **Удобство использования** — не нужно глядеть на селекторы переменных  

---

## 📝 Файлы, которые изменились

```
grafana/dashboards/
├── bioetl-dq-v2.json (updated - добавлены info panels)
├── bioetl-overview-v2.json (updated - добавлены info panels)
└── bioetl-provider-health-v2.json (updated - добавлены info panels)

add_info_panels.py (скрипт для добавления панелей)
```

---

## 🚀 Итоговая структура дашбордов v2

**Верхняя строка (3 height):**
- Pipeline info (6 cols)
- Run ID info (6 cols)
- Execution Timestamp info (12 cols)

**Фильтры (ниже info panels):**
- Pipeline selector (dropdown)
- Run ID selector (dropdown)

**Содержимое (графики и метрики):**
- Bronze/Silver/Gold Records
- Quality Score
- Processing pipelines
- Error rates
- Provider health
- И другие метрики...

---

**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready

**Все три дашборда v2 теперь полностью готовы к использованию!** 🎉
