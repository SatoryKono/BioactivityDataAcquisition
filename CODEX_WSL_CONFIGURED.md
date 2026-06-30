# Codex WSL Setup — Полная конфигурация ✅

## 🎯 Проблема была в синтаксисе WSL вызова из PowerShell

**Проблема**: `wsl -d Ubuntu -e bash -- /path/script.sh` не выводит результат
**Решение**: Использовать синтаксис `wsl -e bash -c "bash /path/script.sh"`

---

## ✅ Ваша система настроена

- **WSL2** ✓ Ubuntu running
- **Node.js** ✓ v20.10.0
- **npm** ✓ 10.2.3
- **Codex CLI** ✓ 0.141.0
- **Docker** ✓ Running
- **OpenAI API ключ** ✓ Configured

---

## 🚀 Быстрый старт — 3 способа

### Способ 1: Из корня репо (рекомендуется)

```powershell
# Интерактивный
.\codex.ps1

# С командой
.\codex.ps1 exec "analyze the code"

# Проверить
.\codex.ps1 check
```

### Способ 2: Из scripts/ai/codex

```powershell
cd scripts\ai\codex
.\run-codex.ps1 exec "your prompt"
```

### Способ 3: Из CMD/BAT

```cmd
codex.bat exec "your prompt"
```

### Способ 4: Из WSL/Bash напрямую

```bash
wsl -d Ubuntu
bash scripts/ai/codex/run-codex.sh exec "your prompt"
```

---

## 📝 Исправленные файлы

| Файл | Изменение |
|------|-----------|
| `scripts/ai/codex/run-codex.ps1` | ✓ Исправлен синтаксис WSL вызова |
| `scripts/ai/codex/headless.ps1` | ✓ Обновлен синтаксис |
| `codex.ps1` | ✓ Создан удобный лаунчер из корня |
| `codex.bat` | ✓ Создан для CMD/BAT |

---

## 🔧 Как работает

```
┌─ codex.ps1 ──────────────────────────────────┐
│  Лаунчер из корня (удобнейший способ)        │
└─────────────┬────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────┐
│ run-codex.ps1                                │
│ PowerShell транспорт для WSL                 │
│ Синтаксис: wsl -e bash -c "bash script"     │
└─────────────┬────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────┐
│ run-codex.sh (canonical)                     │
│ WSL/Bash точка входа                         │
│ 1. Проверка окружения                        │
│ 2. Синхронизация MCP                         │
│ 3. Запуск Codex CLI                          │
└─────────────┬────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────┐
│ Codex CLI                                    │
│ Запускается в директории репо                │
└──────────────────────────────────────────────┘
```

---

## 📋 Все команды

```powershell
# Интерактивный (с подтверждениями)
.\codex.ps1

# Автоматический (без подтверждений)
.\codex.ps1 exec "your prompt"

# Диагностика
.\codex.ps1 check          # Проверить окружение
.\codex.ps1 setup          # Установить компоненты

# MCP конфигурация
.\codex.ps1 mcp-check      # Проверить MCP
.\codex.ps1 mcp-setup      # Синхронизировать MCP

# Аутентификация
.\codex.ps1 login          # API ключ
.\codex.ps1 device-login   # Device code

# Справка
.\codex.ps1 help
```

---

## 💡 Примеры использования

### Анализировать код
```powershell
.\codex.ps1 exec "analyze the data acquisition pipeline for performance issues"
```

### Исправить баг
```powershell
.\codex.ps1 exec "fix the timeout in the validation step"
```

### Рефакторинг
```powershell
.\codex.ps1 exec "refactor to use async/await pattern"
```

### Review тестов
```powershell
.\codex.ps1 exec "review test coverage and add missing edge cases"
```

### Интерактивный режим
```powershell
.\codex.ps1
# Codex откроет интерактивный интерфейс и будет ждать вашего ввода
```

---

## 🔐 OpenAI API Ключ

**Расположение**: `scripts/ai/codex/.env.codex` (в .gitignore)

**Обновить**:
```powershell
notepad .\scripts\ai\codex\.env.codex
```

**Получить новый ключ**: https://platform.openai.com/api-keys

**Примечание**: Скрипты настройки не создают `.env.codex` автоматически. Создайте его вручную из `.env.codex.example`, или используйте флаг `BIOETL_CREATE_LOCAL_ENV_FILES=1` при запуске setup для автоматической генерации шаблона.

---

## 📂 Структура файлов

```
.
├── codex.ps1                           ← Основной лаунчер (использовать!)
├── codex.bat                           ← Для CMD/BAT
├── scripts/
│   └── ai/
│       └── codex/
│           ├── run-codex.ps1           ← PowerShell транспорт (исправлен)
│           ├── run-codex.sh            ← Canonical WSL лаунчер
│           ├── headless.ps1            ← Без MCP sync (исправлен)
│           ├── headless.sh             ← Bash версия
│           ├── .env.codex              ← Конфиг (API ключ)
│           ├── .env.codex.example      ← Шаблон
│           ├── README.md               ← Документация
│           ├── WSL_SETUP_INSTRUCTIONS.md
│           ├── QUICKSTART_WSL.md
│           └── helper/
│               ├── setup-wsl-complete.sh
│               ├── run-codex-impl.sh
│               ├── ensure-codex-cli.sh
│               ├── ensure-mcp.sh
│               └── ...
```

---

## ⚙️ Расширенные опции

### Пропустить MCP синхронизацию
```powershell
$env:CODEX_SKIP_MCP_SETUP = 1
.\codex.ps1 exec "your prompt"
```

### Использовать другой WSL дистрибутив
```powershell
$env:BIOETL_WSL_DISTRO = "Ubuntu"
.\codex.ps1 check
```

### Запуск в headless режиме (без UI)
```powershell
cd scripts\ai\codex
.\headless.ps1 exec "your prompt"
```

---

## 🐛 Решение проблем

### "Command not found" или нет вывода
Используйте батник:
```cmd
codex.bat check
```

### WSL не отвечает
Проверьте:
```powershell
wsl -d Ubuntu -e bash -c "echo test"
```

Должно вывести `test`.

### Медленный старт
Это нормально при первом запуске MCP синхронизации. При повторных запусках будет быстрее.

### Docker не доступен
Убедитесь, что Docker Desktop запущен на Windows.

---

## 🔗 Документация

- **Этот файл**: `CODEX_WSL_USAGE.md` (основное руководство)
- **Настройка**: `scripts/ai/codex/QUICKSTART_WSL.md`
- **README**: `scripts/ai/codex/README.md`
- **WSL инструкции**: `scripts/ai/codex/WSL_SETUP_INSTRUCTIONS.md`
- **Troubleshooting**: `CODEX_SETUP.txt`

---

## ✨ Итог

**Проблема решена:** WSL вывод теперь работает корректно

**Используйте**:
```powershell
.\codex.ps1 exec "your prompt"
```

**Или интерактивно**:
```powershell
.\codex.ps1
```

---

**Статус**: ✅ **Готово к использованию**

Запустите любую из команд выше и Codex начнет работать с вашим кодом.
