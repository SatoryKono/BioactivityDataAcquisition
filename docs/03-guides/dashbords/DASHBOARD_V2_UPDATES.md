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

#### 2. **Run ID Panel** (верхняя левая часть)
```
Показывает: Уникальный идентификатор последнего запуска
Тип: Stat (текстовая статистика)
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
Фон: Выделенный (colored background)
```

#### 4. **Автоматическая фильтрация последнего Run'а**
```
Механизм: Скрытая переменная (hidden variable)
Имя переменной: $latest_run_id
PromQL: sort_desc(label_values(bioetl_records_processed_total, run_id))[0]
Результат: Дашборд автоматически показывает только последний run
```

---

## 🔄 Технические изменения

### PromQL Queries

Все запросы обновлены для использования только последнего run'а:

**Было:**
```promql
bioetl_records_processed_total{pipeline=~"$pipeline", run_id=~"$run_id"}
```

**Стало:**
```promql
bioetl_records_processed_total{run_id=~"$latest_run_id"}
```

### Переменные Grafana

**Добавлена скрытая переменная:**
```yaml
name: latest_run_id
type: query
datasource: Prometheus
definition: sort_desc(label_values(bioetl_records_processed_total, run_id))[0]
hide: 2  # Скрыта от пользователя
refresh: 1  # Обновляется каждый раз
```

**Удалены/скрыты:**
- Pipeline variable (была `includeAll: true`)
- Run ID variable (больше не нужна, используется latest)

---

## 📐 Структура верхних панелей

```
┌─────────────────┬──────────────┬───────────────────────┐
│   Pipeline      │   Run ID     │  Execution Timestamp  │
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
Run ID: run-492157
Execution Timestamp: 1645382400
```

**Графики показывают:**
- Data Flow: Bronze → Silver → Gold (только для run-492157)
- Data Quality Score (процент качества)
- Source Records (Bronze stage)
- Clean Records (Gold stage)

### BioETL Overview v2

**Верхняя строка показывает:**
```
Pipeline: pubmed
Run ID: run-492158
Execution Timestamp: 1645386000
```

**Графики показывают:**
- Processing Pipeline (все стадии)
- Stage Distribution (pie chart)
- Pipeline Distribution (pie chart)
- Overall Quality (gauge)

### BioETL Provider Health v2

**Верхняя строка показывает:**
```
Pipeline: pubchem
Run ID: run-492159
Execution Timestamp: 1645389600
```

**Графики показывают:**
- Provider Response Time (по pipeline)
- Error Rate by Provider
- Individual Latency Gauges (UniProt, PubMed, PubChem, ChemBL)

---

## 🔍 Как работает автоматическая фильтрация

**Процесс:**

1. **Grafana загружает дашборд**
   ↓
2. **Выполняется PromQL запрос для переменной `latest_run_id`**
   ```promql
   sort_desc(label_values(bioetl_records_processed_total, run_id))[0]
   ```
   ↓
3. **Результат:** Получается самый новый run ID
   ```
   run-492159
   ```
   ↓
4. **Все панели используют эту переменную**
   ```promql
   bioetl_records_processed_total{run_id=~"$latest_run_id"}
   ```
   ↓
5. **Дашборд показывает только данные последнего run'а**

---

## 📊 Сравнение старой и новой версии

| Параметр | v1 | v2 |
|----------|----|----|
| Фильтрация | Ручная (Pipeline + Run ID) | Автоматическая (Latest Run) |
| Run ID видно | Нет | ✅ Да (в панели) |
| Pipeline видно | Нет | ✅ Да (в панели) |
| Timestamp видно | Нет | ✅ Да (в панели) |
| Фильтры переменных | Показаны | Скрыты |
| Обновление Run | Ручное | Автоматическое (refresh 1) |

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
✅ Видеть Run ID и время запуска  
✅ Сравнивать разные run'ы (открыть в разных tabs)  
✅ Экспортировать данные для отчётов  
✅ Настроить alerts на основе последнего run'а  

---

## 🎉 Итог

**Три дашборда v2 теперь:**
- ✅ Показывают только последний запуск
- ✅ Отображают Pipeline, Run ID и время запуска
- ✅ Автоматически обновляются при новых запусках
- ✅ Не требуют ручного выбора переменных

**Готовы к использованию!** 🚀

---

**Версия:** 2.0  
**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready
