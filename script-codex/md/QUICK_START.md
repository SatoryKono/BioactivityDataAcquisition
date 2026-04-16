# Codex - Quick Start Guide

## Структура папки `script-codex`

Здесь находятся все скрипты для запуска Codex на безголовой машине.

## Первый раз: Настройка

### 1. Отредактируйте `.env.codex`

```powershell
notepad script-codex\.env.codex
```

Добавьте ваш API key:

```
OPENAI_API_KEY=sk-your-key-here
```

Сохраните файл.

### 2. Запустите

```powershell
cd script-codex
.\run-codex.ps1 login
```

Это загрузит API key и запустит Codex.

## Использование

### Интерактивный режим

```powershell
cd script-codex
.\run-codex.ps1
.\run-codex.ps1 "analyze the code"
```

### Автоматический режим

```powershell
cd script-codex
.\run-codex.ps1 exec "refactor the parser"
```

### Device Auth (для безголовой машины)

```powershell
cd script-codex
.\run-codex.ps1 device-login
```

Потом используйте нормально:

```powershell
.\run-codex.ps1 "your prompt"
```

## Все команды

```powershell
.\run-codex.ps1 help                    # Показать справку
.\run-codex.ps1                         # Интерактивный режим
.\run-codex.ps1 "your prompt"          # С промтом
.\run-codex.ps1 start "your prompt"    # Явно интерактивный
.\run-codex.ps1 exec "your prompt"     # Авто-режим
.\run-codex.ps1 login                  # Логин с API key
.\run-codex.ps1 device-login           # Device auth логин
```

## Где получить API key

https://platform.openai.com/api-keys

1. Откройте ссылку
2. "Create new secret key"
3. Скопируйте (начинается с `sk-`)
4. Вставьте в `.env.codex`

## Готово! 🚀

Теперь у вас есть всё для запуска Codex на любой машине!
