# Cloudflare Tunnel Setup для BioETL

## Обзор

Этот документ описывает настройку Cloudflare Tunnel для доступа к локальным сервисам проекта BioETL через Cloudflare.

## Предварительные требования

- ✅ Cloudflared установлен: `scripts/ai/codex/cloudflared.exe` (версия 2026.7.1)
- ✅ Cloudflare аккаунт
- 🔄 Домен в Cloudflare (требуется для настройки)

## Шаг 1: Авторизация в Cloudflare

Выполните следующую команду из папки `scripts/ai/codex`:

```powershell
cd "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex"
.\cloudflared.exe tunnel login
```

Это откроет браузер с URL авторизации:
```
https://dash.cloudflare.com/argotunnel?aud=&callback=...
```

**Действия в браузере:**
1. Войдите в свой Cloudflare аккаунт
2. Выберите домен, который будет использоваться для туннеля
3. Разрешите доступ cloudflared к вашему аккаунту

После успешной авторизации будет создан файл сертификата:
```
%USERPROFILE%\.cloudflared\cert.pem
```

## Шаг 2: Создание туннеля

После авторизации создайте новый туннель:

```powershell
.\cloudflared.exe tunnel create bioetl-local
```

Эта команда вернёт:
- Tunnel ID (например: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
- Имя туннеля: `bioetl-local`

Сохраните Tunnel ID для дальнейшей настройки.

## Шаг 3: Настройка конфигурации туннеля

Создайте файл конфигурации `config.yml`:

```powershell
notepad "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex\config.yml"
```

Добавьте следующую конфигурацию:

```yaml
tunnel: <TUNNEL_ID>  # Замените на ваш Tunnel ID из шага 2
credentials-file: C:\Users\<USERNAME>\.cloudflared\<TUNNEL_ID>.json

ingress:
  # Пример: доступ к Grafana
  - hostname: grafana.yourdomain.com
    service: http://localhost:3000

  # Пример: доступ к Prometheus
  - hostname: prometheus.yourdomain.com
    service: http://localhost:9090

  # Пример: доступ к локальному веб-приложению
  - hostname: bioetl.yourdomain.com
    service: http://localhost:8000

  # Fallback для всех остальных запросов
  - service: http_status:404
```

**Важно:**
- Замените `<TUNNEL_ID>` на ваш ID из шага 2
- Замените `<USERNAME>` на ваше имя пользователя Windows
- Замените `yourdomain.com` на ваш домен в Cloudflare
- Настройте `hostname` и `service` для ваших локальных сервисов

## Шаг 4: Настройка DNS записей

Для каждого `hostname` в конфигурации создайте CNAME запись в Cloudflare DNS:

```powershell
# Для Grafana
.\cloudflared.exe tunnel route dns bioetl-local grafana.yourdomain.com

# Для Prometheus
.\cloudflared.exe tunnel route dns bioetl-local prometheus.yourdomain.com

# Для основного приложения
.\cloudflared.exe tunnel route dns bioetl-local bioetl.yourdomain.com
```

Или создайте записи вручную в Cloudflare Dashboard:
1. Перейдите в DNS → Records
2. Добавьте CNAME запись:
   - Name: `grafana` (или другое имя)
   - Target: `<TUNNEL_ID>.cfargotunnel.com`
   - Proxy status: Proxied (оранжевое облако)

## Шаг 5: Запуск туннеля

### Ручной запуск

```powershell
cd "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex"
.\cloudflared.exe tunnel --config config.yml run bioetl-local
```

### Запуск как службы Windows

Установите cloudflared как службу:

```powershell
# Установка службы
.\cloudflared.exe service install

# Настройка пути к конфигурации
# Отредактируйте параметры службы через sc.exe или services.msc
```

Или используйте PowerShell для создания службы:

```powershell
# Создание службы
New-Service -Name "CloudflareTunnel" `
    -BinaryPathName "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex\cloudflared.exe tunnel --config E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex\config.yml run bioetl-local" `
    -DisplayName "Cloudflare Tunnel for BioETL" `
    -StartupType Automatic

# Запуск службы
Start-Service -Name "CloudflareTunnel"
```

## Шаг 6: Проверка подключения

1. Убедитесь, что туннель запущен без ошибок
2. Откройте в браузере настроенные URL:
   - `https://grafana.yourdomain.com`
   - `https://prometheus.yourdomain.com`
   - `https://bioetl.yourdomain.com`

## Дополнительные настройки

### Безопасность

1. **Access Policies** в Cloudflare Zero Trust:
   - Настройте правила доступа для каждого hostname
   - Добавьте аутентификацию (Email OTP, Google Auth, и т.д.)
   - Ограничьте доступ по IP или геолокации

2. **SSL/TLS**:
   - Убедитесь, что SSL/TLS режим установлен в "Full" или "Full (strict)"
   - Настройте сертификаты для локальных сервисов при необходимости

### Мониторинг

- Используйте Cloudflare Analytics для мониторинга трафика
- Настройте логирование через Cloudflare Logpush
- Мониторьте состояние туннеля через Cloudflare Dashboard

## Устранение проблем

### Туннель не запускается

```powershell
# Проверка конфигурации
.\cloudflared.exe tunnel --config config.yml run bioetl-local --debug

# Проверка сертификата
.\cloudflared.exe cert check
```

### DNS записи не работают

1. Проверьте, что CNAME записи указывают на правильный target: `<TUNNEL_ID>.cfargotunnel.com`
2. Убедитесь, что Proxy status установлен в "Proxied"
3. Проверьте, что туннель запущен и активен

### Проблемы с доступом

1. Проверьте Access Policies в Cloudflare Zero Trust
2. Убедитесь, что локальные сервисы запущены и доступны на указанных портах
3. Проверьте firewall на Windows

## Полезные команды

```powershell
# Список туннелей
.\cloudflared.exe tunnel list

# Информация о туннеле
.\cloudflared.exe tunnel info bioetl-local

# Удаление туннеля
.\cloudflared.exe tunnel delete bioetl-local

# Очистка сертификата
.\cloudflared.exe tunnel cleanup <TUNNEL_ID>
```

## Интеграция с BioETL

После настройки туннеля вы можете:

1. Давать удалённый доступ к Grafana дашбордам
2. Предоставлять доступ к Prometheus метрикам
3. Создавать публичные endpoints для API
4. Настраивать webhook callbacks для внешних сервисов

## Безопасность

- 🔒 Всегда используйте Access Policies для защиты endpoints
- 🔒 Ограничивайте доступ по IP где возможно
- 🔒 Используйте HTTPS для всех соединений
- 🔒 Регулярно обновляйте cloudflared
- 🔒 Мониторьте логи доступа на предмет подозрительной активности

## Поддержка

- Cloudflare Documentation: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Cloudflare Community: https://community.cloudflare.com/
- BioETL Project Documentation: `docs/05-operations/`
