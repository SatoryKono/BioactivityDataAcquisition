# Запуск OpenAI Codex CLI

## Быстрый старт

```bash
# Войти в WSL Debian
wsl -d Debian

# Интерактивный режим (в папке проекта)
cx

# Неинтерактивный режим с заданием
cxe "опиши архитектуру проекта"
```

## Из PowerShell (без входа в WSL)

```powershell
# Интерактивный
wsl -d Debian -- bash -lc "cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2 && codex"

# Неинтерактивный
wsl -d Debian -- bash -lc "cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2 && codex exec --full-auto 'задание'"
```

## Если DNS сломался (после перезагрузки Windows/VPN)

```bash
wsl -d Debian
bash /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.setup_wsl_codex.sh
```

## Переавторизация (токен истёк)

```bash
wsl -d Debian -- bash -lc "codex login --device-auth"
```

Откроется ссылка + код — ввести на https://auth.openai.com/codex/device

## Полезные флаги `codex exec`

| Флаг | Описание |
|------|----------|
| `--full-auto` | Автоматическое выполнение команд без подтверждения |
| `--json` | Вывод в JSONL (для скриптов) |
| `-m gpt-4o` | Использовать другую модель |
| `-s workspace-write` | Sandbox с записью в проект |
| `-i image.png` | Прикрепить скриншот |

## Что настроено

- **Модель**: `gpt-5.3-codex`
- **Авторизация**: device-code через ChatGPT аккаунт
- **DNS**: OpenAI хосты прописаны в `/etc/hosts` (обход VPN)
- **Конфиг**: `/root/.codex/config.toml`
- **Aliases**: `cx` (интерактив), `cxe` (exec --full-auto), `cdp` (cd в проект)

## Почему WSL

Codex CLI написан на Rust. VPN на Windows ломает Rust TLS stack (stream disconnected).
WSL2 Debian обходит эту проблему — TLS работает нативно через Linux.
DNS в WSL2 нестабилен из-за VPN, поэтому OpenAI хосты прописаны статически в `/etc/hosts`.
