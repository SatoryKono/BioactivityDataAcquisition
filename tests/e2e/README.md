# E2E Tests Documentation

## Обзор

E2E (End-to-End) тесты проверяют работу системы BioETL с реальной инфраструктурой через Docker Compose.

## Текущее Состояние

### ✅ Реализовано

1. **Инфраструктура тестов** (`test_infrastructure.py`)
   - Проверка подключения к Redis
   - Тестирование Redis distributed locks
   - Операции с MinIO (buckets, objects)
   - Интеграция RedisDistributedLock с реальным Redis
   - Checkpoint с MinIO S3

2. **Docker Compose конфигурация**
   - `docker-compose.test.yml` с MinIO и Redis
   - Healthchecks для обоих сервисов
   - Изолированная сеть `bioetl-test`

3. **CI/CD Integration**
   - `.github/workflows/e2e.yml` - nightly запуск (02:00 UTC)
   - Manual dispatch для ручного запуска
   - Автоматическое создание issue при ошибках

4. **Makefile команды**
   - `make test-e2e` - полный цикл (запуск Docker + тесты + teardown)
   - `make test-e2e-local` - тесты с существующими сервисами

### ⏸️ Отложено (Skipped)

Полные pipeline E2E тесты (`test_full_pipeline.py`) временно **пропускаются** из-за:

- **Delta Lake Integration Issues**: Проблемы с Arrow schema compatibility
- **Domain Model Changes**: Несоответствие полей в `Activity` entity
- **PubChem Configuration**: Требуется конфигурация query parameters

Эти тесты будут активированы после исправления указанных проблем.

## Запуск E2E Тестов

### Локально

```bash
# Полный цикл (запустить Docker, тесты, остановить)
make test-e2e

# Если Docker уже запущен
make test-e2e-local

# Только инфраструктурные тесты
pytest tests/e2e/test_infrastructure.py -v -m e2e
```

### Предварительные требования

- Docker и docker-compose установлены
- Порты 9000, 9001 (MinIO) и 16379 (Redis) свободны
- Python 3.11+ с установленными dev зависимостями

### Переменные окружения

E2E тесты автоматически настраивают следующие переменные:

```bash
BIOETL_ENV=dev
BIOETL_TEST_MODE=true
BIOETL_S3_ENDPOINT=http://localhost:9000
BIOETL_S3_ACCESS_KEY=minioadmin
BIOETL_S3_SECRET_KEY=minioadmin
BIOETL_REDIS_URL=redis://localhost:16379
```

## Структура Файлов

```
tests/e2e/
├── __init__.py                   # Описание E2E тестов
├── README.md                     # Эта документация
├── conftest.py                   # Fixtures для E2E (Redis, MinIO)
├── test_infrastructure.py        # ✅ Активные тесты инфраструктуры
└── test_full_pipeline.py         # ⏸️ Отложенные полные pipeline тесты
```

## Покрытие Тестами

### Инфраструктура (Активно)

- [x] Redis подключение и базовые операции
- [x] Redis distributed locks (acquire/release)
- [x] MinIO bucket operations
- [x] MinIO object upload/download
- [x] RedisDistributedLock интеграция
- [x] S3Checkpoint с MinIO

### Pipeline Flow (Отложено)

- [ ] ChEMBL Activity full pipeline (Bronze → Silver → Gold)
- [ ] PubChem Compound pipeline
- [ ] Pipeline resume после failure
- [ ] Idempotency тесты (duplicate records)

## CI/CD

### Nightly Workflow

- **Расписание**: Каждую ночь в 02:00 UTC
- **Триггеры**:
  - Schedule (cron)
  - Manual dispatch
  - Push в `main` (только для изменений E2E файлов)
- **Timeout**: 30 минут
- **Артефакты**: logs, test results (7 дней retention)
- **Уведомления**: Auto-create issue при ошибках

### Локальная отладка CI

```bash
# Эмуляция CI окружения
export BIOETL_ENV=dev
export BIOETL_TEST_MODE=true

# Запустить Docker как в CI
docker compose -f docker-compose.test.yml up -d

# Подождать готовности сервисов
sleep 10

# Запустить тесты
pytest tests/e2e/ -v -m e2e --tb=short --maxfail=3

# Остановить Docker
docker compose -f docker-compose.test.yml down
```

## Минимизация Рисков

### Flaky Tests

- ✅ Docker healthchecks с retry
- ✅ Увеличенные timeouts для первого запуска
- ✅ Isolation через dedicated network

### Медленные Тесты

- ✅ Только nightly CI (не на каждый PR)
- ✅ Лимит 10 записей для pipeline тестов
- ✅ `@pytest.mark.slow` для длительных тестов

### Сетевые Ошибки

- ✅ VCR.py **отключён** для E2E (real HTTP calls)
- ✅ Retry logic в HTTP clients
- ⚠️ Circuit breaker disabled для тестов

## Следующие Шаги

1. **Исправить Delta Lake Integration**
   - Resolve Arrow schema compatibility issues
   - Update `DeltaWriter` to handle test scenarios

2. **Обновить Domain Models**
   - Sync `Activity` entity с pipeline transforms
   - Add missing fields or make them optional

3. **Активировать Pipeline Tests**
   - Remove `@pytest.mark.skip` после исправления
   - Add PubChem query configuration
   - Verify idempotency with real data

4. **Расширить Coverage**
   - UniProt pipeline E2E
   - Gold layer aggregations
   - Quarantine E2E flow

## Troubleshooting

### Тесты не находят Docker сервисы

```bash
# Проверить статус сервисов
docker compose -f docker-compose.test.yml ps

# Проверить healthchecks
docker compose -f docker-compose.test.yml ps --format json | jq '.[].Health'

# Логи сервисов
docker compose -f docker-compose.test.yml logs minio
docker compose -f docker-compose.test.yml logs redis
```

### Port already in use

```bash
# Найти процесс на порту
lsof -i :9000  # MinIO
lsof -i :16379 # Redis

# Или остановить все контейнеры
docker compose -f docker-compose.test.yml down -v
```

### Тесты падают с timeout

- Увеличить `sleep` в Makefile (default 5s)
- Проверить Docker ресурсы (CPU, memory)
- Запустить тесты с `--log-cli-level=DEBUG`

## Контакты

При проблемах с E2E тестами:
- Проверить GitHub Issues с тегом `e2e`
- Проверить nightly workflow failures
- Обратиться к CLAUDE.md и RULES.md для архитектурных требований
