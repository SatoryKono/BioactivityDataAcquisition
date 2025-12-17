#!/bin/bash
set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}     BioETL Developer Setup Script     ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 1. Проверка версии Python
echo -e "\n${YELLOW}[1/6] Проверка окружения...${NC}"
REQUIRED_PYTHON="3.11"
PYTHON_CMD="python3"

if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}Ошибка: Python не найден. Пожалуйста, установите Python $REQUIRED_PYTHON+.${NC}"
    exit 1
fi

# Получаем версию для отображения
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Обнаружен Python версии: $PYTHON_VERSION"

# Проверка версии через Python (без зависимости от bc)
if ! $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}Ошибка: Требуется Python версии $REQUIRED_PYTHON или выше.${NC}"
    exit 1
fi

# 2. Создание виртуального окружения
echo -e "\n${YELLOW}[2/6] Настройка виртуального окружения (.venv)...${NC}"
if [ -d ".venv" ]; then
    echo "Виртуальное окружение уже существует."
else
    $PYTHON_CMD -m venv .venv
    echo -e "${GREEN}Виртуальное окружение создано.${NC}"
fi

# Активация venv для скрипта
# Используем условную логику, чтобы избежать падения при set -e
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo -e "${RED}Не удалось найти скрипт активации виртуального окружения.${NC}"
    exit 1
fi

# 3. Установка зависимостей
echo -e "\n${YELLOW}[3/6] Установка зависимостей проекта...${NC}"
echo "Обновление pip..."
pip install --upgrade pip setuptools wheel

echo "Установка пакета в режиме разработки..."
pip install -e ".[dev,docs]"

# 4. Настройка Git Hooks
echo -e "\n${YELLOW}[4/6] Установка pre-commit hooks...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo -e "${GREEN}Pre-commit hooks установлены.${NC}"
else
    echo -e "${RED}Pre-commit не установлен. Проверьте requirements.${NC}"
fi

# 5. Настройка переменных окружения
echo -e "\n${YELLOW}[5/6] Настройка конфигурации (.env)...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}Файл .env создан из шаблона .env.example.${NC}"
        echo -e "${YELLOW}ВАЖНО: Пожалуйста, отредактируйте .env и укажите актуальные секреты/пути!${NC}"
    else
        echo -e "${RED}Файл .env.example не найден!${NC}"
    fi
else
    echo "Файл .env уже существует. Пропуск."
fi

# 6. Проверка установки
echo -e "\n${YELLOW}[6/6] Проверка установки...${NC}"
if python -c "import bioetl; print(f'BioETL {bioetl.__version__} успешно импортирован')" &> /dev/null; then
    echo -e "${GREEN}Модуль bioetl доступен.${NC}"
else
    echo -e "${RED}Ошибка при импорте bioetl. Проверьте установку.${NC}"
    exit 1
fi

echo -e "\n${BLUE}=======================================${NC}"
echo -e "${GREEN}✅ Настройка завершена успешно!${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "Для начала работы:"
echo -e "1. Активируйте окружение: ${YELLOW}source .venv/bin/activate${NC}"
echo -e "2. Запустите тесты:       ${YELLOW}make test${NC}"
echo -e "3. Запустите инфраструктуру: ${YELLOW}make docker-up${NC}"
echo -e "\nУдачи!"
