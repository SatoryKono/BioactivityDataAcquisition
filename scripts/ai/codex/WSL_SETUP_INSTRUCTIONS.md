# Инструкция по установке WSL и настройке Codex

## Текущее состояние

- ❌ WSL не установлен (команда `wsl` не распознается)
- ❌ Node.js не установлен
- ✅ Скрипты Codex готовы к работе
- ✅ Шаблон .env.codex.example создан

## Шаг 1: Установка WSL2

**Требуются права администратора**

### Вариант A: Через PowerShell (рекомендуется)

Откройте PowerShell от имени администратора и выполните:

```powershell
wsl --install
```

Эта команда:
- Установит WSL2
- Установит Ubuntu как дистрибутив по умолчанию
- Потребует перезагрузки компьютера

После перезагрузки Ubuntu автоматически запустится и попросит создать пользователя и пароль.

### Вариант B: Через Windows Features

Если `wsl --install` не работает, включите компоненты вручную:

1. Откройте PowerShell от имени администратора
2. Выполните команды:

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

3. Перезагрузите компьютер
4. Скачайте и установите [WSL2 Linux kernel update package](https://aka.ms/wsl2kernel)
5. Установите WSL2 как дистрибутив по умолчанию:

```powershell
wsl --set-default-version 2
```

6. Установите Ubuntu из Microsoft Store или через:

```powershell
wsl --install -d Ubuntu
```

## Шаг 2: Первичная настройка Ubuntu

После установки WSL и перезагрузки:

1. Запустите Ubuntu (из меню Start или командой `wsl`)
2. Создайте пользователя и пароль при запросе
3. Обновите систему:

```bash
sudo apt update && sudo apt upgrade -y
```

## Шаг 3: Настройка Codex

### 3.1. Создайте файл .env.codex

Скрипты настройки не создают `.env.codex` по умолчанию. Создайте его вручную:

Из Windows PowerShell:

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex
copy .env.codex.example .env.codex
notepad .env.codex
```

Добавьте ваш OpenAI API ключ:

```
OPENAI_API_KEY=sk-ваш-ключ-здесь
```

Получите ключ: https://platform.openai.com/api-keys

**Альтернатива**: Запустите настройку с флагом opt-in для автоматического создания шаблона:

```powershell
$env:BIOETL_CREATE_LOCAL_ENV_FILES="1"
.\setup-codex-wsl.bat
```

### 3.2. Запустите автоматическую настройку

Из Windows PowerShell:

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex
.\setup-codex-wsl.bat
```

Или из WSL:

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
bash ./helper/setup-wsl-complete.sh
```

Этот скрипт:
- Проверит WSL окружение
- Установит Node.js и npm (если нужно)
- Установит Codex CLI
- Настроит MCP конфигурацию
- Проверит Docker (опционально)

## Шаг 4: Запуск Codex

### Из Windows PowerShell:

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex
.\launch-codex-wsl.ps1
```

С командой:

```powershell
.\launch-codex-wsl.ps1 exec "analyze the code"
```

### Из WSL:

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
bash ./run-codex.sh
```

С командой:

```bash
bash ./run-codex.sh "analyze the code"
```

## Доступные команды

```powershell
# PowerShell
.\launch-codex-wsl.ps1 start          # Интерактивный режим
.\launch-codex-wsl.ps1 exec "prompt"  # Авто-выполнение
.\launch-codex-wsl.ps1 check          # Проверка окружения
.\launch-codex-wsl.ps1 setup          # Настройка компонентов
.\launch-codex-wsl.ps1 mcp-setup      # Настройка MCP
```

```bash
# WSL/Bash
bash ./run-codex.sh start             # Интерактивный режим
bash ./run-codex.sh exec "prompt"     # Авто-выполнение
bash ./run-codex.sh check             # Проверка окружения
bash ./run-codex.sh setup             # Настройка компонентов
bash ./run-codex.sh mcp-setup         # Настройка MCP
```

## Устранение проблем

### "WSL is not recognized"

Установите WSL2 как описано в Шаге 1.

### "Node.js not found"

Запустите настройку:

```powershell
.\launch-codex-wsl.ps1 setup
```

### "API key not found"

Отредактируйте .env.codex и добавьте ваш ключ.

### Setup висит/зависает

Запустите диагностику:

```powershell
.\helper\diagnose-hang.ps1
```

Или прочитайте [SETUP_HANG_FIX.md](./md/SETUP_HANG_FIX.md)

## Структура скриптов

```
scripts/ai/codex/
├── run-codex.ps1              # PowerShell транспорт к WSL launcher
├── run-codex.sh               # ⭐ Канонический WSL/Bash entry point
├── launch-codex-wsl.ps1       # Упрощенный launcher для WSL
├── setup-codex-wsl.bat        # Batch файл для настройки WSL
├── .env.codex.example         # Шаблон для API ключа
├── helper/
│   ├── setup-wsl-complete.sh  # Полная настройка WSL
│   ├── setup-env.sh           # Настройка окружения
│   ├── ensure-codex-cli.sh    # Установка Codex CLI
│   ├── ensure-mcp.sh           # Синхронизация MCP
│   └── run-codex-impl.sh      # Реализация запуска Codex
└── md/                        # Документация
```

## Следующие шаги после установки

1. Протестируйте интерактивный режим:
   ```powershell
   .\launch-codex-wsl.ps1 start
   ```

2. Протестируйте с командой:
   ```powershell
   .\launch-codex-wsl.ps1 exec "analyze the pipeline"
   ```

3. Ознакомьтесь с документацией:
   - [README.md](./README.md)
   - [QUICK_START.md](./md/QUICK_START.md)
