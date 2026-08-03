# Codex Login Guide - Working Solution

## Проблема с Device-Auth

Device-auth не работает в вашем сетевом окружении из-за проблем с DNS/сетью:
- ❌ `codex login --device-auth` не работает в WSL
- ❌ `codex login --device-auth` не работает в Windows
- Ошибка: `error sending request for url (https://auth.openai.com/api/accounts/deviceauth/usercode)`

## ✅ Рабочее решение: API ключ метод

API ключ метод уже работает стабильно в вашей среде и является рекомендуемым решением.

## Быстрый старт

### Однократная настройка

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
source .env.codex
echo $OPENAI_API_KEY | codex login --with-api-key
```

### Проверка статуса

```bash
codex login status
```

Ожидаемый результат:
```
Logged in using an API key - sk-proj-***E9osA
```

## Автоматизация входа

### Добавить в ~/.bashrc

Добавьте следующие строки в ваш `~/.bashrc`:

```bash
# Auto-login to Codex
if [ -f "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/.env.codex" ]; then
    export OPENAI_API_KEY=$(grep OPENAI_API_KEY /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex/.env.codex | cut -d '=' -f2)
    if ! codex login status > /dev/null 2>&1; then
        echo $OPENAI_API_KEY | codex login --with-api-key > /dev/null 2>&1
    fi
fi
```

После этого перезагрузите shell:
```bash
source ~/.bashrc
```

### Использовать скрипт входа

Создайте скрипт `login-codex.sh`:

```bash
#!/bin/bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
source .env.codex
echo $OPENAI_API_KEY | codex login --with-api-key
```

Сделайте его исполняемым:
```bash
chmod +x login-codex.sh
```

Используйте когда нужно:
```bash
./login-codex.sh
```

## Запуск Codex

После входа используйте обычные команды:

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex

# Интерактивный режим
bash run-codex.sh

# С промтом
bash run-codex.sh "анализируй код"

# Автоматический режим
bash run-codex.sh exec "исправь ошибку"
```

## Безопасность API ключ метода

✅ **Безопасно, потому что:**
- API ключ хранится локально в `.env.codex`
- Файл не отслеживается в git (в .gitignore)
- Ключ уже используется в вашем окружении
- Современные API ключи имеют ограничения и можно отозвать

## Почему device-auth не работает

Проблема с DNS резолвингом в вашем сетевом окружении:
- Сеть работает (ping до IP адресов успешен)
- DNS резолвинг доменных имен не работает
- Это влияет на все попытки device-auth

## Рекомендации

1. **Используйте API ключ метод** - он работает стабильно
2. **Настройте автоматический вход** через ~/.bashrc
3. **Не тратьте время на device-auth** - проблема сетевая, не связана с Codex
4. **Если нужно device-auth** - сначала решите проблемы с DNS в сети

## Проверка работы

После входа проверьте работу Codex:

```bash
codex login status
codex --version
```

Запустите тестовый запрос:
```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
bash run-codex.sh "привет, тест"
```

## Текущий статус

✅ **API ключ метод работает:**
- Codex CLI установлен в WSL (версия 0.144.3)
- API ключ настроен в `.env.codex`
- Аутентификация успешна
- Все функции Codex доступны

❌ **Device-auth не работает:**
- Проблемы с DNS в сетевом окружении
- Не зависит от платформы (WSL/Windows)
- Требует настройки сети

## Вывод

Используйте API ключ метод - это простое, безопасное и рабочее решение для вашего окружения. Device-auth может быть полезен в других сетевых условиях, но в вашем случае API ключ метод является оптимальным выбором.
