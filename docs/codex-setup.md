# OpenAI Codex CLI — Установка и запуск

> Codex CLI работает через WSL2 Debian, т.к. VPN на Windows ломает Rust TLS stack.

---

## 1. Быстрый старт (уже настроено)

```bash
# Войти в WSL
wsl -d Debian

# Интерактивный режим
cx

# Неинтерактивный режим
cxe "задание для Codex"
```

Из PowerShell (без входа в WSL):

```powershell
# Интерактивный
wsl -d Debian -- bash -lc "cd /mnt/e/g-drive/05-AI/github/BioactivityDataAcquisition2 && codex"

# Неинтерактивный
wsl -d Debian -- bash -lc "cd /mnt/e/g-drive/05-AI/github/BioactivityDataAcquisition2 && codex exec --full-auto 'задание'"
```

---

## 2. Установка с нуля

### 2.1. Создать WSL2 Debian

```powershell
# Если Debian нет в WSL:
# Скачать rootfs (VPN может блокировать wsl --install)
curl --ssl-no-revoke -L -o debian.appx "https://aka.ms/wsl-debian-gnulinux"

# Переименовать и распаковать
ren debian.appx debian.zip
Expand-Archive debian.zip -DestinationPath debian-extracted

# Найти install.tar.gz (может быть вложен в DistroLauncher-Appx-*.appx)
# Импортировать:
mkdir C:\Users\%USERNAME%\WSL\Debian
wsl --import Debian C:\Users\%USERNAME%\WSL\Debian path\to\install.tar.gz --version 2
```

### 2.2. Установить Node.js и Codex

```bash
wsl -d Debian

# Обновить пакеты
apt-get update && apt-get install -y curl ca-certificates git

# Установить Node.js 22 (из бинарного tarball — nvm не нужен)
cd /tmp
curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.gz -o node.tar.gz
tar -xzf node.tar.gz
cp -r node-v22.14.0-linux-x64/{bin,lib,include,share} /usr/local/
rm -rf node.tar.gz node-v22.14.0-linux-x64

# Проверить
node --version   # v22.14.0
npm --version    # 10.9.2

# Установить Codex CLI
npm install -g @openai/codex
codex --version  # codex-cli 0.104.0
```

### 2.3. Настроить DNS (обход VPN)

VPN ломает DNS-резолвинг в WSL2. Прописываем хосты статически.

```bash
# Отключить автогенерацию /etc/hosts и /etc/resolv.conf
cat > /etc/wsl.conf << 'EOF'
[network]
generateHosts = false
generateResolvConf = false
EOF

# Настроить DNS-серверы
cat > /etc/resolv.conf << 'EOF'
nameserver 172.26.16.1
nameserver 8.8.8.8
EOF

# Добавить OpenAI хосты (IP могут измениться — см. раздел "Обновление DNS")
cat >> /etc/hosts << 'EOF'
104.18.32.47 chatgpt.com
162.159.140.245 api.openai.com
104.18.41.241 auth.openai.com
172.65.90.22 auth0.openai.com
64.239.109.193 developers.openai.com
EOF
```

> После изменения wsl.conf нужно перезапустить WSL:
> `wsl --terminate Debian` из PowerShell, затем `wsl -d Debian`.

### 2.4. Настроить git

```bash
git config --global user.name "YourName"
git config --global user.email "your@email.com"
```

### 2.5. Авторизация

```bash
codex login --device-auth
```

1. Откроется URL и одноразовый код
2. Перейти на https://auth.openai.com/codex/device в браузере
3. Ввести код и подтвердить вход через ChatGPT-аккаунт

Проверка:
```bash
codex login status
# Logged in using ChatGPT
```

### 2.6. Конфигурация Codex

```bash
mkdir -p ~/.codex
cat > ~/.codex/config.toml << 'TOML'
model = 'gpt-5.3-codex'
model-provider = 'openai'
model-reasoning-effort = 'high'
personality = 'pragmatic'

[model-providers]
[model-providers.openai]
api-key-env = 'OPENAI-API-KEY'
base-url = 'https://api.openai.com/v1'
name = 'OpenAI'
request-max-retries = 10
stream-idle-timeout-ms = 600000
stream-max-retries = 20

[projects]
[projects.'/mnt/e/g-drive/05-AI/github/BioactivityDataAcquisition2']
trust-level = 'trusted'
TOML
```

> MCP-серверы отключены — DNS нестабилен, а openaiDeveloperDocs некритичен.

### 2.7. Настроить aliases (опционально)

Добавить в `~/.bashrc`:

```bash
# Node.js
export PATH="/usr/local/bin:$PATH"

# BioETL project
export BIOETL-DIR="/mnt/e/g-drive/05-AI/github/BioactivityDataAcquisition2"
alias cdp="cd $BIOETL-DIR"
alias cx="cd $BIOETL-DIR && codex"
alias cxe="cd $BIOETL-DIR && codex exec --full-auto"

# Auto-fix DNS при входе
if ! grep -q "api.openai.com" /etc/hosts 2>/dev/null; then
  bash "$BIOETL-DIR/.setup-wsl-codex.sh" 2>/dev/null
fi
```

---

## 3. Использование

### Интерактивный режим

```bash
cx                          # alias — cd в проект + codex
codex                       # из папки проекта
codex "начальный промпт"    # сразу с заданием
codex -i screenshot.png     # с приложенным скриншотом
```

### Неинтерактивный режим (exec)

```bash
cxe "задание"                                    # alias — exec --full-auto
codex exec --full-auto "задание"                  # полный вариант
codex exec --full-auto --json "задание"           # JSONL-вывод
codex exec -s danger-full-access "задание"        # полный доступ к FS
```

### Код-ревью

```bash
codex review          # review текущих изменений
codex exec review     # в exec-режиме
```

### Флаги

| Флаг | Описание |
|------|----------|
| `--full-auto` | `--sandbox workspace-write` + авто-одобрение команд |
| `--json` | Вывод событий в JSONL |
| `-m MODEL` | Выбрать модель (`gpt-4o`, `o3`, `gpt-5.3-codex`) |
| `-s SANDBOX` | `read-only` / `workspace-write` / `danger-full-access` |
| `-i FILE` | Прикрепить изображение |
| `-C DIR` | Рабочая директория |
| `--search` | Включить веб-поиск |

### Управление сессиями

```bash
codex resume          # продолжить предыдущую сессию
codex resume --last   # продолжить последнюю
codex fork --last     # форкнуть последнюю сессию
```

---

## 4. Обслуживание

### Переавторизация (токен истёк)

```bash
codex login --device-auth
```

### Обновление DNS (IP изменились)

Если Codex перестал подключаться — IP хостов OpenAI могли измениться.

Из PowerShell узнать актуальные IP:
```powershell
Resolve-DnsName chatgpt.com -Type A
Resolve-DnsName api.openai.com -Type A
Resolve-DnsName auth.openai.com -Type A
```

В WSL обновить `/etc/hosts`:
```bash
# Удалить старые записи
sed -i '/chatgpt.com\|openai.com/d' /etc/hosts
# Добавить новые
echo "NEW-IP chatgpt.com" >> /etc/hosts
echo "NEW-IP api.openai.com" >> /etc/hosts
echo "NEW-IP auth.openai.com" >> /etc/hosts
```

Или запустить скрипт (резолвит автоматически, если DNS работает):
```bash
bash /mnt/e/g-drive/05-AI/github/BioactivityDataAcquisition2/.setup-wsl-codex.sh
```

### Обновление Codex

```bash
wsl -d Debian -- bash -lc "npm update -g @openai/codex && codex --version"
```

### Обновление Node.js

```bash
wsl -d Debian
cd /tmp
curl -fsSL https://nodejs.org/dist/vXX.YY.ZZ/node-vXX.YY.ZZ-linux-x64.tar.gz -o node.tar.gz
tar -xzf node.tar.gz
cp -r node-vXX.YY.ZZ-linux-x64/{bin,lib,include,share} /usr/local/
rm -rf node.tar.gz node-vXX.YY.ZZ-linux-x64
```

---

## 5. Troubleshooting

| Проблема | Решение |
|----------|---------|
| `stream disconnected` | DNS сломался. Обновить `/etc/hosts` (см. раздел 4) |
| `Resolving timed out` | DNS таймаут. Проверить `/etc/resolv.conf` содержит `172.26.16.1` и `8.8.8.8` |
| `MCP server DNS error` | Нормально — MCP отключены в конфиге, ошибка некритична |
| `failed to refresh available models` | Таймаут при старте. Повторить запуск |
| `Reconnecting... N/5` | VPN блокирует соединение. Проверить DNS и `/etc/hosts` |
| WSL не запускается | `wsl --terminate Debian` и снова `wsl -d Debian` |
| `/etc/hosts` сбросился | `generateHosts = false` не установлен в `/etc/wsl.conf` |
| `/etc/resolv.conf` сбросился | `generateResolvConf = false` не установлен в `/etc/wsl.conf` |

---

## 6. Архитектура решения

```
Windows (VPN)
├── PowerShell / Git Bash
│   └── wsl -d Debian
│       └── WSL2 Debian 11
│           ├── Node.js 22.14.0 (/usr/local/)
│           ├── Codex CLI 0.104.0 (npm global)
│           ├── Auth: device-code → chatgpt.com
│           ├── /etc/hosts → статические IP OpenAI
│           ├── /etc/wsl.conf → generateHosts=false
│           └── Проект: /mnt/e/g-drive/.../BioactivityDataAcquisition2
│               ├── AGENTS.md → инструкции для Codex
│               └── .codex/config.toml → настройки проекта
```

**Почему WSL**: Codex CLI написан на Rust. VPN перехватывает TLS (SSL inspection),
и Rust TLS stack (rustls) не доверяет VPN-сертификату. Python httpx и Linux curl
работают нормально — они используют системные CA-сертификаты. WSL2 обходит проблему,
т.к. Linux TLS не проходит через VPN proxy.

**Почему статический DNS**: WSL2 использует NAT через Windows-хост. VPN делает
DNS-резолвинг нестабильным (таймауты 10+ сек). Статические записи в `/etc/hosts`
обеспечивают мгновенное разрешение имён.
