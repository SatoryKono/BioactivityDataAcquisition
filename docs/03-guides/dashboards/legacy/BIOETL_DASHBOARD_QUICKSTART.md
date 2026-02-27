# BioETL Dashboard — Чек-лист быстрого старта

## ✅ Pre-flight Checklist

- [ ] Python 3.11+ установлен: `python --version`
- [ ] Docker & Docker Compose: `docker --version && docker compose --version`
- [ ] Порты 3000, 9090, 8000 свободны
- [ ] 2GB RAM свободно

## 🚀 Запуск (5 минут)

### 1️⃣ Клонировать/Обновить проект
```bash
cd /path/to/BioactivityDataAcquisition2
git pull origin main
```

### 2️⃣ Установить зависимости BioETL
```bash
pip install -e .
# Или через uv (быстрее)
uv sync
```

### 3️⃣ Запустить контейнеры мониторинга
```bash
docker compose -f docker-compose.monitoring.yml up -d
# Проверить статус
docker compose -f docker-compose.monitoring.yml ps
```

### 4️⃣ Запустить metrics сервер
```bash
# Способ A: В фоне (разработка)
python ./metrics-server.py &

# Способ B: В отдельном терминале (удобно для debug)
python ./metrics-server.py
```

### 5️⃣ Проверить, что всё работает
```bash
# Metrics endpoint
curl http://localhost:8000/metrics | head -10
# Output: # HELP bioetl-records-processed-total ...

# Prometheus API
curl http://localhost:9090/api/v1/query?query=bioetl-records-processed-total
# Output: JSON с метриками

# Grafana UI
# Открыть в браузере: http://localhost:3000
```

### 6️⃣ Открыть дашборд
```
URL: http://localhost:3000/d/bioetl-simple
Логин: admin
Пароль: admin
```

## 📊 Что смотреть в дашбордах

| Дашборд | URL | Что показывает |
|---------|-----|-----------------|
| Simple | /d/bioetl-simple | Основные метрики (Records, Quality) |
| Overview | /d/bioetl-overview | Общая статистика |
| Data Quality | /d/bioetl-dq-v2 | Метрики качества данных |
| Provider Health | /d/bioetl-provider-health | Статус каждого provider |

## 🔍 Отладка (если что-то не работает)

### Prometheus не собирает метрики (targets = DOWN)
```bash
# Проверить metrics сервер
curl http://localhost:8000/metrics

# Если ошибка → перезапустить
pkill -f metrics-server.py
python ./metrics-server.py &

# Дождаться 15 сек, затем проверить Prometheus targets:
# http://localhost:9090/targets
```

### Дашборд пуст (No data)
```bash
# 1. Проверить Prometheus query
# http://localhost:9090 → Explore
# Query: bioetl-records-processed-total

# 2. Если нет результатов → метрики не генерируются
# Проверить metrics-server.py работает:
ps aux | grep metrics-server

# 3. Обновить дашборд (F5) после 15 сек scrape interval
```

### Grafana не подключается к Prometheus
```bash
# Проверить статус Prometheus
curl http://localhost:9090/-/healthy

# Проверить Data Source в Grafana
# http://localhost:3000 → Configuration → Data Sources → Prometheus
# Должно быть: http://host.docker.internal:9090

# Если ошибка → обновить URL и нажать "Save & test"
```

## 📈 Пример: Как читать дашборд

### BioETL Simple Dashboard

**Верхняя строка (Stat панели):**
- Bronze Records: 4000+ (исходные данные)
- Silver Records: 3800+ (очищенные данные)
- Gold Records: 3500+ (готовые данные)
- Quality Ratio: 87% (процент данных, дошедших до gold)

**Нижний график (Timeseries):**
- Тренд обработки за последний час
- Три линии: bronze (зелёная), silver (синяя), gold (красная)
- Если линия плоская → данные не обновляются (проверить metrics)

## 🛑 Остановка сервисов

```bash
# Остановить контейнеры
docker compose -f docker-compose.monitoring.yml down

# Остановить metrics сервер
pkill -f metrics-server.py

# Удалить все данные (осторожно!)
docker compose -f docker-compose.monitoring.yml down -v
```

## 📝 Полезные файлы

| Файл | Назначение |
|------|-----------|
| `docker-compose.monitoring.yml` | Конфигурация контейнеров |
| `grafana/prometheus.yml` | Конфигурация Prometheus |
| `grafana/provisioning/` | Автозагрузка дашбордов |
| `metrics-server.py` | Metrics endpoint |
| `BIOETL-DASHBOARD-SETUP.md` | Полная инструкция |

## 🎯 Типичный workflow

1. **Запустить**
   ```bash
   docker compose -f docker-compose.monitoring.yml up -d
   python ./metrics-server.py &
   ```

2. **Открыть Grafana**
   ```
   http://localhost:3000/d/bioetl-simple
   ```

3. **Мониторить метрики**
   - Обновляется каждые 5 сек (refresh rate в дашборде)
   - Данные собираются каждые 15 сек (scrape interval)

4. **При нужде отредактировать**
   - Dashboard → Edit panel → Update query → Save

5. **Остановить**
   ```bash
   docker compose -f docker-compose.monitoring.yml down
   pkill -f metrics-server.py
   ```

## ❓ FAQ

**Q: Как изменить пароль Grafana?**
A: `docker exec bioetl-grafana grafana-cli admin reset-admin-password newpassword`

**Q: Как добавить свою метрику?**
A: Отредактировать `metrics-server.py`, добавить Counter/Gauge, перезапустить

**Q: Как сохранить дашборд?**
A: Dashboard → Export → Save JSON → Поделиться с командой

**Q: Куда сохраняются данные Prometheus?**
A: В Docker volume `bioetl-prometheus-data` (retention: 15 дней)

**Q: Как скачать метрики?**
A: `http://localhost:9090/api/v1/query-range?query=...&start=...&end=...`

---

**Дата:** 22 февраля 2026  
**Версия:** 1.0  
**Поддержка:** См. BIOETL-DASHBOARD-SETUP.md (раздел Troubleshooting)
