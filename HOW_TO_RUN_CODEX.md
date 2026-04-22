# Codex - Как запустить

## ✅ Статус системы

Все компоненты установлены и готовы к работе:
- ✅ Node.js v25.2.1 (Windows) / v18.19.1 (WSL)
- ✅ npm 11.12.1 (Windows) / 9.2.0 (WSL)
- ✅ Codex CLI v0.120.0
- ✅ .env.codex с OPENAI_API_KEY
- ✅ MCP конфигурация синхронизирована

## 🚀 Запуск Codex

### Вариант 1: Windows Terminal (Рекомендуется)

```powershell
.\scripts\ai\codex\launch-interactive.ps1
```

### Вариант 2: WSL терминал (Ubuntu)

```bash
# Откройте WSL терминал (Ubuntu)
wsl -d Ubuntu

# Перейдите в папку
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex

# Запустите Codex
bash run-codex.sh start
```

### Вариант 3: Одна команда WSL

```bash
wsl -d Ubuntu bash -i -c "cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex && ./run-codex.sh start"
```

### Вариант 4: Использование Exec режима (без интерактивности)

Для автоматического выполнения без подтверждений:

```powershell
.\scripts\ai\codex\run-codex.ps1 exec "анализируй мой код"
```

## 🔍 Диагностика

Проверить статус всех компонентов:

```powershell
.\scripts\ai\codex\run-codex.ps1 check
```

Установить недостающие компоненты:

```powershell
.\scripts\ai\codex\run-codex.ps1 setup
```

## ⚙️ Все команды

```powershell
# Диагностика
.\scripts\ai\codex\run-codex.ps1 check

# Установка
.\scripts\ai\codex\run-codex.ps1 setup

# Интерактивный режим (с инструкциями)
.\scripts\ai\codex\run-codex.ps1 start

# Автоматический режим
.\scripts\ai\codex\run-codex.ps1 exec "ваш промпт"

# Логин
.\scripts\ai\codex\run-codex.ps1 login

# Справка
.\scripts\ai\codex\run-codex.ps1 help
```

## 📝 Редактирование API ключа

Если нужно изменить OPENAI_API_KEY:

```powershell
# Откройте в текстовом редакторе
code .\scripts\ai\codex\.env.codex

# Или в Notepad
notepad .\scripts\ai\codex\.env.codex
```

Замените `sk-your-key-here` на ваш реальный API ключ из:
https://platform.openai.com/api-keys

## 🐛 Если возникли проблемы

### WSL не отвечает
```powershell
# Перезагрузить WSL
wsl --shutdown

# Затем попробуйте снова
```

### Проблема с терминалом
Используйте **Windows Terminal** из Microsoft Store:
https://www.microsoft.com/store/productId/9N0DX20HK701

### Версия Codex не обновляется
```powershell
.\scripts\ai\codex\run-codex.ps1 setup
```

---

## 📊 Что было исправлено

✅ **Таймауты на все долгие операции:**
- git rev-parse: 5 сек
- npm install: 120 сек
- Python setup_mcp: 30 сек
- Проверка Codex: 10 сек
- MCP синхронизация: 60 сек

✅ **Логика безопасности:**
- Лимит повторов проверок: макс 2 попытки
- Graceful fallback при таймаутах
- Продолжение работы при ошибках MCP

✅ **Правильные пути к конфигам:**
- .env.codex в scripts/ai/codex/
- Автоматическое создание при отсутствии
- Проверка API ключа перед запуском

