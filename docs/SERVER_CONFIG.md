# Server Configuration Reference

Sources: `minecraft-server-bumcraft/docker-compose.yml`, `minecraft-server-bumcraft/.env`, `minecraft-server-bumcraft/data/server.properties`.

## Docker Compose (`configs/docker-compose.yml`)

Image: `itzg/minecraft-server:java21`
Container name: `mc-bumcraft-server`
Restart policy: `unless-stopped`

### Ports
- `25565:25565/tcp` — Minecraft game traffic
- `25565:25565/udp` — Query/status
- `24454:24454/udp` — Simple Voice Chat
- `25575:25575/tcp` — RCON

### Key environment variables
| Variable | Value | Notes |
|---|---|---|
| `EULA` | `TRUE` | Accepts Minecraft EULA |
| `UID`/`GID` | `1000` | Match host user to avoid root-owned files |
| `TYPE` | `AUTO_CURSEFORGE` | CurseForge modpack auto-install |
| `CF_PAGE_URL` | `https://www.curseforge.com/minecraft/modpacks/bumcraft-2-eviction-edition` | Modpack page |
| `CF_API_KEY` | `${CF_API_KEY}` | CurseForge API key (from `.env`) |
| `CF_MODPACK_ZIP` | `/modpacks/Bumcraft 2- Eviction Edition-1.0.zip` | Local modpack zip fallback |
| `CURSEFORGE_FILES` | `i-wanna-skate,citadel` | Extra direct-file downloads |
| `MEMORY` | `24G` | JVM heap |
| `USE_AIKAR_FLAGS` | `false` | AIKAR flags disabled |
| `JVM_XX_OPTS` | ZGC opts (see compose) | Generational ZGC, Java 21 |
| `MOTD` | `Bumcraft 2: Skate or Evict Edition (24GB ZGC)` | Server MOTD |
| `ALLOW_FLIGHT` | `true` | Allows flight |
| `ENABLE_RCON` | `true` | Enables RCON |
| `RCON_PASSWORD` | `[REDACTED]` | ⚠️ default — rotate |
| `SNOOPER_ENABLED` | `false` | Disables Mojang snooper |

### Volumes
- `./data:/data` — world, configs, mods, logs
- `./modpacks:/modpacks:ro` — modpack zip drop-in
- `./mods:/mods:ro` — additional mod jars

## server.properties (`configs/server.properties`)

| Setting | Value |
|---|---|
| `difficulty` | `easy` |
| `gamemode` | `survival` |
| `allow-flight` | `true` |
| `enable-rcon` | `true` |
| `rcon.port` | `25575` |
| `rcon.password` | `[REDACTED]` ⚠️ |
| `online-mode` | `true` |
| `max-players` | `20` |
| `view-distance` | `6` |
| `simulation-distance` | `6` |
| `spawn-protection` | `16` |
| `pvp` | `true` |
| `enable-command-block` | `false` |
| `enforce-secure-profile` | `true` |
| `snooper-enabled` | `false` |
| `motd` | `Bumcraft 2\: Skate or Evict Edition (24GB ZGC)` |

## Environment template (`configs/.env.example`)

```ini
# CurseForge API key (required for AUTO_CURSEFORGE downloads)
CF_API_KEY=

# RCON
RCON_HOST=127.0.0.1
RCON_PORT=25575
RCON_PASSWORD=CHANGE_ME

# Ollama / AI builder
OLLAMA_BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen3-coder-next

# RCON API
API_HOST=0.0.0.0
API_PORT=8090
```

> ⚠️ **Security:** Never commit real values for `CF_API_KEY`, `RCON_PASSWORD`, or other secrets. Rotate defaults before deployment. See `SECURITY.md`.

## Forge manifest (`data/.forge-manifest.json`)
- Minecraft version: `1.20.1`
- Forge version: `47.3.0`
- Server entry: `/data/./run.sh`

## Resource pack
- `data/resourcepacks/Quark Programmer Art.zip`
