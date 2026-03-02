# Info Panels (Pipeline, Run Type, Timestamp) добавлены!

## ✅ Что было сделано

Добавлены информационные панели в верхнюю часть каждого дашборда v2:

### DQ v2 / Overview v2 — 3 info-панели:

#### 1. Pipeline Panel
```
Показывает: Текущий выбранный pipeline
Тип: Text (HTML), отображает $pipeline
```

#### 2. Run Type Panel
```
Показывает: Текущий тип запуска (incremental/backfill/rebuild)
Тип: Text (HTML), отображает $run-type
```

#### 3. Execution Timestamp Panel
```
Показывает: Время создания метрики (Unix timestamp)
Метрика: bioetl-records-processed-created
Тип: Stat
```

### Provider Health v2 — 2 info-панели:

#### 1. Provider Panel
```
Показывает: Текущий выбранный provider
Тип: Text (HTML), отображает $provider
```

#### 2. Health Status Panel
```
Показывает: "Provider Health" (статический текст)
Тип: Text (HTML)
```

---

## 📊 Структура верхней строки дашборда

```
DQ v2 / Overview v2:
┌─────────────────────┬───────────────────┬──────────────────────────────┐
│  Pipeline (6 cols)  │  Run Type (6 cols)│  Timestamp (12 cols)         │
├─────────────────────┴───────────────────┴──────────────────────────────┤
│                                                                          │
│                      Основные графики и метрики                         │
│                    (24 cols - во всю ширину)                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────┘

Provider Health v2:
┌─────────────────────┬───────────────────┬──────────────────────────────┐
│  Provider (6 cols)  │ Health Status(6c) │  Timestamp (12 cols)         │
├─────────────────────┴───────────────────┴──────────────────────────────┤
│                                                                          │
│              Provider latency графики и gauges                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────┘
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
Run Type Panel: <обновляется список run-type'ов для uniprot>
Timestamp Panel: <показывает время для выбранного run-type>
```

### При выборе Pipeline = "All"

```
Pipeline Panel: All (или последний используемый)
Run Type Panel: <показывает все run-type'ы>
Timestamp Panel: <показывает максимальное время>
```

### При выборе Run Type

```
Pipeline Panel: <остаётся неизменным>
Run Type Panel: <выбранный run-type>
Timestamp Panel: <обновляется время>
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

```

---

## 🚀 Итоговая структура дашбордов v2

**Верхняя строка (3 height) — DQ v2 / Overview v2:**
- Pipeline info (6 cols)
- Run Type info (6 cols)
- Execution Timestamp info (12 cols)

**Верхняя строка (3 height) — Provider Health v2:**
- Provider info (6 cols)
- Health Status info (6 cols)
- Execution Timestamp info (12 cols)

**Фильтры (dropdown selectors):**
- Pipeline / Run Type (DQ v2, Overview v2)
- Provider (Provider Health v2)

**Содержимое (графики и метрики):**
- Bronze/Silver/Gold Records
- Quality Score (ratio)
- Processing pipelines
- Stage/Pipeline Distribution (piechart)
- Provider latency gauges
- Health Check Status

---

**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready

**Все три дашборда v2 теперь полностью готовы к использованию!** 🎉
