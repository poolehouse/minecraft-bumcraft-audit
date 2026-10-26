# System Architecture

## Components

| Component | Technology | Role |
|---|---|---|
| Game server | Forge 1.20.1 (MC 1.20.1) on `itzg/minecraft-server:java21` | Hosts the Bumcraft modpack world |
| Container | Docker / Docker Compose | Process isolation, volume mounting, env injection |
| Modpack | CurseForge "Bumcraft 2: Eviction Edition" | 105 mods + 82 configs |
| Control plane | RCON (TCP 25575) | Remote command execution |
| AI builder | `mc_ai_builder.py` (asyncio + mcrcon + httpx) | Chat-driven `!build`/`!undo` via Ollama |
| RCON API | `mc_rcon_api.py` (FastAPI) | HTTP → RCON proxy on port 8090 |
| LLM | Ollama `qwen3-coder-next` | Natural-language → Minecraft command JSON |

## Network ports

| Port | Protocol | Purpose |
|---|---|---|
| 25565 | TCP + UDP | Minecraft game + query/status |
| 24454 | UDP | Simple Voice Chat mod |
| 25575 | TCP | RCON (remote console) |
| 8090 | TCP | FastAPI RCON HTTP API |

## Data flow — AI build request

1. Player types `!build <prompt>` in-game chat.
2. `mc_ai_builder.py` tails `data/logs/latest.log`, detects the command, extracts the player name.
3. It queries Ollama (`/chat/completions`, model `qwen3-coder-next`) with a system prompt requiring a JSON array of `/commands` using relative `~ ~ ~` coordinates.
4. It parses the JSON (with truncated-JSON recovery), executes each command via RCON (0.1s spacing), records the command list in an in-memory undo history, and reports success/failure back to the player via `/tellraw`.
5. `!undo` inverts the last `/fill ... <block>` command to `minecraft:air` for that player.

## Data flow — HTTP API build

1. Client POSTs to `http://<host>:8090/build` with `{prompt, player, execute}`.
2. `mc_rcon_api.py` queries Ollama, parses commands, optionally executes them via RCON, and returns the generated + executed command lists.

## Trust boundaries

- The RCON port (25575) and FastAPI port (8090) expose op-level command execution. They must not be exposed to the public internet without authentication and TLS.
- The AI builder grants build privileges to any player who can send chat — no permission gating.
- Ollama runs locally (`localhost:11434`); no external model provider is called by default.

## Limitations

- Undo history is in-memory and lost on restart.
- Log-polling (1s interval) is fragile to log rotation/format changes.
- No backup/restore automation is wired in the compose file.

See `docs/AUDIT_REPORT.md` for the full findings and remediation list.