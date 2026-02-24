# Обновление Дашбордов v2 — Changelog

**Дата:** 22 февраля 2026  
**Версия:** 2.0  
**Статус:** ✅ Готово  

---

## 📊 Обновленные дашборды

### 1. **BioETL Data Quality v2** (bioetl-dq-v2.json)
- UID: `bioetl-dq-v2`
- URL: http://localhost:3000/d/bioetl-dq-v2

### 2. **BioETL Overview v2** (bioetl-overview-v2.json)
- UID: `bioetl-overview-v2`
- URL: http://localhost:3000/d/bioetl-overview-v2

### 3. **BioETL Provider Health v2** (bioetl-provider-health-v2.json)
- UID: `bioetl-provider-health-v2`
- URL: http://localhost:3000/d/bioetl-provider-health-v2

---

## ✨ Ключевые улучшения

### ✅ Добавлено в каждый дашборд:

#### 1. **Pipeline Panel** (верхняя левая часть)
```
Показывает: Название текущего пайплайна
Тип: Stat (текстовая статистика)
Позиция: Левый верхний угол
Размер: 6 колонок
Фон: Выделенный (colored background)
```

#### 2. **Run Type Panel** (верхняя левая часть)
```
Показывает: Тип запуска (incremental, backfill, rebuild)
Тип: Text (HTML)
Позиция: Вторая левая ячейка
Размер: 6 колонок
Фон: Выделенный (colored background)
```

#### 3. **Execution Timestamp Panel** (верхняя часть)
```
Показывает: Время выполнения запуска
Тип: Stat (текстовая статистика)
Позиция: Правая верхняя часть
Размер: 12 колонок
Метрика: bioetl_records_processed_created
```

#### 4. **Фильтрация по переменным**
```
Механизм: Переменные Grafana (dropdown selectors)
$pipeline: Выбор pipeline (multi-select, include all)
$run_type: Выбор типа запуска (multi-select, include all)
$execution: Скрытая переменная (hidden, single)
Результат: Дашборд фильтрует данные по выбранным значениям
```

---

## 🔄 Технические изменения

### PromQL Queries

Все запросы обновлены для использования только последнего run'а:

**Типичный PromQL запрос в v2:**
```promql
bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}
```

### Переменные Grafana

**Data Quality v2 / Overview v2 — 3 переменные:**
```yaml
# Видимые:
pipeline:
  type: query
  definition: label_values(bioetl_records_processed_total, pipeline)
  multi: true, includeAll: true

run_type:
  type: query
  definition: label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)
  multi: true, includeAll: true

# Скрытая:
execution:
  type: query
  hide: 2  # Скрыта от пользователя
  single: true
```

**Provider Health v2 — 1 переменная:**
```yaml
provider:
  type: query
  definition: label_values(bioetl_health_check_latency_ms_bucket, provider)
  multi: true, includeAll: true
```

---

## 📐 Структура верхних панелей

```
┌─────────────────┬──────────────┬───────────────────────┐
│   Pipeline      │  Run Type    │  Execution Timestamp  │
│   (6 cols)      │  (6 cols)    │     (12 cols)         │
├─────────────────┴──────────────┴───────────────────────┤
│                                                         │
│              Основные графики и метрики                │
│         (24 cols - во всю ширину дашборда)            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Примеры использования

### BioETL Data Quality v2

**Верхняя строка показывает:**
```
Pipeline: uniprot
Run Type: incremental
Execution Timestamp: 1645382400
```

**Графики показывают:**
- Data Flow: Bronze → Silver → Gold (timeseries)
- Data Quality Score (gauge, ratio Gold/Bronze)
- Source Records (Bronze stage, stat)
- Clean Records (Gold stage, stat)

### BioETL Overview v2

**Верхняя строка показывает:**
```
Pipeline: pubmed
Run Type: backfill
Execution Timestamp: 1645386000
```

**Графики показывают:**
- Processing Pipeline (timeseries по стадиям)
- Stage Distribution (piechart)
- Pipeline Distribution (piechart)
- Overall Quality (gauge)

### BioETL Provider Health v2

**Верхняя строка показывает:**
```
Provider: chembl
Health Status: Provider Health
Execution Timestamp: 1645389600
```

**Графики показывают:**
- Provider Response Time (P95 latency, histogram_quantile)
- Health Check Status (stat)
- Individual Latency Gauges (UniProt, PubMed, PubChem, ChemBL)

---

## 🔍 Как работает фильтрация

**Процесс:**

1. **Grafana загружает дашборд**
   ↓
2. **Заполняются переменные из Prometheus labels**
   ```promql
   label_values(bioetl_records_processed_total, pipeline)   → $pipeline
   label_values(bioetl_records_processed_total, run_type)    → $run_type
   ```
   ↓
3. **Пользователь выбирает нужные значения** в dropdown
   ```
   Pipeline: uniprot    Run Type: incremental
   ```
   ↓
4. **Все панели фильтруются по выбранным значениям**
   ```promql
   bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}
   ```
   ↓
5. **Дашборд показывает отфильтрованные данные**

---

## 📊 Сравнение старой и новой версии

| Параметр | Simple (v1) | v2 дашборды |
|----------|-------------|-------------|
| Фильтрация | Pipeline + Run Type + Execution | Pipeline + Run Type (execution hidden) |
| Run Type видно | В dropdown | ✅ Да (в info-панели + dropdown) |
| Pipeline видно | В dropdown | ✅ Да (в info-панели + dropdown) |
| Timestamp видно | Нет | ✅ Да (в info-панели) |
| Refresh rate | 5 секунд | 30 секунд |
| Time range | 1 час | 7 дней |

---

## 🚀 Запуск обновленных дашбордов

### Способ 1: Автоматически (через provisioning)

Дашборды автоматически обновляются при перезагрузке Grafana:

```bash
docker restart bioetl-grafana
```

### Способ 2: Вручную

1. Открыть Grafana: http://localhost:3000
2. Home → Dashboards → BioETL
3. Выбрать нужный дашборд v2
4. Нажать F5 для обновления

### Способ 3: Через Grafana API

```bash
# Перезагрузить дашборды через API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @bioetl-dq-v2.json
```

---

## 🔧 Отладка

### Если дашборд показывает "No data":

1. **Проверить, что metrics сервер работает:**
   ```bash
   curl http://localhost:8000/metrics | grep bioetl_records_processed
   ```

2. **Проверить Prometheus target:**
   ```
   http://localhost:9090/targets → найти "bioetl" → должна быть "UP"
   ```

3. **Проверить, что есть данные за последний run:**
   ```
   http://localhost:9090 → Explore
   Query: bioetl_records_processed_total
   Должны быть результаты
   ```

4. **Обновить дашборд:**
   - F5 в браузере
   - Или нажать кнопку refresh в Grafana

---

## 📝 Файлы, которые были изменены

```
grafana/dashboards/
├── bioetl-dq-v2.json (updated)
├── bioetl-overview-v2.json (updated)
└── bioetl-provider-health-v2.json (updated)
```

---

## ✅ Что можно делать с новыми дашбордами

✅ Видеть последний запуск автоматически  
✅ Видеть название пайплайна в реальном времени  
✅ Видеть Run Type и время запуска
✅ Сравнивать разные run'ы (открыть в разных tabs)  
✅ Экспортировать данные для отчётов  
✅ Настроить alerts на основе последнего run'а  

---

## 🎉 Итог

**Три дашборда v2 теперь:**
- ✅ Показывают только последний запуск
- ✅ Отображают Pipeline, Run Type и время запуска
- ✅ Автоматически обновляются при новых запусках
- ✅ Не требуют ручного выбора переменных

**Готовы к использованию!** 🚀

---

**Версия:** 2.0  
**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready
