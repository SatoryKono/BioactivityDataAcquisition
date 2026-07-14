# Codex Device Auth Setup Guide

## ⚠️ Важно: Device-auth не работает в текущем окружении

В вашем сетевом окружении device-auth не работает из-за проблем с DNS:
- ❌ `codex login --device-auth` не работает в WSL
- ❌ `codex login --device-auth` не работает в Windows
- Ошибка: `error sending request for url (https://auth.openai.com/api/accounts/deviceauth/usercode)`

## ✅ Рекомендуемое решение: API ключ метод

Используйте `QUICK_LOGIN_GUIDE.md` для настройки входа через API ключ - это простое и рабочее решение.

## Обзор

Device Auth позволяет аутентифицироваться в Codex без передачи API ключа через командную строку, используя браузер для авторизации.

## Проблема с DNS в WSL

При попытке использовать `codex login --device-auth` в WSL может возникнуть ошибка:
```
Error logging in with device code: error sending request for url (https://auth.openai.com/api/accounts/deviceauth/usercode)
```

Это связано с проблемами DNS резолвинга в WSL. Сеть работает (ping до IP адресов работает), но доменные имена не резолвятся.

## Решение 1: Настройка DNS в WSL

### Шаг 1: Отключить автоматическую генерацию resolv.conf

Создайте или отредактируйте `/etc/wsl.conf`:

```bash
sudo bash -c 'cat > /etc/wsl.conf << EOF
[network]
generateResolvConf = false
EOF'
```

### Шаг 2: Настроить статический DNS

Отредактируйте `/etc/resolv.conf`:

```bash
sudo bash -c 'cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF'
```

### Шаг 3: Защитить resolv.conf от перезаписи

```bash
sudo chattr +i /etc/resolv.conf
```

### Шаг 4: Перезапустить WSL

```powershell
# В PowerShell (администратор)
wsl --shutdown
# Затем снова запустите WSL
wsl
```

### Шаг 5: Проверить DNS

```bash
# Проверить резолвинг домена
ping auth.openai.com

# Если работает, попробовать device-auth
codex login --device-auth
```

## Решение 2: Использовать Windows для device-auth

Если DNS в WSL не работает, можно выполнить device-auth через Windows:

### Шаг 1: Установить cloudflared в Windows (уже установлено)

```powershell
cd "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex"
.\cloudflared.exe --version
```

### Шаг 2: Установить Codex CLI в Windows

```powershell
# Через npm
npm install -g @openai/codex-cli

# Или через официальный установщик
# Скачайте с https://github.com/openai/openai-codex/releases
```

### Шаг 3: Выполнить device-auth в Windows

```powershell
codex login --device-auth
```

Это откроет браузер с URL авторизации. После успешной авторизации учетные данные будут сохранены в Windows.

### Шаг 4: Скопировать учетные данные в WSL

```bash
# В WSL
mkdir -p ~/.codex
# Скопируйте файлы из Windows ~/.codex в WSL ~/.codex
# Через /mnt/c/Users/YourUsername/.codex/
```

## Решение 3: Использовать API ключ (рекомендено для WSL)

Так как device-auth имеет проблемы с DNS в WSL, рекомендуется использовать метод с API ключом:

### Шаг 1: Создать .env.codex файл

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
cat .env.codex
```

Убедитесь, что файл содержит:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### Шаг 2: Выполнить вход с API ключом

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
source .env.codex
echo $OPENAI_API_KEY | codex login --with-api-key
```

### Шаг 3: Проверить статус

```bash
codex login status
```

## Решение 4: Временное использование прокси

Если проблема с DNS сохраняется, можно использовать прокси:

### Шаг 1: Настроить HTTP прокси

```bash
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port
```

### Шаг 2: Попробовать device-auth

```bash
codex login --device-auth
```

## Текущая ситуация

В вашем случае:
- ✅ Codex CLI установлен в WSL (версия 0.144.3)
- ✅ API ключ настроен в `.env.codex`
- ✅ Аутентификация через `--with-api-key` работает успешно
- ❌ Device-auth не работает из-за проблем с DNS в WSL
- ✅ Сеть работает (ping до IP адресов работает)
- ❌ DNS резолвинг доменных имен не работает

## Рекомендация

Для текущей настройки рекомендуется использовать метод с API ключом (`--with-api-key`), так как:
1. Он работает стабильно в вашей среде
2. Не требует настройки DNS
3. Более безопасен для автоматизированных скриптов
4. Уже успешно настроен

Если вам конкретно нужен device-auth (например, для передачи устройства другому пользователю), то:
1. Сначала настройте DNS в WSL (Решение 1)
2. Или используйте Windows для device-auth (Решение 2)

## Проверка текущей аутентификации

```bash
# Проверить статус входа
codex login status

# Если не авторизован, использовать API ключ
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
source .env.codex
echo $OPENAI_API_KEY | codex login --with-api-key
```

## Полезные команды

```bash
# Проверить DNS резолвинг
ping auth.openai.com
nslookup auth.openai.com

# Проверить сетевое подключение
ping 8.8.8.8
curl -I https://www.google.com

# Проверить текущий DNS
cat /etc/resolv.conf

# Проверить WSL конфигурацию
cat /etc/wsl.conf

# Перезапустить WSL (из PowerShell)
wsl --shutdown
```

## Автоматизация

Для автоматического входа можно добавить в `~/.bashrc`:

```bash
# Auto-login to Codex
if [ -f "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/.env.codex" ]; then
    export OPENAI_API_KEY=$(grep OPENAI_API_KEY /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/.env.codex | cut -d '=' -f2)
    if ! codex login status > /dev/null 2>&1; then
        echo $OPENAI_API_KEY | codex login --with-api-key > /dev/null 2>&1
    fi
fi
```

## Вывод

Device-auth в WSL имеет проблемы с DNS в вашей текущей конфигурации. Рекомендуется использовать метод с API ключом, который уже работает стабильно. Если вам нужен именно device-auth, настройте DNS в WSL или используйте Windows для аутентификации.
