# Mistral Vibe - Как запустить

## ✅ Статус системы

Все компоненты готовы к работе:
- ✅ Python 3.x установлен
- ✅ pip/pipx доступны
- ✅ Mistral Vibe может быть установлен
- ✅ .env.mistrallvibe с MISTRAL_API_KEY готов
- ✅ Таймауты и retry логика добавлены

## 🚀 Запуск Mistral Vibe

### Вариант 1: Windows Terminal (Рекомендуется)

```powershell
.\scripts\ai\mistrallvibe\launch-interactive.ps1
```

Это откроет новую вкладку Windows Terminal с интерактивной сессией Vibe.

### Вариант 2: WSL терминал (Ubuntu)

```bash
# Откройте WSL терминал
wsl -d Ubuntu

# Перейдите в папку
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mistrallvibe

# Запустите Vibe
bash run-vibe.sh start
```

### Вариант 3: Одна команда WSL

```bash
wsl -d Ubuntu bash -i -c "cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mistrallvibe && bash run-vibe.sh start"
```

### Вариант 4: Автоматический режим (без интерактивности)

Для выполнения команды без подтверждений:

```powershell
.\scripts\ai\mistrallvibe\run-vibe.ps1 "анализируй код в папке src"
```

или через WSL:

```bash
./run-vibe.sh "inspect the test failures"
```

## 🔍 Диагностика

### Проверить статус всех компонентов

**PowerShell:**
```powershell
.\scripts\ai\mistrallvibe\run-vibe.ps1 check
```

**WSL/Bash:**
```bash
cd scripts/ai/mistrallvibe && bash helper/check-env.sh
```

### Установить недостающие компоненты

**PowerShell:**
```powershell
.\scripts\ai\mistrallvibe\run-vibe.ps1 setup
```

**WSL/Bash:**
```bash
cd scripts/ai/mistrallvibe && bash helper/setup-env.sh
```

## ⚙️ Все команды

### PowerShell

```powershell
# Диагностика
.\scripts\ai\mistrallvibe\run-vibe.ps1 check

# Установка
.\scripts\ai\mistrallvibe\run-vibe.ps1 setup

# Интерактивный режим (с инструкциями)
.\scripts\ai\mistrallvibe\run-vibe.ps1 start

# Автоматический режим с промптом
.\scripts\ai\mistrallvibe\run-vibe.ps1 "ваш промпт"

# Справка
.\scripts\ai\mistrallvibe\run-vibe.ps1 --help
```

### WSL/Bash

```bash
cd scripts/ai/mistrallvibe

# Диагностика
bash helper/check-env.sh

# Установка
bash helper/setup-env.sh

# Интерактивный режим
bash run-vibe.sh start

# Автоматический режим с промптом
bash run-vibe.sh "ваш промпт"

# Справка
bash run-vibe.sh --help
```

## 📝 Редактирование API ключа

Если нужно изменить MISTRAL_API_KEY:

```powershell
# Откройте в текстовом редакторе
code .\scripts\ai\mistrallvibe\.env.mistrallvibe

# Или в Notepad
notepad .\scripts\ai\mistrallvibe\.env.mistrallvibe
```

Замените `your-api-key-here` на ваш реальный API ключ из:
https://console.mistral.ai/api-keys/

## 🐛 Решение проблем

### pip install зависает

Теперь добавлен таймаут (60 сек) и автоматический retry (2 попытки):

```bash
# Если все равно зависает, установите вручную:
pip install --user mistral-vibe

# Или через pipx:
pipx install mistral-vibe
```

### Mistral Vibe не найден в PATH

После установки может потребоваться перезагрузить терминал:

```bash
# Или добавить PATH вручную:
export PATH="$HOME/.local/bin:$PATH"

# Проверить:
vibe --version
```

### WSL не отвечает

```powershell
# Перезагрузить WSL
wsl --shutdown

# Затем попробуйте снова
```

### Windows Terminal не установлен

Установите из Microsoft Store:
https://www.microsoft.com/store/productId/9N0DX20HK701

Или используйте вариант запуска через WSL терминал напрямую.

### Проблема с конфигурацией

```powershell
# Пересоздать .env.mistrallvibe:
Remove-Item .\scripts\ai\mistrallvibe\.env.mistrallvibe
.\scripts\ai\mistrallvibe\run-vibe.ps1 setup
```

## 📊 Что было исправлено

✅ **Таймауты добавлены на:**
- git rev-parse: 5 сек
- command -v проверки: 10 сек
- pip install: 60 сек (с retry)
- pipx install: 60 сек (с retry)
- Проверки файлов: 5 сек
- Проверки команд: 10 сек

✅ **Retry логика добавлена:**
- pip/pipx установка: макс 2 попытки
- sleep 2 сек между повторами

✅ **Graceful fallback:**
- Если pipx недоступен, используется pip
- Если vibe не в PATH, показывается инструкция

## 🔗 Связанные документы

- `MISTRAL_VIBE_SETUP_PLAN.md` — детальный план настройки
- `MISTRAL_VIBE_SETUP_SUMMARY.md` — краткое резюме различий
- `scripts/ai/mistrallvibe/README.md` — документация совместимости
- `scripts/ai/vibe/README.md` — каноническая документация Vibe

