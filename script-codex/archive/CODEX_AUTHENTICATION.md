# Codex Authentication для Безголовой Машины

## Быстрый способ: Переменная окружения

### Из PowerShell:

```powershell
# 1. Установить API key (замените на ваш реальный ключ)
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# 2. Запустить Codex
.\script-codex\run-codex.ps1 login
```

### Из WSL:

```bash
# 1. Установить API key
export OPENAI_API_KEY="sk-your-api-key-here"

# 2. Запустить Codex
bash ./script-codex/run-codex.sh login
```

---

## Постоянный способ: Файл .env.codex

### 1. Отредактируйте `.env.codex`:

```bash
notepad .\.env.codex
```

Содержимое:
```
OPENAI_API_KEY=sk-your-api-key-here
```

### 2. Запустите Codex:

```powershell
.\script-codex\run-codex.ps1 login
```

Скрипт автоматически загрузит API key из файла.

---

## Получить API Key

1. Откройте: https://platform.openai.com/api-keys
2. Залогиньтесь в OpenAI
3. Нажмите "Create new secret key"
4. Скопируйте ключ (начинается с `sk-`)
5. Вставьте в `.env.codex` или переменную окружения

---

## Рекомендуемый процесс

### Первый раз:

```powershell
# 1. Установить ключ
$env:OPENAI_API_KEY = "sk-..."

# 2. Запустить с аутентификацией
.\script-codex\run-codex.ps1 login

# 3. Проверить что работает
# Введите: analyze the repository
```

### В дальнейшем:

Просто используйте:
```powershell
.\script-codex\run-codex.ps1 login
```

Ключ будет загружен автоматически из `.env.codex`.

---

## Для безголовой машины без GUI

**Используйте API Key метод** - это единственный способ без браузера.

Команда `run-codex login` в `script-codex` специально подходит для этого:
- ✅ Не требуют браузера
- ✅ Используют API key напрямую
- ✅ Подходят для CI/CD и автоматизации
- ✅ Работают в WSL

---

## Проверить что работает

```powershell
# После установки API key
.\script-codex\run-codex.ps1 login

# В Codex введите:
show me the src directory structure

# Codex должен ответить без ошибок аутентификации
```

---

## Безопасность

⚠️ **Не коммитьте `.env.codex` с реальными ключами!**

Добавьте в `.gitignore`:
```
.env.codex
.env.local
.env
```

Ключ хранится локально и не передается.

---

## Если возникают проблемы

```powershell
# 1. Проверьте переменную
$env:OPENAI_API_KEY

# 2. Проверьте файл
Get-Content .\.env.codex

# 3. Проверьте формат ключа (должен начинаться с sk-)

# 4. Убедитесь что ключ активен на https://platform.openai.com/api-keys
```

---

## Готово! 🚀

Теперь Codex может работать без GUI браузера на любой машине!
