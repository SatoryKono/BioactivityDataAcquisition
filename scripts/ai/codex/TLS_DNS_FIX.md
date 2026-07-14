# TLS/DNS Fix for Device-Auth

## Проблема

Device-auth не работает из-за проблем с DNS резолвингом в WSL:
- ❌ `codex login --device-auth` не может подключиться к `https://auth.openai.com/api/accounts/deviceauth/usercode`
- ❌ Команды с `sudo` в WSL зависают (требуют интерактивный ввод пароля)
- ✅ Сеть работает (ping до IP адресов успешен)
- ❌ DNS резолвинг доменных имен не работает

## Диагностика

### IP адрес auth.openai.com
```
104.18.41.241
172.64.146.15
```

### Текущий DNS в WSL
```
nameserver 172.26.16.1 (WSL default)
```

## Решения

### Вариант 1: Ручная настройка /etc/hosts (требует sudo)

Выполните в WSL:

```bash
# Отредактируйте /etc/hosts вручную
sudo nano /etc/hosts

# Добавьте строку:
104.18.41.241 auth.openai.com

# Сохраните и выйдите (Ctrl+X, Y, Enter)
```

После этого попробуйте device-auth:
```bash
codex login --device-auth
```

### Вариант 2: Настройка DNS в Windows (рекомендуется)

Так как WSL использует DNS Windows, настройте DNS в Windows:

1. **Откройте настройки сети:**
   - Windows Settings → Network & Internet
   - Change adapter options
   - Правый клик на вашем адаптере → Properties
   - Internet Protocol Version 4 (TCP/IPv4) → Properties

2. **Используйте следующие DNS:**
   ```
   Preferred DNS server: 8.8.8.8
   Alternate DNS server: 8.8.4.4
   ```

3. **Перезапустите WSL:**
   ```powershell
   wsl --shutdown
   wsl
   ```

4. **Протестируйте device-auth:**
   ```bash
   codex login --device-auth
   ```

### Вариант 3: Использовать прокси

Если DNS не работает, можно использовать HTTP прокси:

```bash
# Установите переменные окружения
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port

# Попробуйте device-auth
codex login --device-auth
```

### Вариант 4: Продолжить использовать API ключ (рекомендуется)

API ключ метод уже работает стабильно:

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
source .env.codex
echo $OPENAI_API_KEY | codex login --with-api-key
```

## Почему sudo команды зависают

Команды с `sudo` в WSL зависают, потому что:
1. Требуют интерактивный ввод пароля
2. В автоматических скриптах нет возможности ввода пароля
3. WSL может не иметь правильной настройки sudoers

## Проверка работы DNS после настройки

После настройки DNS проверьте:

```bash
# Проверка резолвинга
ping auth.openai.com

# Проверка HTTPS соединения
curl -I https://auth.openai.com

# Проверка device-auth
codex login --device-auth
```

## Рекомендация

Для вашего окружения **рекомендуется**:

1. **Настроить DNS в Windows** (Вариант 2) - это решит проблему глобально
2. **Или продолжить использовать API ключ** (Вариант 4) - это простое и рабочее решение

Настройка /etc/hosts через sudo проблематична из-за требований интерактивного ввода пароля.

## Текущий статус

✅ **API ключ метод работает стабильно**
❌ **Device-auth не работает из-за DNS**
⚠️ **Sudo команды в WSL зависают (требуют пароль)**
✅ **Сеть работает (ping до IP успешен)**
❌ **DNS резолвинг не работает**

## Документация

- `QUICK_LOGIN_GUIDE.md` - руководство по API ключ методу
- `DEVICE_AUTH_SETUP.md` - полное руководство по device-auth
- `setup-wsl-dns.sh` - скрипт настройки DNS (требует ручного выполнения sudo команд)