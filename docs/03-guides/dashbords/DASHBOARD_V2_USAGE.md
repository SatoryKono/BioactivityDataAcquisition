# BioETL Dashboards v2 — Руководство по использованию

## 🎯 Обновленные дашборды

Три дашборда версии 2.0 теперь включают информацию о последнем запуске:

| Дашборд | URL | Информация |
|---------|-----|-----------|
| **Data Quality v2** | http://localhost:3000/d/bioetl-dq-v2 | Pipeline, Run ID, Timestamp |
| **Overview v2** | http://localhost:3000/d/bioetl-overview-v2 | Pipeline, Run ID, Timestamp |
| **Provider Health v2** | http://localhost:3000/d/bioetl-provider-health-v2 | Pipeline, Run ID, Timestamp |

---

## 📊 Что показывает каждый дашборд

### 1. BioETL Data Quality v2
**Назначение:** Анализ качества данных для последнего запуска

**Верхняя строка:**
```
Pipeline: uniprot          Run ID: run-492157     Execution Timestamp: 1645382400
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
**Назначение:** Общий обзор обработки для последнего запуска

**Верхняя строка:**
```
Pipeline: pubmed           Run ID: run-492158     Execution Timestamp: 1645386000
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
**Назначение:** Статус каждого provider'а для последнего запуска

**Верхняя строка:**
```
Pipeline: pubchem          Run ID: run-492159     Execution Timestamp: 1645389600
```

**Графики:**
- Provider Response Time (P95 latency)
- Error Rate by Provider
- Individual Latency Gauges (UniProt, PubMed, PubChem, ChemBL)

**Интерпретация:**
- Зелёный цвет ✅ — < 0.5s, отлично
- Жёлтый ⚠️ — 0.5-1s, норма
- Оранжевый ⚠️ — 1-2s, медленно
- Красный ❌ — > 2s, проблема

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

3. **Дашборд автоматически покажет:**
   - ✅ Pipeline название
   - ✅ Run ID последний
   - ✅ Execution Timestamp
   - ✅ Все метрики для этого run'а

### Регулярно

1. **Открывайте дашборд** — автоматически обновляется
2. **Смотрите Pipeline и Run ID** — всегда актуальные
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
| UniProt | < 0.5s | 0.5-1s | > 1s |
| PubMed | < 1s | 1-2s | > 2s |
| PubChem | < 1s | 1-2s | > 2s |
| ChemBL | < 1s | 1-2s | > 2s |

---

## 🔍 Как ищете проблему

### Если качество упало

1. **Откройте BioETL Data Quality v2**
2. **Посмотрите Pipeline и Run ID**
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
2. **Посмотрите Error Rate графики**
3. **Найдите provider с ошибками**
4. **Проверьте latency — если > 5s, то он заблокирован**

---

## 💡 Советы

### Совет 1: Сравнение разных запусков

Хотите сравнить два разных run'а?
```
1. Откройте BioETL Overview v2 в Tab 1
2. Откройте старый дашборд BioETL Overview в Tab 2 (с ручной фильтрацией)
3. Выберите разные Run ID'ы
4. Сравните рядом
```

### Совет 2: Мониторинг тренда

Хотите видеть тренд последних запусков?
```
1. Откройте BioETL Data Quality v2
2. Скопируйте Query: bioetl_records_processed_total{run_id=~"$latest_run_id"}
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

### Проблема: Pipeline/Run ID не показывается

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
Run ID: run-492157
Execution Timestamp: 1645382400 (26 февраля, 10:00)

Data Quality Score: 97%  ✅
Bronze Records: 10,000
Gold Records: 9,700
Quality Ratio: 97%

Error Rate: < 0.1%
Response Time: 350ms
```

**Вывод:** Отличный run, всё хорошо ✅

### Проблемный run

```
Pipeline: pubmed
Run ID: run-492158
Execution Timestamp: 1645385000 (26 февраля, 10:50)

Data Quality Score: 62%  ❌
Bronze Records: 5,000
Gold Records: 3,100
Quality Ratio: 62%

Error Rate: 5.2%  ⚠️
Response Time: 2.1s  ⚠️
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
- ✅ Показывают только последний запуск
- ✅ Отображают Pipeline, Run ID и время запуска
- ✅ Автоматически обновляются при новых запусках
- ✅ Не требуют ручного выбора переменных
- ✅ Готовы к production использованию

**Открывайте и мониторьте!** 🚀

---

**Последнее обновление:** 22 февраля 2026  
**Версия:** 2.0  
**Статус:** ✅ Production Ready
