# BioETL Dashboard Documentation — Полный индекс

## 📚 Документация

| Файл | Размер | Для кого | Читать |
|------|--------|---------|--------|
| **BIOETL_DASHBOARD_QUICKSTART.md** | 6.5 KB | 🚀 Разработчиков (за 5 минут) | [→](./BIOETL_DASHBOARD_QUICKSTART.md) |
| **BIOETL_DASHBOARD_SETUP.md** | 23 KB | 📖 Полная инструкция (60 минут) | [→](./BIOETL_DASHBOARD_SETUP.md) |
| **BIOETL_DASHBOARD_VISUAL_GUIDE.md** | 17 KB | 👁️ Визуальный гайд (20 минут) | [→](./BIOETL_DASHBOARD_VISUAL_GUIDE.md) |
| **BIOETL_DASHBOARD_EXAMPLES.md** | 15 KB | 💡 Примеры кастомизации (30 минут) | [→](./BIOETL_DASHBOARD_EXAMPLES.md) |
| **Этот файл** | 10 KB | 🗺️ Карта и навигация | - |

---

## 🎯 С чего начать?

### Если у вас есть 5 минут ⏱️
→ Прочитайте [BIOETL_DASHBOARD_QUICKSTART.md](./BIOETL_DASHBOARD_QUICKSTART.md)
- ✅ Чек-лист установки
- ✅ 6 простых шагов
- ✅ Быстрая диагностика

### Если у вас есть 1 час 📚
→ Прочитайте [BIOETL_DASHBOARD_SETUP.md](./BIOETL_DASHBOARD_SETUP.md)
- ✅ Полная архитектура
- ✅ Пошаговая установка
- ✅ Конфигурация каждого компонента
- ✅ Troubleshooting гайд

### Если вы визуал 👁️
→ Посмотрите [BIOETL_DASHBOARD_VISUAL_GUIDE.md](./BIOETL_DASHBOARD_VISUAL_GUIDE.md)
- ✅ Диаграммы и схемы
- ✅ Как читать дашборды
- ✅ Примеры графиков

### Если вы хотите кастомизировать 💡
→ Изучите [BIOETL_DASHBOARD_EXAMPLES.md](./BIOETL_DASHBOARD_EXAMPLES.md)
- ✅ Добавить метрики
- ✅ Создать дашборды
- ✅ Настроить алерты
- ✅ PromQL примеры

---

## 📊 Типичные сценарии

### Сценарий 1: "Я только что клонировал проект"
```
1. Прочитать: QUICKSTART.md (5 минут)
2. Выполнить: чек-лист установки (10 минут)
3. Открыть: http://localhost:3000 ✅
```

### Сценарий 2: "Дашборд пуст, нет данных"
```
1. Перейти: SETUP.md → Troubleshooting
2. Найти: раздел "Дашборд показывает No data"
3. Выполнить: диагностику (5-10 минут)
```

### Сценарий 3: "Хочу добавить свою метрику"
```
1. Перейти: EXAMPLES.md → Добавить новую метрику
2. Отредактировать: metrics_server.py
3. Перезапустить: metrics сервер
4. Использовать в Grafana: PromQL query
```

### Сценарий 4: "Нужно создать собственный дашборд"
```
1. Перейти: EXAMPLES.md → Создать пользовательский дашборд
2. Выбрать: Способ A (UI) или Способ B (JSON)
3. Добавить: панели и queries
4. Сохранить: дашборд
```

### Сценарий 5: "Нужно настроить алерты"
```
1. Перейти: EXAMPLES.md → Настроить Alert
2. Выбрать: простой способ (UI) или advanced (YAML)
3. Сконфигурировать: notification channel (Email/Slack)
4. Протестировать: alert
```

---

## 🏗️ Архитектура компонентов

```
┌─────────────────────────────────────────────────────────┐
│              BioETL Monitoring Stack                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [BioETL App]  →  [Metrics  →  [Prometheus  →  [Grafana]
│  Обработка        Exporter      Time-Series     UI
│  данных           :8000         DB :9090        :3000
│                   (Python)      (Container)     (Container)
│
│  ┌─────────────────────────────────────────────────────┐
│  │ 4 дашборда:                                        │
│  │ • BioETL Simple              (основной)            │
│  │ • BioETL Data Quality v2     (качество данных)     │
│  │ • BioETL Overview v2         (обзор pipeline)      │
│  │ • BioETL Provider Health v2  (статус provider'ов)  │
│  └─────────────────────────────────────────────────────┘
│
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 Ключевые метрики

| Метрика | Как читать | Где используется |
|---------|-----------|-----------------|
| `bioetl_records_processed_total` | Кол-во обработанных записей по stage | Simple, DQ v2, Overview v2 |
| `bioetl_records_processed_created` | Timestamp создания метрики | DQ v2, Overview v2 (Execution Timestamp) |
| `bioetl_health_check_status` | Статус health check (1=healthy) | Provider Health v2 |
| `bioetl_health_check_latency_ms` | P95 latency provider'а (histogram) | Provider Health v2 |

---

## 🎛️ Команды для справки

### Docker

```bash
# Запустить мониторинг
docker compose -f docker-compose.monitoring.yml up -d

# Просмотреть логи
docker logs bioetl-prometheus -f

# Остановить
docker compose -f docker-compose.monitoring.yml down

# Перезагрузить конфиг Prometheus (автоматически)
# Prometheus слушает /etc/prometheus/prometheus.yml
```

### Metrics Server

```bash
# Запустить
python ./metrics_server.py &

# Проверить
curl http://localhost:8000/metrics

# Остановить
pkill -f metrics_server.py
```

### Grafana

```bash
# Вход: admin / admin
# Изменить пароль:
docker exec bioetl-grafana \
  grafana-cli admin reset-admin-password newpassword

# Создать API token
# Settings → API Keys → New API key
```

### Prometheus Query API

```bash
# Текущее значение метрики
curl "http://localhost:9090/api/v1/query?query=bioetl_records_processed_total"

# График за временной диапазон
curl "http://localhost:9090/api/v1/query_range?\
query=bioetl_records_processed_total&\
start=1704067200&end=1704153600&step=300"

# Список всех метрик
curl "http://localhost:9090/api/v1/label/__name__/values"
```

---

## 🔍 Где искать информацию

### Установка и первый запуск
→ **QUICKSTART.md** или **SETUP.md** раздел "Пошаговая установка"

### Диагностика проблем
→ **SETUP.md** раздел "Troubleshooting"

### Как использовать дашборды
→ **VISUAL_GUIDE.md** раздел "Как читать каждый дашборд"

### Кастомизация метрик
→ **EXAMPLES.md** раздел "Добавить новую метрику"

### Создание дашбордов
→ **EXAMPLES.md** раздел "Создать пользовательский дашборд"

### Настройка алертов
→ **EXAMPLES.md** раздел "Настроить Alert"

### PromQL примеры
→ **EXAMPLES.md** раздел "Шпаргалка по PromQL"

### Конфигурация компонентов
→ **SETUP.md** раздел "Конфигурация компонентов"

---

## 📈 Быстрые ссылки

| Компонент | URL | Назначение |
|-----------|-----|-----------|
| Grafana Home | http://localhost:3000 | Главная страница |
| Simple Dashboard | http://localhost:3000/d/bioetl-simple | Основной дашборд |
| Все дашборды | http://localhost:3000/dashboards | Список дашбордов |
| Query Explorer | http://localhost:3000/explore | Тестирование PromQL |
| Prometheus | http://localhost:9090 | Главная Prometheus |
| Prometheus Targets | http://localhost:9090/targets | Статус target'ов |
| Prometheus Graph | http://localhost:9090/graph | Ломаное UI (deprecated) |
| Metrics endpoint | http://localhost:8000/metrics | Raw Prometheus metrics |
| Health check | http://localhost:8000/health | Статус metrics сервера |

---

## 🎓 Обучающие ресурсы

### Для новичков
1. Посмотреть VISUAL_GUIDE.md
2. Открыть BioETL Simple Dashboard
3. Поменять фильтры (Pipeline, Run Type)
4. Посмотреть как меняются графики

### Для intermediate
1. Изучить PromQL в EXAMPLES.md
2. Открыть http://localhost:9090/graph → Explore
3. Написать собственный query
4. Добавить панель в дашборд

### Для advanced
1. Отредактировать metrics_server.py
2. Добавить собственную метрику
3. Создать дашборд с JSON
4. Настроить alerts с Prometheus

---

## 🚨 Emergency Checklist

### Всё сломалось — что делать?

```bash
# 1. Перезапустить все компоненты
docker compose -f docker-compose.monitoring.yml down
docker compose -f docker-compose.monitoring.yml up -d

# 2. Перезапустить metrics сервер
pkill -f metrics_server.py
python ./metrics_server.py &

# 3. Дождаться 15 секунд scrape interval
sleep 15

# 4. Очистить кэш браузера
# F12 → Application → Clear site data

# 5. Обновить дашборд
# F5 в браузере

# 6. Проверить здоровье компонентов
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
curl http://localhost:8000/health
```

---

## 📞 Получить помощь

1. **Проверить Troubleshooting**: SETUP.md
2. **Посмотреть логи**: `docker logs bioetl-prometheus`
3. **Диагностировать**: [SETUP.md - Troubleshooting](./BIOETL_DASHBOARD_SETUP.md#troubleshooting)
4. **Проверить архитектуру**: VISUAL_GUIDE.md

---

## 📦 Что включено в инструкцию

```
📂 Документация
├── 📄 BIOETL_DASHBOARD_QUICKSTART.md      (5 минут)
├── 📄 BIOETL_DASHBOARD_SETUP.md           (60 минут)
├── 📄 BIOETL_DASHBOARD_VISUAL_GUIDE.md    (20 минут)
├── 📄 BIOETL_DASHBOARD_EXAMPLES.md        (30 минут)
└── 📄 README.md (этот файл)

📂 Конфигурация
├── 📄 metrics_server.py                   (Metrics endpoint)
├── 📄 docker-compose.monitoring.yml       (Docker контейнеры)
├── 📄 grafana/prometheus.yml              (Prometheus конфиг)
└── 📄 grafana/provisioning/               (Auto-provisioning)

📂 Дашборды (автоматическое loading)
├── 📊 bioetl-simple.json
├── 📊 bioetl-dq-v2.json
├── 📊 bioetl-overview-v2.json
└── 📊 bioetl-provider-health-v2.json
```

---

## ✨ Что можно делать с BioETL Dashboard

- ✅ Мониторить обработку данных в реальном времени
- ✅ Отслеживать качество данных по стадиям
- ✅ Видеть ошибки и проблемы
- ✅ Сравнивать производительность pipeline'ов
- ✅ Анализировать тренды за неделю/месяц
- ✅ Настраивать алерты на критические события
- ✅ Экспортировать метрики для отчётов
- ✅ Кастомизировать дашборды под свои потребности
- ✅ Интегрировать с другими системами (Slack, PagerDuty)
- ✅ Использовать для внутренних презентаций

---

## 🎯 Конечная цель

Вы успешно:
- ✅ Установили мониторинг (Prometheus + Grafana)
- ✅ Запустили metrics сервер
- ✅ Загрузили 4 дашборда
- ✅ Видите метрики в реальном времени
- ✅ Можете создавать свои дашборды
- ✅ Понимаете архитектуру мониторинга
- ✅ Умеете диагностировать проблемы

---

**Последнее обновление:** 22 февраля 2026  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию

Начните с [BIOETL_DASHBOARD_QUICKSTART.md](./BIOETL_DASHBOARD_QUICKSTART.md) — займет 5 минут! ⏱️
