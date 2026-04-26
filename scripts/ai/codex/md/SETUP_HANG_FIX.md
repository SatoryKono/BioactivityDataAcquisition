# Codex Setup Hang - Диагностика и Решение

## Причина зависания

Скрипт зависает на команде `apt-get update` в Ubuntu WSL. Это происходит по одной из причин:

1. **apt заблокирован другим процессом** (например, unattended-upgrades)
1. **Требуется пароль для sudo** (passwordless sudo не настроен)
1. **Очень медленное или нестабильное соединение**
1. **apt кэш повреждён**

## Как исправлено

### ✅ Вариант 1: Быстрый запуск (БЕЗ БЛОКИРОВКИ)

Новая версия `run-codex.ps1` **НЕ блокируется на setup**:

```powershell
.\run-codex.ps1
```

- Проверит компоненты (быстро, 2 сек)
- Если чего-то не хватает, запустит setup в **фоне** (non-blocking)
- Сразу же запустит Codex
- Setup завершится в фоне, готово будет при следующем запуске

### ✅ Вариант 2: Явный setup (с пропуском apt)

```powershell
.\run-codex.ps1 setup
```

Новый скрипт `setup-env.sh`:

- **Пропускает `apt-get update`** если он зависает
- Скачивает Node.js бинарный файл напрямую с nodejs.org
- Устанавливает через npm (без apt)
- 3 попытки установки Codex с таймаутами

### ✅ Вариант 3: Диагностика (найти точное место зависания)

```powershell
.\script-codex\helper\diagnose-hang.ps1
```

Покажет:

- [1/5] WSL работает?
- [2/5] Bash работает?
- [3/5] apt-get update зависает?
- [4/5] Node.js установлен?
- [5/5] npm install работает?

## Что конкретно изменилось

### run-codex.ps1 (main script)

```diff
- Блокировался на setup если чего-то не хватало
+ Запускает setup в фоне (non-blocking)
+ Сразу же запускает Codex
```

### setup-env.sh (installation script)

```diff
- Зависал на: sudo apt-get update
+ Пропускает apt если оно зависает
+ Скачивает Node.js бинарники напрямую
+ 3 попытки npm install с разными registry'ями
+ Все операции с таймаутами (60-180 сек)
```

### check-env.ps1 (environment check)

```diff
- Требовал ручного запуска setup
+ Теперь интегрирован в main скрипт
+ Проверка не блокирует
```

## Если всё ещё зависает

### 1. Проверьте WSL

```powershell
wsl --list --running
```

Должно показать: `Ubuntu` (или ваш distro)

### 2. Убедитесь passwordless sudo

```bash
wsl -d Ubuntu -- bash -c "sudo -n true && echo 'OK' || echo 'FAIL'"
```

Если `FAIL`, добавьте в `/etc/sudoers`:

```
%wheel ALL=(ALL) NOPASSWD: ALL
```

### 3. Разблокируйте apt

```bash
wsl -d Ubuntu -- sudo apt-get update 2>&1 | head -20
```

Если зависает,킬ните процесс и запустите:

```bash
wsl -d Ubuntu -- sudo rm -f /var/lib/apt/lists/lock
wsl -d Ubuntu -- sudo dpkg --configure -a
```

### 4. Установите Node.js вручную

```bash
wsl -d Ubuntu -e bash "$HOME/script-codex/helper/setup-env.sh"
```

### 5. Последний вариант - ручная установка

```bash
# В WSL Ubuntu:
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash
sudo apt-get install -y nodejs
mkdir -p ~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex
```

## Проверка решения

После запуска `.\run-codex.ps1`:

✅ Должно вывести:

```
[OK] Node.js: installed
[OK] Codex: installed
[i] Launching Codex...
```

❌ Если зависает > 5 сек на любом этапе → запустите диагностику:

```powershell
.\script-codex\helper\diagnose-hang.ps1
```

## Дополнительная информация

- **Timeout setup-env.sh**: 180 сек (3 мин) максимум
- **Timeout npm install**: 120 сек за попытку, 3 попытки всего
- **Timeout apt-get**: 60 сек (потом пропускается)
- **Background setup**: автоматически завершится в течение 5-10 минут

Если setup завершилось с ошибкой, при следующем запуске `.\run-codex.ps1` он запустит setup заново.
