# RCON HTTP API — `mc_rcon_api.py`

Source: `src/mc_rcon_api.py` (verbatim copy of the audited service)

## Purpose

A **FastAPI** HTTP → RCON proxy that exposes Minecraft server command execution over HTTP, plus an AI build endpoint powered by Ollama. Runs on `0.0.0.0:8090`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check; verifies RCON `list` command |
| `POST` | `/command` | Execute a single RCON command (`{command, wait_for_response}`) |
| `POST` | `/commands` | Execute multiple commands sequentially |
| `POST` | `/build` | Generate + optionally execute build commands from natural language (`{prompt, player, execute, max_commands}`) |
| `POST` | `/clear` | Clear an area around the player (`/fill ... minecraft:air`; `{size, player}`) |

## Request / response models (summary)

**`CommandRequest`:** `command: str`, `wait_for_response: bool = true`  
**`CommandResponse`:** `success: bool`, `command: str`, `response: str`, `error?: str`  
**`BuildRequest`:** `prompt: str`, `player: str = "Player"`, `execute: bool = true`, `max_commands: int = 50`  
**`BuildResponse`:** `success`, `prompt`, `commands: list[str]`, `executed: list[CommandResponse]`, `error?: str`

## Key implementation details

- **RCON lifecycle:** `connect_rcon()` / `get_rcon()` with auto-reconnect on failure; lifespan context connects on startup and disconnects on shutdown.
- **Ollama integration:** `query_ollama()` posts to `{OLLAMA_BASE_URL}/chat/completions` with model `qwen3-coder-next`, temperature 0.3, 8192 max tokens, 10-minute timeout → raises `504` on timeout.
- **Command parsing:** Same regex + truncated-JSON recovery approach as `mc_ai_builder.py`; returns only strings starting with `/`.
- **CORS:** `allow_origins=["*"]`, all methods/headers (⚠️ tighten for internet exposure).
- **Command prefixing:** Commands without a leading `/` get one prepended.
- **Player notifications:** `/tellraw` messages sent on build start and completion when a `player` is provided.

## Configuration (env vars)

| Variable | Default |
|---|---|
| `RCON_HOST` | `127.0.0.1` |
| `RCON_PORT` | `25575` |
| `RCON_PASSWORD` | `[REDACTED]` |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` |
| `MODEL_NAME` | `qwen3-coder-next` |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8090` |

## Running

```bash
pip install fastapi httpx mcrcon pydantic uvicorn
python src/mc_rcon_api.py
# or: uvicorn src.mc_rcon_api:app --host 0.0.0.0 --port 8090
```

## Gaps & risks (from `docs/AUDIT_REPORT.md`)

- **No authentication/authorization** on the HTTP API — anyone who can reach port 8090 can execute op-level commands.
- **CORS allow-all** (`allow_origins=["*"]`).
- Default RCON password hard-coded.
- No rate limiting or request-size validation beyond pydantic models.

> ⚠️ Do not expose port 8090 (or 25575) to the public internet without authentication, TLS, and IP restrictions.
