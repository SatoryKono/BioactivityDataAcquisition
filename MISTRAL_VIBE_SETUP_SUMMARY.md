# Резюме: Анализ Codex vs Mistral Vibe и План настройки

## 🔍 Основные различия архитектур

### Codex (✅ Исправлен)
- **CLI:** JavaScript/Node.js
- **Установка:** `npm install -g @openai/codex`
- **Точка входа:** `scripts/ai/codex/run-codex.sh`
- **Конфиг:** `scripts/ai/codex/.env.codex`
- **Таймауты:** ✅ Добавлены (5-120 сек)
- **Retry логика:** ✅ Макс 2 повторения

### Mistral Vibe (⚠️ Требует улучшений)
- **CLI:** Python
- **Установка:** `pip install mistral-vibe`
- **Точка входа:** `scripts/ai/vibe/launch.sh` (canonical)
- **Конфиг:** `scripts/ai/mistrallvibe/.env.mistrallvibe`
- **Таймауты:** ❌ Отсутствуют
- **Retry логика:** ❌ Отсутствует

---

## 📋 6-фазный план настройки Mistral Vibe

### **Фаза 1: Таймауты в check-env.sh** (Высокий приоритет)
**Файл:** `./scripts/ai/mistrallvibe/helper/check-env.sh`

Добавить таймауты:
- `timeout 5 git rev-parse` — проверка git репозитория
- `timeout 10 command -v vibe` — проверка установки Vibe
- `timeout 10 python3 --version` — проверка Python

```bash
# ПЕРЕД
if command -v vibe >/dev/null 2>&1; then

# ПОСЛЕ
if timeout 10 bash -c "command -v vibe >/dev/null 2>&1"; then
```

---

### **Фаза 2: Таймауты и retry в setup-env.sh** (Высокий приоритет)
**Файл:** `./scripts/ai/mistrallvibe/helper/setup-env.sh`

Добавить:
- Таймауты на pip/pipx install (60 сек)
- Лимит повторов установки (макс 2 попытки)
- Проверку PATH после установки

```bash
# ПЕРЕД
if pipx install mistral-vibe; then

# ПОСЛЕ
RETRY=0
MAX_RETRIES=2
while [[ $RETRY -lt $MAX_RETRIES ]]; do
    if timeout 60 pipx install mistral-vibe; then
        break
    fi
    RETRY=$((RETRY + 1))
done
```

---

### **Фаза 3: Таймауты в run-vibe.ps1** (Средний приоритет)
**Файл:** `./scripts/ai/mistrallvibe/run-vibe.ps1`

Добавить:
- Таймауты на WSL вызовы (30 сек)
- Обработку ошибок при зависании
- Retry логику для вызовов helper скриптов

```powershell
# ПЕРЕД
& (Join-Path $HelperDir "check-env.ps1")

# ПОСЛЕ
$job = Start-Job -ScriptBlock { & (Join-Path $HelperDir "check-env.ps1") }
$result = Wait-Job -Job $job -Timeout 30
if ($result) {
    Receive-Job -Job $job
} else {
    Write-Error "Проверка вышла по таймауту"
    Stop-Job -Job $job -PassThru | Remove-Job
}
```

---

### **Фаза 4: Таймауты в vibe/launch.sh** (Средний приоритет)
**Файл:** `./scripts/ai/vibe/launch.sh`

Добавить:
- Таймауты на проверки файлов (5 сек)
- Graceful fallback если файл недоступен
- Retry для загрузки конфигов

```bash
# ПЕРЕД
if [[ -f "${HOME}/.local/bin/env" ]]; then
    source "${HOME}/.local/bin/env" 2>/dev/null || true
fi

# ПОСЛЕ
if timeout 5 test -f "${HOME}/.local/bin/env" 2>/dev/null; then
    if timeout 5 bash -c "source '${HOME}/.local/bin/env'" 2>/dev/null; then
        source "${HOME}/.local/bin/env" 2>/dev/null || true
    fi
fi
```

---

### **Фаза 5: Создание launch-interactive.ps1** (Низкий приоритет)
**Новый файл:** `./scripts/ai/mistrallvibe/launch-interactive.ps1`

Скопировать из `codex/launch-interactive.ps1`:
- Попытка открыть Windows Terminal
- Fallback на прямой WSL вызов
- Четкие инструкции для пользователя

```powershell
wsl -d Ubuntu bash -i -c "cd '$ScriptPathWSL' && bash run-vibe.sh"
```

---

### **Фаза 6: Создание HOW_TO_RUN_VIBE.md** (Низкий приоритет)
**Новый файл:** `./HOW_TO_RUN_VIBE.md`

Содержит:
- Статус компонентов (Python, pip, vibe, .env.mistrallvibe)
- 4 способа запуска (Windows Terminal, WSL, одна команда, автоматический режим)
- Команды диагностики (`.\run-vibe.ps1 check`)
- Решение проблем (PATH, pip зависания и т.д.)

---

## 🚀 Порядок реализации

### **Срочно (Сегодня)**
1. ✅ Фаза 1: Таймауты в check-env.sh
2. ✅ Фаза 2: Таймауты в setup-env.sh
3. ✅ Фаза 4: Таймауты в vibe/launch.sh

### **Важно (На неделю)**
4. ✅ Фаза 3: Таймауты в run-vibe.ps1
5. ✅ Фаза 5: launch-interactive.ps1

### **Дополнительно (Опционально)**
6. ✅ Фаза 6: HOW_TO_RUN_VIBE.md

---

## 📊 Сравнительная таблица

| Компонент | Codex | Mistral Vibe | Статус |
|-----------|-------|--------------|--------|
| **git rev-parse таймаут** | ✅ 5s | ❌ Нет | Нужен |
| **command -v таймаут** | ✅ 10s | ❌ Нет | Нужен |
| **pip install таймаут** | N/A | ❌ Нет | Нужен |
| **Retry логика** | ✅ 2 попытки | ❌ Нет | Нужна |
| **Graceful fallback** | ✅ Есть | ❌ Нет | Нужен |
| **PATH проверка** | ✅ Есть | ⚠️ Неполная | Нужна |
| **Интерактивный launcher** | ✅ launch-interactive.ps1 | ❌ Нет | Нужен |
| **HOW_TO документ** | ✅ HOW_TO_RUN_CODEX.md | ❌ Нет | Нужен |

---

## ⚠️ Критические проблемы Mistral Vibe

1. **pip install может зависнуть** на slow networks — нужен 60s таймаут
2. **PATH может не обновиться** после install — нужна проверка
3. **git rev-parse зависает** при больших репозиториях — нужен 5s таймаут
4. **Нет retry логики** при ошибках — может потребоваться ручной перезапуск
5. **Интерактивный режим не работает** из PowerShell — нужен WSL терминал

---

## ✅ Что уже работает

- ✅ Базовая структура PowerShell скриптов
- ✅ Система логирования с цветами
- ✅ Разделение на check/setup команды
- ✅ Чтение конфигурации из .env.mistrallvibe
- ✅ Делегирование на canonical launcher (scripts/ai/vibe/)

---

## 📝 Документация

- `MISTRAL_VIBE_SETUP_PLAN.md` — подробный план (этот файл в расширенном виде)
- `HOW_TO_RUN_CODEX.md` — пример для Codex (используйте как образец)
- `scripts/ai/mistrallvibe/README.md` — текущая документация (требует обновления)

