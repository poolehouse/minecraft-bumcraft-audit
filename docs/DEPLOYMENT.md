# Deployment Guide

> ⚠️ Review `docs/AUDIT_REPORT.md` and apply the remediation checklist (especially the Create/FramedBlocks fix and credential rotation) **before** deploying to any shared or production environment.

## Prerequisites

- Docker + Docker Compose
- Java 21 (host, if not using the container image)
- Ollama running with `qwen3-coder-next` (for AI builder / RCON API)
- A CurseForge API key from https://console.curseforge.com/ (for `AUTO_CURSEFORGE`)

## Step 1 — Prepare configuration

```bash
cd minecraft-server-bumcraft   # the server directory
cp configs/.env.example .env   # (adapt paths to your layout)
```

Edit `.env`:
- Set `CF_API_KEY` to your CurseForge key.
- Set `RCON_PASSWORD` to a strong, unique value.
- Adjust `OLLAMA_BASE_URL` / `MODEL_NAME` if using a remote Ollama instance.

## Step 2 — Resolve the mod conflict (required)

The pack crashes on startup because `FramedBlocks` needs Create >= 6.0.2 but Create is `0.5.1.j`. Choose:

- **Option A:** Upgrade Create and its addons to >= 6.0.2, keep FramedBlocks.
- **Option B:** Remove/downgrade FramedBlocks to match Create 0.5.1.j.

Also remove the duplicate `citadel-2.6.1.jar` (keep `citadel-2.6.3.jar`).

Update `modpacks/Bumcraft 2- Eviction Edition-1.0.zip` (or the mods folder) after changes.

## Step 3 — Start the server

```bash
docker compose up -d
```

Verify:
```bash
docker compose logs -f mc-bumcraft-server
```

Watch for `Forge Mod Loader has successfully loaded` and no `FML` crash reports in `data/crash-reports/`.

## Step 4 — Start the tooling services

**RCON API:**
```bash
cd /path/to/minecraft-bumcraft-audit
pip install -r requirements.txt   # create this from imports: fastapi, httpx, mcrcon, pydantic, uvicorn
uvicorn src.mc_rcon_api:app --host 0.0.0.0 --port 8090
```

**AI Builder:**
```bash
pip install httpx mcrcon
python src/mc_ai_builder.py
```

## Step 5 — Verify

- Game port: `mc status <host>:25565` or join in Minecraft.
- RCON API health: `curl http://<host>:8090/health`
- AI builder: in-game, type `!build preset:halfpipe` and watch for the structure.

## Step 6 — Backups (recommended)

The compose file mounts `./data` but schedules no backups. Add a cron job or sidecar that periodically tars `data/world`, `data/config`, and `data/server.properties` to off-host storage, and test a restore.

## Environment variable cheat sheet

| Var | Where used | Example |
|---|---|---|
| `CF_API_KEY` | docker-compose (CurseForge) | `[REDACTED]` |
| `RCON_PASSWORD` | compose + server.properties + both Python scripts | `STRONG_RANDOM_PASS` |
| `OLLAMA_BASE_URL` | mc_ai_builder.py / mc_rcon_api.py | `http://localhost:11434/v1` |
| `MODEL_NAME` | both Python scripts | `qwen3-coder-next` |
| `MEMORY` | docker-compose | `24G` (consider reducing) |

## Security checklist (pre-deploy)

- [ ] `.env` contains real secrets, not defaults
- [ ] `.env` is gitignored
- [ ] RCON password rotated from `[REDACTED]`
- [ ] Ports 25575 (RCON) and 8090 (API) not exposed to public internet without auth/TLS
- [ ] `allow_origins` in `mc_rcon_api.py` narrowed if internet-facing
- [ ] Create/FramedBlocks conflict resolved
- [ ] Backup schedule tested
