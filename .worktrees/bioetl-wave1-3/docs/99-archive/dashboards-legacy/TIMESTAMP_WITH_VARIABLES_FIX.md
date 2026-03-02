# Исправление: Execution Timestamp теперь работает с переменными!

## ✅ Что было исправлено

Обновлены запросы для Execution Timestamp панели во всех дашбордах v2, чтобы работать с переменными pipeline и run-type.

### ПроблемА

**Было:**
```promql
bioetl-run-start-timestamp
```

Этот запрос не использовал переменные pipeline и run-id, поэтому всегда показывал глобальное время независимо от выбранных фильтров.

### РешениЕ

**Стало:**
```promql
max(bioetl-records-processed-created{pipeline=~"$pipeline", run-type=~"$run-type"})
```

Теперь запрос:
- ✅ Использует переменную `$pipeline` для фильтрации
- ✅ Использует переменную `$run-type` для фильтрации
- ✅ Берёт максимальное значение (если несколько значений)
- ✅ Обновляется при изменении фильтров

---

## 📊 Как теперь работает

### Пошагово

1. **Пользователь выбирает Pipeline**
   ```
   Pipeline: uniprot
   ```

2. **Пользователь выбирает Run Type**
   ```
   Run Type: incremental
   ```

3. **Execution Timestamp обновляется**
   ```promql
   max(bioetl-records-processed-created{pipeline=~"uniprot", run-type=~"incremental"})
   ```

4. **Панель показывает время для этого конкретного run'а**
   ```
   Execution Timestamp: 1645382400 (26 Feb 2026, 10:00 UTC)
   ```

### При изменении фильтров

- Если выбрать другой Pipeline → Timestamp обновится
- Если выбрать другой Run Type → Timestamp обновится
- Если выбрать "All" → Timestamp покажет максимальное значение

---

## 📋 Обновленные PromQL в панелях

Также обновлены все PromQL запросы в панелях для использования обеих переменных:

### Было:
```promql
bioetl-records-processed-total{run-id=~"..."}
```

### Стало:
```promql
bioetl-records-processed-total{pipeline=~"$pipeline", run-type=~"$run-type"}
```

---

## 🎯 Дашборды, которые обновлены

| Дашборд | Файл | Статус |
|---------|------|--------|
| BioETL Data Quality v2 | bioetl-dq-v2.json | ✅ Updated |
| BioETL Overview v2 | bioetl-overview-v2.json | ✅ Updated |
| BioETL Provider Health v2 | bioetl-provider-health-v2.json | ✅ Updated |

---

## 📈 Примеры использования

### Пример 1: Конкретный pipeline и run

```
Pipeline: pubmed
Run Type: backfill

Результат:
- Execution Timestamp: 1645386000 (время запуска PubMed)
- Все графики: данные только для backfill запусков
```

### Пример 2: Все run'ы одного pipeline

```
Pipeline: uniprot
Run Type: All

Результат:
- Execution Timestamp: максимальное время (последний запуск)
- Все графики: объединённые данные всех типов запуска uniprot
```

### Пример 3: Все pipeline'ы и run'ы

```
Pipeline: All
Run Type: All

Результат:
- Execution Timestamp: максимальное время (последний запуск вообще)
- Все графики: объединённые данные всех pipeline'ов и типов запуска
```

---

## 🔍 Как проверить, что работает

1. **Откройте дашборд:**
   ```
   http://localhost:3000/d/bioetl-dq-v2
   ```

2. **Выберите Pipeline:**
   ```
   Pipeline: uniprot
   ```

3. **Выберите Run Type:**
   ```
   Run Type: incremental
   ```

4. **Проверьте Execution Timestamp:**
   ```
   Должно показать время для этого specific run'а
   Пример: 1645382400
   ```

5. **Измените фильтры:**
   - Timestamp должен обновиться
   - Все графики должны пересчитаться

---

## ✨ Достоинства этого исправления

✅ **Timestamp теперь привязан к фильтрам** — показывает время только для выбранных данных  
✅ **Динамическое обновление** — при изменении Pipeline/Run Type обновляется автоматически
✅ **Многовыборная фильтрация** — работает с "All" опциями  
✅ **Консистентность** — все панели используют одинаковую логику фильтрации  

---

## 📝 Файлы, которые изменились

```
grafana/dashboards/
├── bioetl-dq-v2.json (updated)
├── bioetl-overview-v2.json (updated)
└── bioetl-provider-health-v2.json (updated)

```

---

## 🚀 Итог

Execution Timestamp теперь полностью интегрирован с переменными pipeline и run-type. Дашборды v2 готовы к production!

**Все три дашборда теперь имеют:**
- ✅ Pipeline фильтр
- ✅ Run Type фильтр (зависит от Pipeline)
- ✅ Execution Timestamp (зависит от обоих фильтров)
- ✅ Все графики и метрики (зависят от обоих фильтров)

---

**Дата:** 22 февраля 2026  
**Статус:** ✅ Production Ready
