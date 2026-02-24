# BioETL Dashboard Guides — Индекс документации

> **Path verification (required):** before applying this guide/prompt, locate the runtime observability modules with `rg -n "PrometheusMetrics|start_http_server|metrics_server_integration" src/bioetl`.
> Use these runtime paths:
> Metric definitions/registries — `src/bioetl/infrastructure/observability/metrics.py`, `src/bioetl/infrastructure/observability/prometheus_metrics.py`.
> Metrics server wiring/integration — `src/bioetl/infrastructure/observability/metrics_server_adapter.py`, `src/bioetl/interfaces/cli/commands/metrics_server_integration.py`.

**Местоположение:** `/docs/03-guides/dashboards/`

## 📚 Документация

### 🌟 Главный файл (начните отсюда)

- **BIOETL_DASHBOARD_COMPLETE.md** — Сводка всех компонентов и итоги

### 📖 Основные руководства

1. **BIOETL_DASHBOARD_README.md**

   - Индекс и навигация по всей документации
   - Ответы на вопрос "Где искать?"
   - Быстрые ссылки на компоненты

1. **BIOETL_DASHBOARD_QUICKSTART.md** (⏱️ 5 минут)

   - Чек-лист установки
   - 6 простых команд для запуска
   - Диагностика проблем
   - FAQ

1. **BIOETL_DASHBOARD_SETUP.md** (📖 60 минут)

   - Полная архитектура мониторинга
   - Пошаговая установка (Шаг 1-6)
   - Конфигурация компонентов
   - Использование дашбордов
   - Troubleshooting гайд (10+ решений)

1. **BIOETL_DASHBOARD_VISUAL_GUIDE.md** (👁️ 20 минут)

   - Диаграммы архитектуры
   - Типы панелей Grafana
   - Как читать каждый дашборд
   - Примеры интерпретации данных

1. **BIOETL_DASHBOARD_EXAMPLES.md** (💡 30 минут)

   - Добавить новую метрику
   - Создать собственный дашборд
   - Настроить Alerts
   - PromQL примеры (20+ запросов)
   - Экспорт/импорт дашбордов

### 🛠️ Рабочие файлы

- **src/bioetl/infrastructure/observability/prometheus_metrics.py** — Prometheus metrics endpoint (генерирует метрики)

______________________________________________________________________

## 🎯 Рекомендуемый порядок чтения

### Новичок (40 минут)

1. BIOETL_DASHBOARD_COMPLETE.md ← Сводка (5 мин)
1. BIOETL_DASHBOARD_VISUAL_GUIDE.md ← Диаграммы (20 мин)
1. BIOETL_DASHBOARD_QUICKSTART.md ← Быстрый старт (15 мин)

### Intermediate (2 часа)

1. BIOETL_DASHBOARD_README.md ← Навигация (5 мин)
1. BIOETL_DASHBOARD_SETUP.md ← Полная инструкция (60 мин)
1. BIOETL_DASHBOARD_VISUAL_GUIDE.md ← Примеры (20 мин)
1. BIOETL_DASHBOARD_QUICKSTART.md ← Настройка (35 мин)

### Advanced (3+ часа)

1. Все документы выше (2 часа)
1. BIOETL_DASHBOARD_EXAMPLES.md ← Кастомизация (60 мин)
1. Экспериментирование с Grafana

______________________________________________________________________

## 🚀 Быстрый старт

```bash
# 1. Прочитать сводку
cat BIOETL_DASHBOARD_COMPLETE.md

# 2. Запустить контейнеры
docker compose -f ../../docker-compose.monitoring.yml up -d

# 3. Запустить metrics сервер
python ./src/bioetl/infrastructure/observability/prometheus_metrics.py &

# 4. Открыть Grafana
# http://localhost:3000
```

______________________________________________________________________

## 📊 Структура документации

```
📂 dashboards/
├── 📄 README.md (этот файл)           ← Навигация
│
├── 🌟 BIOETL_DASHBOARD_COMPLETE.md     ← Начните отсюда
│
├── 📖 BIOETL_DASHBOARD_README.md       ← Индекс документации
├── 🚀 BIOETL_DASHBOARD_QUICKSTART.md   ← За 5 минут
├── 📚 BIOETL_DASHBOARD_SETUP.md        ← Полная инструкция
├── 👁️  BIOETL_DASHBOARD_VISUAL_GUIDE.md ← Диаграммы
├── 💡 BIOETL_DASHBOARD_EXAMPLES.md     ← Примеры
│
└── 🛠️  src/bioetl/infrastructure/observability/prometheus_metrics.py                ← Рабочий код
```

______________________________________________________________________

## 🔍 Где найти ответ на вопрос?

| Вопрос                  | Ответ в файле                               |
| ----------------------- | ------------------------------------------- |
| Что было сделано?       | BIOETL_DASHBOARD_COMPLETE.md                |
| С чего начать?          | BIOETL_DASHBOARD_README.md                  |
| Дайте 5 минут на старт  | BIOETL_DASHBOARD_QUICKSTART.md              |
| Дайте полную инструкцию | BIOETL_DASHBOARD_SETUP.md                   |
| Покажите диаграммы      | BIOETL_DASHBOARD_VISUAL_GUIDE.md            |
| Я хочу кастомизировать  | BIOETL_DASHBOARD_EXAMPLES.md                |
| Что-то не работает      | BIOETL_DASHBOARD_SETUP.md (Troubleshooting) |
| Как читать графики?     | BIOETL_DASHBOARD_VISUAL_GUIDE.md            |
| Как добавить метрику?   | BIOETL_DASHBOARD_EXAMPLES.md                |
| PromQL примеры          | BIOETL_DASHBOARD_EXAMPLES.md                |

______________________________________________________________________

## 📈 Состояние готовности

✅ **Установка** — Все компоненты работают
✅ **Конфигурация** — Prometheus, Grafana, Metrics сервер настроены
✅ **Дашборды** — 4 дашборда загружены и работают
✅ **Метрики** — Генерируются и собираются каждые 15 сек
✅ **Документация** — 1,900+ строк полной документации

______________________________________________________________________

## 🎓 Уровни сложности

| Уровень             | Время   | Что изучить                  | Результат             |
| ------------------- | ------- | ---------------------------- | --------------------- |
| 🟢 **Новичок**      | 40 мин  | COMPLETE, VISUAL, QUICKSTART | Мониторинг работает   |
| 🟡 **Intermediate** | 2 часа  | + SETUP + README             | Понимаю архитектуру   |
| 🔴 **Advanced**     | 3+ часа | + EXAMPLES                   | Кастомизирую дашборды |

______________________________________________________________________

## 📞 Поддержка

Все вопросы и ответы находятся в этих документах:

1. **Не знаю с чего начать?** → BIOETL_DASHBOARD_COMPLETE.md
1. **Нужна полная инструкция?** → BIOETL_DASHBOARD_SETUP.md
1. **Что-то не работает?** → BIOETL_DASHBOARD_SETUP.md (раздел Troubleshooting)
1. **Хочу кастомизировать?** → BIOETL_DASHBOARD_EXAMPLES.md

______________________________________________________________________

## 📂 Связанные файлы

- Конфигурация Prometheus: `../../docker-compose.monitoring.yml`
- Конфигурация метрик: `./src/bioetl/infrastructure/observability/prometheus_metrics.py`
- Дашборды JSON: `../../grafana/dashboards/`

______________________________________________________________________

**Версия:** 1.0
**Дата обновления:** 22 февраля 2026
**Статус:** ✅ Готово к использованию

🚀 Начните с **BIOETL_DASHBOARD_COMPLETE.md**!
