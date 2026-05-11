# WSL Setup für Codex Integration

## Übersicht

Diese Anleitung richtet Codex (Anthropic's AI Coding Assistant) für die Verwendung unter WSL2 ein. Codex läuft nicht als Docker-Container, sondern als lokale Desktop-Anwendung, aber wir konfigurieren die Docker MCP-Server (Model Context Protocol) so, dass sie über Docker unter WSL2 laufen.

## Voraussetzungen

- Windows 10/11 mit WSL2 aktiviert
- Docker Desktop mit WSL2 Integration
- Anthropic Codex installiert und konfiguriert

## Setup-Schritte

### 1. Docker Desktop WSL2-Integration aktivieren

```powershell
# In PowerShell als Administrator
wsl --list --verbose
# Output sollte zeigen: Ubuntu (Running, Version 2)
```

Stellen Sie sicher, dass in Docker Desktop unter "Settings > Resources > WSL Integration" Ubuntu aktiviert ist.

### 2. MCP-Server starten

```powershell
# Aus dem Projektverzeichnis
docker compose -f docker-compose.codex.yml up -d

# Status überprüfen
docker compose -f docker-compose.codex.yml ps
```

### 3. Codex konfigurieren

Bearbeiten Sie `.codex/settings.json` für WSL-Pfade:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
      "env": {
        "MEMORY_FILE_PATH": "/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/00-project/ai/memory/mcp-memory.json"
      }
    },
    "docker": {
      "command": "docker",
      "args": ["exec", "-i", "bioetl-mcp-docker", "/mcp_docker_wrapper.sh"]
    }
  }
}
```

### 4. Codex starten

1. Öffnen Sie Anthropic's Codex Application
2. Die MCP-Server werden automatisch verbunden
3. Überprüfen Sie in Codex's Settings, ob alle MCP-Server grün sind

## Docker-kommandos

```bash
# MCP-Container-Status
docker compose -f docker-compose.codex.yml ps

# Logs anzeigen
docker compose -f docker-compose.codex.yml logs -f

# Alle MCP-Container stoppen
docker compose -f docker-compose.codex.yml down

# Neustarten
docker compose -f docker-compose.codex.yml restart
```

## Fehlerbehebung

### Docker-Socket nicht erreichbar
```powershell
# Docker Desktop starten
# WSL Integration in Settings überprüfen
# /var/run/docker.sock sollte erreichbar sein
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock docker:latest docker ps
```

### MCP-Server-Fehler
```powershell
# Logs überprüfen
docker compose -f docker-compose.codex.yml logs bioetl-mcp-memory
docker compose -f docker-compose.codex.yml logs bioetl-mcp-docker
```

### Netzwerkfehler
```powershell
# Netzwerk überprüfen
docker network inspect warp-network
docker network inspect bridge
```

## Umgebungsvariablen

Erstellen Sie `.env` mit erforderlichen Tokens:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxx
GRAFANA_SERVICE_ACCOUNT_TOKEN=eyJrIjoiexxxxxxxxxxxx
BRAVE_API_KEY=Brxxxxxxxxxxxxxxxxxx
```

## Performance-Tipps für WSL2

1. **WSL-Speicher optimieren** - `C:\Users\{user}\.wslconfig`:
   ```ini
   [wsl2]
   memory=8GB
   processors=4
   swap=2GB
   ```

2. **Docker-Ressourcen erhöhen** - Docker Desktop Settings:
   - CPUs: 4+
   - Memory: 8GB+
   - Swap: 2GB+

3. **Dateilage optimieren** - Platzieren Sie das Projekt im WSL-Dateisystem:
   ```powershell
   # Schneller Zugriff
   \\wsl$\Ubuntu\home\{user}\projects\BioactivityDataAcquisition2
   ```

## WSL-Proxy (optional)

Wenn Sie einen HTTP-Proxy verwenden:

```bash
# In `.wsl_proxy_env.sh` konfigurieren
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
export NO_PROXY=localhost,127.0.0.1,host.docker.internal
```

## Siehe auch

- [Codex MCP Integration](https://www.docker.com/blog/connect-codex-to-mcp-servers-mcp-toolkit/)
- [WSL Docker Integration](https://docs.docker.com/desktop/wsl/)
- [MCP Protocol](https://modelcontextprotocol.io/)
