# Windows DNS Setup Guide for Device-Auth

## Обзор

Настройка DNS в Windows решит проблемы с DNS резолвингом в WSL и позволит использовать device-auth для Codex.

## Автоматическая настройка (рекомендуется)

### Использование PowerShell скрипта

Запустите скрипт от имени администратора:

```powershell
# Запуск от имени администратора
cd "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\scripts\ai\codex"
.\setup-windows-dns.ps1
```

Этот скрипт автоматически:
1. Определит активный сетевой адаптер
2. Настроит DNS серверы (8.8.8.8, 8.8.4.4)
3. Перезапустит WSL
4. Протестирует DNS резолвинг

## Ручная настройка

### Шаг 1: Откройте настройки сети

1. Нажмите `Win + R` и введите `ncpa.cpl`
2. Или: Settings → Network & Internet → Change adapter options

### Шаг 2: Выберите сетевой адаптер

1. Найдите ваш активный сетевой адаптер (обычно "Ethernet" или "Wi-Fi")
2. Правый клик → Properties

### Шаг 3: Настройте DNS

1. Выберите "Internet Protocol Version 4 (TCP/IPv4)"
2. Нажмите Properties
3. Выберите "Use the following DNS server addresses"
4. Введите:
   ```
   Preferred DNS server: 8.8.8.8
   Alternate DNS server: 8.8.4.4
   ```
5. Нажмите OK → Close

### Шаг 4: Перезапустите WSL

```powershell
wsl --shutdown
wsl
```

### Шаг 5: Протестируйте DNS

В WSL выполните:

```bash
# Проверка резолвинга
ping auth.openai.com

# Проверка HTTPS
curl -I https://auth.openai.com

# Проверка device-auth
codex login --device-auth
```

## Проверка текущих настроек DNS

### В Windows

```powershell
# Показать текущие DNS для всех адаптеров
Get-DnsClientServerAddress -AddressFamily IPv4

# Показать DNS для конкретного адаптера
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" -AddressFamily IPv4
```

### В WSL

```bash
# Показать текущий DNS
cat /etc/resolv.conf

# Проверить резолвинг
ping auth.openai.com
```

## Устранение проблем

### DNS не применяется

1. Убедитесь, что вы запустили настройки от имени администратора
2. Перезагрузите компьютер
3. Отключите и включите сетевой адаптер

### WSL не видит новые DNS

1. Полностью перезапустите WSL: `wsl --shutdown`
2. Подождите 10-15 секунд перед запуском WSL
3. Проверьте `/etc/resolv.conf` в WSL

### Device-auth всё ещё не работает

1. Проверьте резолвинг: `ping auth.openai.com`
2. Проверьте HTTPS: `curl -I https://auth.openai.com`
3. Попробуйте альтернативный DNS: `1.1.1.1`, `1.0.0.1`

## Альтернативные DNS серверы

Если Google DNS не работают, попробуйте:

### Cloudflare DNS
```
Preferred: 1.1.1.1
Alternate: 1.0.0.1
```

### OpenDNS
```
Preferred: 208.67.222.222
Alternate: 208.67.220.220
```

### Quad9
```
Preferred: 9.9.9.9
Alternate: 149.112.112.112
```

## Возврат к автоматическому DNS

Если нужно вернуть автоматические настройки DNS:

### Через интерфейс
1. Откройте настройки сети (как выше)
2. Выберите "Obtain DNS server address automatically"
3. Нажмите OK

### Через PowerShell
```powershell
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ResetServerAddresses
```

## Влияние на другие приложения

Настройка DNS в Windows:
- ✅ Повлияет на все приложения в Windows
- ✅ Повлияет на WSL (использует DNS Windows)
- ✅ Может улучшить скорость интернета
- ⚠️ Может повлиять на корпоративные DNS настройки (если есть)

## Безопасность

Использование Google DNS (8.8.8.8):
- ✅ Безопасно и надежно
- ✅ Не логирует персональные данные
- ✅ Поддерживает DNSSEC
- ✅ Быстрый и стабильный

## После настройки

После успешной настройки DNS:

1. **Перезапустите WSL**
   ```powershell
   wsl --shutdown
   wsl
   ```

2. **Проверьте DNS в WSL**
   ```bash
   cat /etc/resolv.conf
   ping auth.openai.com
   ```

3. **Протестируйте device-auth**
   ```bash
   codex login --device-auth
   ```

4. **Если device-auth сработает, скопируйте учетные данные**
   ```bash
   # Учетные данные будут в Windows ~/.codex
   # Они автоматически будут доступны в WSL
   ```

## Текущий статус

- ✅ Инструкции созданы
- ⏳ Ожидает настройки DNS в Windows
- ⏳ Ожидает перезапуска WSL
- ⏳ Ожидает тестирования device-auth

## Рекомендация

Используйте автоматический PowerShell скрипт `setup-windows-dns.ps1` для быстрой и безопасной настройки DNS.