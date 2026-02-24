# BioETL Dashboard Guides — Индекс документации

**Местоположение:** `/docs/03-guides/dashboards/`

## 📚 Документация

### 🌟 Главный файл (начните отсюда)
- **BIOETL_DASHBOARD_COMPLETE.md** — Сводка всех компонентов и итоги

### 📖 Основные руководства

1. **BIOETL_DASHBOARD_README.md** 
   - Индекс и навигация по всей документации
   - Ответы на вопрос "Где искать?"
   - Быстрые ссылки на компоненты

2. **BIOETL_DASHBOARD_QUICKSTART.md** (⏱️ 5 минут)
   - Чек-лист установки
   - 6 простых команд для запуска
   - Диагностика проблем
   - FAQ

3. **BIOETL_DASHBOARD_SETUP.md** (📖 60 минут)
   - Полная архитектура мониторинга
   - Пошаговая установка (Шаг 1-6)
   - Конфигурация компонентов
   - Использование дашбордов
   - Troubleshooting гайд (10+ решений)

4. **BIOETL_DASHBOARD_VISUAL_GUIDE.md** (👁️ 20 минут)
   - Диаграммы архитектуры
   - Типы панелей Grafana
   - Как читать каждый дашборд
   - Примеры интерпретации данных

5. **BIOETL_DASHBOARD_EXAMPLES.md** (💡 30 минут)
   - Добавить новую метрику
   - Создать собственный дашборд
   - Настроить Alerts
   - PromQL примеры (20+ запросов)
   - Экспорт/импорт дашбордов

### 🛠️ Рабочие файлы

- **metrics_server.py** — Prometheus metrics endpoint (генерирует метрики)

---

## 🎯 Рекомендуемый порядок чтения

### Новичок (40 минут)
1. BIOETL_DASHBOARD_COMPLETE.md ← Сводка (5 мин)
2. BIOETL_DASHBOARD_VISUAL_GUIDE.md ← Диаграммы (20 мин)
3. BIOETL_DASHBOARD_QUICKSTART.md ← Быстрый старт (15 мин)

### Intermediate (2 часа)
1. BIOETL_DASHBOARD_README.md ← Навигация (5 мин)
2. BIOETL_DASHBOARD_SETUP.md ← Полная инструкция (60 мин)
3. BIOETL_DASHBOARD_VISUAL_GUIDE.md ← Примеры (20 мин)
4. BIOETL_DASHBOARD_QUICKSTART.md ← Настройка (35 мин)

### Advanced (3+ часа)
1. Все документы выше (2 часа)
2. BIOETL_DASHBOARD_EXAMPLES.md ← Кастомизация (60 мин)
3. Экспериментирование с Grafana

---

## 🚀 Быстрый старт

```bash
# 1. Прочитать сводку
cat BIOETL_DASHBOARD_COMPLETE.md

# 2. Запустить контейнеры
docker compose -f ../../docker-compose.monitoring.yml up -d

# 3. Запустить metrics сервер
python ./metrics_server.py &

# 4. Открыть Grafana
# http://localhost:3000
```

---

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
└── 🛠️  metrics_server.py                ← Рабочий код
```

---

## 🔍 Где найти ответ на вопрос?

| Вопрос | Ответ в файле |
|--------|--------------|
| Что было сделано? | BIOETL_DASHBOARD_COMPLETE.md |
| С чего начать? | BIOETL_DASHBOARD_README.md |
| Дайте 5 минут на старт | BIOETL_DASHBOARD_QUICKSTART.md |
| Дайте полную инструкцию | BIOETL_DASHBOARD_SETUP.md |
| Покажите диаграммы | BIOETL_DASHBOARD_VISUAL_GUIDE.md |
| Я хочу кастомизировать | BIOETL_DASHBOARD_EXAMPLES.md |
| Что-то не работает | BIOETL_DASHBOARD_SETUP.md (Troubleshooting) |
| Как читать графики? | BIOETL_DASHBOARD_VISUAL_GUIDE.md |
| Как добавить метрику? | BIOETL_DASHBOARD_EXAMPLES.md |
| PromQL примеры | BIOETL_DASHBOARD_EXAMPLES.md |

---

## 📈 Состояние готовности

✅ **Установка** — Все компоненты работают
✅ **Конфигурация** — Prometheus, Grafana, Metrics сервер настроены
✅ **Дашборды** — 4 дашборда загружены и работают
✅ **Метрики** — Генерируются и собираются каждые 15 сек
✅ **Документация** — 1,900+ строк полной документации

---

## 🎓 Уровни сложности

| Уровень | Время | Что изучить | Результат |
|---------|-------|-----------|-----------|
| 🟢 **Новичок** | 40 мин | COMPLETE, VISUAL, QUICKSTART | Мониторинг работает |
| 🟡 **Intermediate** | 2 часа | + SETUP + README | Понимаю архитектуру |
| 🔴 **Advanced** | 3+ часа | + EXAMPLES | Кастомизирую дашборды |

---

## 📞 Поддержка

Все вопросы и ответы находятся в этих документах:

1. **Не знаю с чего начать?** → BIOETL_DASHBOARD_COMPLETE.md
2. **Нужна полная инструкция?** → BIOETL_DASHBOARD_SETUP.md
3. **Что-то не работает?** → BIOETL_DASHBOARD_SETUP.md (раздел Troubleshooting)
4. **Хочу кастомизировать?** → BIOETL_DASHBOARD_EXAMPLES.md

---

## 📂 Связанные файлы

- Конфигурация Prometheus: `../../docker-compose.monitoring.yml`
- Конфигурация метрик: `./metrics_server.py`
- Дашборды JSON: `../../grafana/dashboards/`

---

**Версия:** 1.0  
**Дата обновления:** 22 февраля 2026  
**Статус:** ✅ Готово к использованию  

🚀 Начните с **BIOETL_DASHBOARD_COMPLETE.md**!
