# BioETL Dashboards v2 — Руководство по использованию

## 🎯 Обновленные дашборды

Три дашборда версии 2.0 теперь включают информацию о последнем запуске:

| Дашборд | URL | Переменные |
|---------|-----|-----------|
| **Data Quality v2** | http://localhost:3000/d/bioetl-dq-v2 | Pipeline, Run Type, Timestamp |
| **Overview v2** | http://localhost:3000/d/bioetl-overview-v2 | Pipeline, Run Type, Timestamp |
| **Provider Health v2** | http://localhost:3000/d/bioetl-provider-health-v2 | Provider, Timestamp |

---

## 📊 Что показывает каждый дашборд

### 1. BioETL Data Quality v2
**Назначение:** Анализ качества данных

**Верхняя строка (info-панели):**
```
Pipeline: uniprot          Run Type: incremental     Execution Timestamp: 1645382400
```

**Графики:**
- Data Flow: Bronze → Silver → Gold (процесс обработки)
- Data Quality Score (% качества - gauge)
- Source Records (Bronze stage)
- Clean Records (Gold stage)

**Интерпретация:**
- Если Quality Score > 95% ✅ — отлично
- Если Quality Score 80-95% ⚠️ — норма
- Если Quality Score < 80% ❌ — требует внимания

---

### 2. BioETL Overview v2
**Назначение:** Общий обзор обработки pipeline

**Верхняя строка (info-панели):**
```
Pipeline: pubmed           Run Type: backfill     Execution Timestamp: 1645386000
```

**Графики:**
- Processing Pipeline (тренд по стадиям)
- Stage Distribution (pie chart)
- Pipeline Distribution (pie chart)
- Overall Quality (gauge)

**Интерпретация:**
- Bronze → Silver → Gold должны снижаться (нормальный процесс)
- Overall Quality должен быть ≥95%
- Если что-то застопорилось на стадии → ошибка

---

### 3. BioETL Provider Health v2
**Назначение:** Статус и latency каждого provider'а

**Верхняя строка (info-панели):**
```
Provider: chembl           Health Status: Provider Health     Execution Timestamp: 1645389600
```

**Переменная:** `$provider` (вместо $pipeline/$run_type в других дашбордах)

**Графики:**
- Provider Response Time (P95 latency, histogram_quantile)
- Health Check Status (stat)
- Individual Latency Gauges (UniProt, PubMed, PubChem, ChemBL)

**Интерпретация (пороги в миллисекундах):**
- Зелёный цвет ✅ — < 0.5ms
- Жёлтый ⚠️ — 0.5-1ms
- Оранжевый ⚠️ — 1-2ms
- Красный ❌ — > 2ms

---

## 🚀 Как использовать

### Первый раз

1. **Откройте Grafana:**
   ```
   http://localhost:3000
   ```

2. **Перейдите на дашборд:**
   ```
   Home → Dashboards → BioETL → BioETL Data Quality v2
   ```

3. **Дашборд покажет:**
   - ✅ Pipeline название (info-панель)
   - ✅ Run Type (info-панель)
   - ✅ Execution Timestamp (info-панель)
   - ✅ Все метрики с фильтрацией по выбранным значениям

### Регулярно

1. **Открывайте дашборд** — автоматически обновляется (каждые 30 сек)
2. **Смотрите Pipeline и Run Type** — в info-панелях вверху
3. **Проверяйте метрики** — сравнивайте с нормой

---

## 📈 Нормальные значения

### BioETL Data Quality v2

| Метрика | Норма | Внимание | Критично |
|---------|-------|----------|----------|
| Data Quality Score | > 95% | 80-95% | < 80% |
| Gold Records | > 90% Bronze | 70-90% | < 70% |

### BioETL Overview v2

| Метрика | Норма | Внимание | Критично |
|---------|-------|----------|----------|
| Overall Quality | > 95% | 80-95% | < 80% |
| Bronze → Silver | > 80% | 50-80% | < 50% |
| Silver → Gold | > 90% | 70-90% | < 70% |

### BioETL Provider Health v2

| Provider | Норма | Внимание | Критично |
|----------|-------|----------|----------|
| UniProt | < 0.5ms | 0.5-1ms | > 1ms |
| PubMed | < 1ms | 1-2ms | > 2ms |
| PubChem | < 1ms | 1-2ms | > 2ms |
| ChemBL | < 1ms | 1-2ms | > 2ms |

---

## 🔍 Как ищете проблему

### Если качество упало

1. **Откройте BioETL Data Quality v2**
2. **Посмотрите Pipeline и Run Type**
3. **Проверьте Data Quality Score**
4. **Если < 80%:**
   - Перейдите на **BioETL Provider Health v2**
   - Проверьте, какой provider медленный
   - Обновите данные или перезапустите

### Если данные не обрабатываются

1. **Откройте BioETL Overview v2**
2. **Посмотрите Processing Pipeline график**
3. **Если линии плоские:**
   - Перезагрузите metrics server: `python ./metrics_server.py &`
   - Перезагрузите Prometheus: `docker restart bioetl-prometheus`
4. **Дождитесь 15 сек scrape interval**

### Если provider недоступен

1. **Откройте BioETL Provider Health v2**
2. **Посмотрите Health Check Status**
3. **Проверьте Individual Latency Gauges**
4. **Проверьте Provider Response Time — высокая latency указывает на проблему**

---

## 💡 Советы

### Совет 1: Сравнение разных запусков

Хотите сравнить два разных запуска?
```
1. Откройте BioETL Overview v2 в Tab 1
2. Откройте BioETL Overview v2 в Tab 2
3. Выберите разные значения Pipeline/Run Type в каждом Tab
4. Сравните рядом
```

### Совет 2: Мониторинг тренда

Хотите видеть тренд последних запусков?
```
1. Откройте BioETL Data Quality v2
2. Скопируйте Query: bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}
3. Перейдите на http://localhost:9090/explore
4. Вставьте query и смотрите тренд за 7 дней
```

### Совет 3: Экспорт для отчётов

Хотите экспортировать данные?
```
1. Dashboard → 3 точки (⋮) → Export
2. Выбрать Panel → Export as PNG
3. Отправить в отчёт
```

---

## 🐛 Проблемы и решения

### Проблема: "No data" в дашборде

**Решение:**
```bash
# 1. Проверить metrics сервер
curl http://localhost:8000/metrics

# 2. Если нет — перезапустить
python ./metrics_server.py &

# 3. Дождаться 15 сек
# 4. Обновить дашборд (F5)
```

### Проблема: Pipeline/Run Type не показывается

**Решение:**
```bash
# 1. Перезагрузить Grafana
docker restart bioetl-grafana

# 2. Обновить дашборд
# F5 в браузере

# 3. Очистить кэш
# F12 → Application → Clear site data
```

### Проблема: Timestamp показывает 0 или старый

**Решение:**
```
Это нормально — timestamp показывает время последней метрики.
Если метрики старые, значит запуск был давно.
Запустите новый run — обновится автоматически.
```

---

## 📊 Примеры интерпретации

### Хороший run

```
Pipeline: uniprot
Run Type: incremental
Execution Timestamp: 1645382400 (26 февраля, 10:00)

Data Quality Score: 0.97  ✅
Bronze Records: 10,000
Gold Records: 9,700
Quality Ratio: 0.97
```

**Вывод:** Отличный run, всё хорошо ✅

### Проблемный run

```
Pipeline: pubmed
Run Type: backfill
Execution Timestamp: 1645385000 (26 февраля, 10:50)

Data Quality Score: 0.62  ❌
Bronze Records: 5,000
Gold Records: 3,100
Quality Ratio: 0.62
```

**Вывод:** Проблема — PubMed медленный, много ошибок ❌

---

## 🎯 Когда открывать какой дашборд

| Вопрос | Дашборд |
|--------|---------|
| Как качество данных? | Data Quality v2 |
| Сколько данных обработано? | Overview v2 |
| Какой provider медленный? | Provider Health v2 |
| Почему упало качество? | Provider Health v2 |
| Когда был последний запуск? | Любой (см. Timestamp) |

---

## ✨ Итог

**Три дашборда v2 теперь:**
- ✅ Отображают Pipeline, Run Type и время запуска в info-панелях
- ✅ Фильтрация по Pipeline и Run Type через dropdown
- ✅ Автоматически обновляются (каждые 30 сек)
- ✅ Provider Health v2 — отдельная фильтрация по Provider
- ✅ Готовы к production использованию

**Открывайте и мониторьте!** 🚀

---

**Последнее обновление:** 22 февраля 2026  
**Версия:** 2.0  
**Статус:** ✅ Production Ready
