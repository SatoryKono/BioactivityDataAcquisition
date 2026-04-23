# Анализ различий Codex vs Mistral Vibe и План настройки Mistral Vibe

## 📊 Сравнение архитектур

### Codex
```
run-codex.ps1 (PowerShell)
├─ Делегирует → WSL (wsl bash)
├─ run-codex.sh (bash)
│  ├─ check-env.sh
│  ├─ setup-env.sh
│  └─ run-codex-impl.sh
└─ Устанавливает Node.js/npm → npm install @openai/codex
```

**Архитектура:** 
- ✅ Запускается ИЗ Windows через WSL
- ✅ Использует npm для установки
- ✅ Требует OPENAI_API_KEY в .env.codex
- ✅ Все компоненты в scripts/ai/codex/

### Mistral Vibe
```
run-vibe.ps1 (PowerShell)
├─ Делегирует → scripts/ai/vibe/launch.ps1
├─ run-vibe.sh (bash)
│  ├─ Делегирует → scripts/ai/vibe/launch.sh (canonical)
│  └─ helper/ (check-env.sh, setup-env.sh)
└─ vibe/launch.sh
   ├─ Устанавливает Python → pip install mistral-vibe
   ├─ Читает .env.mistrallvibe
   └─ Запускает: vibe --workdir REPO_ROOT
```

**Архитектура:**
- ✅ Использует каноническую точку входа (scripts/ai/vibe/)
- ✅ Использует Python/pip для установки
- ✅ Требует MISTRAL_API_KEY в .env.mistrallvibe
- ⚠️ Миграция: mistrallvibe/helper → вспомогательные скрипты
- ⚠️ Настройки рассеяны в двух местах (mistrallvibe/ и vibe/)

---

## 🔍 Ключевые различия

| Аспект | Codex | Mistral Vibe |
|--------|-------|--------------|
| **Язык CLI** | JavaScript/Node | Python |
| **Установка** | npm install -g @openai/codex | pip install mistral-vibe |
| **Конфиг** | .env.codex | .env.mistrallvibe |
| **API ключ** | OPENAI_API_KEY | MISTRAL_API_KEY |
| **Путь лаунчера** | scripts/ai/codex/ | scripts/ai/vibe/ (canonical) |
| **Таймауты** | ✅ Добавлены | ❌ Отсутствуют |
| **Retry логика** | ✅ Лимит 2 повторения | ❌ Нет |
| **Проверка PATH** | PowerShell | bash (не через PowerShell) |
| **Интерактивный режим** | Требует терминала | Требует терминала |

---

## 🎯 План настройки Mistral Vibe (применив опыт Codex)

### Фаза 1: Обогащение check-env.sh с таймаутами ✅

**Файл:** `./scripts/ai/mistrallvibe/helper/check-env.sh`

Добавить:
1. Таймауты на команды проверки (особенно `git rev-parse`)
2. Проверку PATH для ~/.local/bin
3. Graceful fallback при ошибках

```bash
# BEFORE
if command -v vibe >/dev/null 2>&1; then

# AFTER
if timeout 10 command -v vibe >/dev/null 2>&1; then
```

### Фаза 2: Обогащение setup-env.sh с таймаутами ✅

**Файл:** `./scripts/ai/mistrallvibe/helper/setup-env.sh`

Добавить:
1. Таймауты на pip/pipx install (60 сек)
2. Лимит повторов при установке (макс 2 попытки)
3. Проверка PATH после установки

```bash
# BEFORE
if pipx install mistral-vibe; then

# AFTER
if timeout 60 pipx install mistral-vibe; then
    # После установки добавить PATH проверку
fi
```

### Фаза 3: Обновление run-vibe.ps1 ✅

**Файл:** `./scripts/ai/mistrallvibe/run-vibe.ps1`

Добавить:
1. Диагностику (как в Codex)
2. Обработку команды `check` полноценно (не только запуск helper)
3. Обработку команды `setup` полноценно
4. Таймауты для WSL вызовов

```powershell
# BEFORE
& (Join-Path $HelperDir "check-env.ps1")

# AFTER
# Добавить таймауты и обработку ошибок
$job = Start-Job -ScriptBlock { & (Join-Path $HelperDir "check-env.ps1") }
$result = Wait-Job -Job $job -Timeout 30
```

### Фаза 4: Улучшение vibe/launch.sh ✅

**Файл:** `./scripts/ai/vibe/launch.sh`

Добавить:
1. Таймауты на проверки (git rev-parse)
2. Retry логику при неудачных попытках доступа к файлам
3. Graceful fallback если Vibe не установлен

```bash
# BEFORE
if [[ -f "${HOME}/.local/bin/env" ]]; then

# AFTER
if timeout 5 test -f "${HOME}/.local/bin/env"; then
```

### Фаза 5: Создание launch-interactive.ps1 ✅

**Новый файл:** `./scripts/ai/mistrallvibe/launch-interactive.ps1`

Скопировать логику из Codex для открытия интерактивного режима:
- Пытаться открыть Windows Terminal
- Fallback на прямой WSL вызов
- Четкие инструкции если терминал недоступен

### Фаза 6: Создание HOW_TO_RUN_VIBE.md ✅

**Новый файл:** `./scripts/ai/mistrallvibe/HOW_TO_RUN_VIBE.md`

Аналогично `HOW_TO_RUN_CODEX.md`:
- Статус компонентов
- 4 варианта запуска
- Команды диагностики
- Решение проблем

---

## 📋 Список изменяемых файлов

### Обновление (изменить существующие)
1. ✅ `./scripts/ai/mistrallvibe/helper/check-env.sh` → добавить таймауты
2. ✅ `./scripts/ai/mistrallvibe/helper/check-env.ps1` → добавить таймауты
3. ✅ `./scripts/ai/mistrallvibe/helper/setup-env.sh` → добавить таймауты и retry
4. ✅ `./scripts/ai/mistrallvibe/helper/setup-env.ps1` → добавить таймауты
5. ✅ `./scripts/ai/mistrallvibe/run-vibe.ps1` → улучшить диагностику
6. ✅ `./scripts/ai/vibe/launch.sh` → добавить таймауты

### Создание (новые файлы)
1. ✅ `./scripts/ai/mistrallvibe/launch-interactive.ps1` → интерактивный запуск
2. ✅ `./HOW_TO_RUN_VIBE.md` → инструкции пользователя
3. ✅ `./MISTRAL_VIBE_FIXES.md` → документация применённых исправлений

---

## 🚀 Приоритет исправлений

**Высокий приоритет (критические):**
1. Таймауты на pip install (60 сек) — может зависать
2. Таймауты на git rev-parse (5 сек) — может зависать
3. Проверка PATH после установки — может не работать после install

**Средний приоритет (важное):**
4. Лимит повторов при неудачных проверках (макс 2)
5. Graceful fallback при отсутствии Vibe
6. Интерактивный launcher (launch-interactive.ps1)

**Низкий приоритет (улучшение):**
7. Улучшенная диагностика в PowerShell
8. Документация и инструкции

---

## ✅ Выполнено (применено из Codex)

- ✅ Структура PowerShell скриптов (аналогия)
- ✅ Система логирования с цветами
- ✅ Разделение на check/setup команд
- ✅ Использование helper скриптов
- ✅ Чтение конфига из .env файла

---

## ⚠️ Что НЕ НУЖНО делать

❌ Переносить Vibe из `scripts/ai/vibe/` в `scripts/ai/mistrallvibe/`
❌ Дублировать логику (используйте каноническую точку входа)
❌ Изменять API Mistral — только добавлять параметры
❌ Требовать обновление версии Vibe — быть совместимым

