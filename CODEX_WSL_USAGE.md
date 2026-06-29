# Запуск Codex через WSL — Полное руководство

## ✅ Ваша система готова

Все компоненты установлены и работают:

- **WSL2** ✓ Ubuntu running
- **Node.js** ✓ v20.10.0
- **Codex CLI** ✓ 0.141.0
- **Docker** ✓ Running
- **OpenAI API ключ** ✓ Настроен

## 🚀 Быстрый старт

### 1. Из PowerShell (самый быстрый способ)

```powershell
# Интерактивный режим (с подтверждениями)
.\codex.ps1

# С командой (автоматический режим)
.\codex.ps1 exec "analyze the code"
```

### 2. Или из scripts/ai/codex

```powershell
cd scripts\ai\codex
.\run-codex.ps1 check
.\run-codex.ps1 exec "your prompt"
```

### 3. Или из CMD/BAT

```cmd
codex.bat check
codex.bat exec "your prompt"
```

### 4. Или из WSL/Bash напрямую

```bash
wsl -d Ubuntu
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
bash run-codex.sh exec "your prompt"
```

## 📋 Доступные команды

```powershell
.\codex.ps1                      # Интерактивный режим
.\codex.ps1 exec "prompt"        # Авто-режим (без подтверждений)
.\codex.ps1 check                # Проверка окружения
.\codex.ps1 setup                # Установка компонентов
.\codex.ps1 mcp-check            # Проверка MCP
.\codex.ps1 mcp-setup            # Синхронизация MCP
.\codex.ps1 login                # Вход с API ключом
.\codex.ps1 device-login         # Device code вход
.\codex.ps1 help                 # Справка
```

## 💡 Примеры использования

### Проанализировать код
```powershell
.\codex.ps1 exec "analyze the ChemBL data parser and find bottlenecks"
```

### Исправить баг
```powershell
.\codex.ps1 exec "the data validation fails with timeout, debug and fix"
```

### Рефакторинг
```powershell
.\codex.ps1 exec "refactor the ETL pipeline to use async/await"
```

### Проверить тесты
```powershell
.\codex.ps1 exec "review test coverage and add missing tests"
```

## 🔧 Как это работает

```
PowerShell (codex.ps1)
    ↓
WSL (run-codex.sh)
    ↓
1. Проверка окружения (Node.js, npm, Codex CLI)
2. Синхронизация MCP конфигурации
3. Запуск Codex CLI
```

## 📂 Расположение файлов

| Файл | Назначение |
|------|-----------|
| `codex.ps1` | Лаунчер из корня (самый удобный) |
| `codex.bat` | Батник для CMD |
| `scripts\ai\codex\run-codex.ps1` | Основной PowerShell лаунчер |
| `scripts\ai\codex\run-codex.sh` | Основной WSL/Bash лаунчер (canonical) |
| `scripts\ai\codex\.env.codex` | Конфигурация (API ключ) |

## 🔐 API Ключ

Расположен в: `scripts\ai\codex\.env.codex`

Для обновления:
```powershell
notepad .\scripts\ai\codex\.env.codex
```

Получить новый ключ: https://platform.openai.com/api-keys

## ⚙️ Расширенные команды

### Пропустить синхронизацию MCP
```powershell
$env:CODEX_SKIP_MCP_SETUP = 1
.\codex.ps1 exec "your prompt"
```

### Использовать другой WSL дистрибутив
```powershell
$env:BIOETL_WSL_DISTRO = "Ubuntu"
.\codex.ps1 check
```

### Запуск без синхронизации MCP (headless)
```powershell
cd scripts\ai\codex
.\headless.ps1 exec "your prompt"
```

## 🐛 Решение проблем

### "wsl не найден"
WSL установлена. Если команда не работает в PowerShell, используйте:
```cmd
codex.bat check
```

### Нет вывода на экран
Проверьте:
```powershell
wsl -d Ubuntu -e bash -c "echo test"
```

Должно вывести `test`.

### API ключ не найден
Отредактируйте:
```powershell
notepad .\scripts\ai\codex\.env.codex
OPENAI_API_KEY=sk-your-key
```

### Setup зависает
Запустите диагностику:
```powershell
.\codex.ps1 check
```

Или в WSL:
```bash
wsl -d Ubuntu
bash scripts/ai/codex/helper/diagnose-hang.ps1
```

## 🎯 Следующие шаги

1. **Протестируйте интерактивный режим**:
   ```powershell
   .\codex.ps1
   ```

2. **Протестируйте с командой**:
   ```powershell
   .\codex.ps1 exec "list Docker containers"
   ```

3. **Проверьте окружение**:
   ```powershell
   .\codex.ps1 check
   ```

## 📚 Дополнительная документация

- Main README: `scripts\ai\codex\README.md`
- WSL Setup: `scripts\ai\codex\WSL_SETUP_INSTRUCTIONS.md`
- Quick Start: `scripts\ai\codex\QUICKSTART_WSL.md`
- Troubleshooting: `CODEX_SETUP.txt`

---

**Статус**: ✅ Готово к использованию

Запустите `.\codex.ps1` из корня репозитория.
