# AI Builder Service — `mc_ai_builder.py`

Source: `src/mc_ai_builder.py` (verbatim copy of the audited service)

## Purpose

An asyncio-based RCON bot that enables **chat-driven AI building** on the Bumcraft server. Players type `!build` or `!undo` in-game; the service tails the server log, queries Ollama to generate Minecraft commands, executes them via RCON, and supports undo.

## Supported commands

| Chat command | Behavior |
|---|---|
| `!build <prompt>` | Free-text build → Ollama generates commands → executed via RCON |
| `!build preset:halfpipe` | Builds a stone halfpipe ramp (relative coords) |
| `!build preset:streetplaza` | Builds a skate street plaza (ledges, stairs, rails, manual pad) |
| `!undo` | Reverts the player's last build (fills with air) |

## Presets (hard-coded, relative `~ ~ ~` coordinates)

- **halfpipe:** stone quarter-pipe transition + stone brick coping + light gray concrete skating surface.
- **streetplaza:** stone/concrete plaza base, four stone-brick ledges, stone-brick stairs, gray concrete manual pad, iron-bar rails.

## Architecture

```
[player chat] → latest.log → mc_ai_builder.py (log poll, 1s)
                                    ↓
                              Ollama (qwen3-coder-next)
                              /chat/completions
                                    ↓
                              JSON array of /commands
                                    ↓
                              RCON (25575) → Minecraft server
                                    ↓
                              /tellraw result to player
```

## Key implementation details

- **Log polling:** Reads `latest.log` from the last known byte offset; detects log rotation (file shrank → reset offset to 0).
- **Command extraction:** Regexes `<player> !build ...` / `<player>: !build ...` / bare `!build ...` patterns.
- **Ollama prompt:** System prompt instructs the model to return ONLY a JSON array of commands using `/setblock`, `/fill`, `/clone`, `/structure` with relative `~ ~ ~` coords; max 50 commands; prefer `/fill` for volumes; removal via `minecraft:air`.
- **JSON parsing:** `re.search(r'\[.*\]', ...)` with `json.loads`; includes `_fix_truncated_json` recovery for truncated model output (closes the array at the last valid string boundary).
- **Execution:** Sequential RCON commands with 0.1s spacing between each.
- **Undo:** Stores up to 10 command lists per player in `UNDO_HISTORY` (in-memory dict). Undo inverts `/fill ... <block>` → `/fill ... minecraft:air` via regex. Results reported via `/tellraw`.
- **Notifications:** `/tellraw` messages in red/green/gold for errors, progress, and completion.

## Configuration (env vars)

| Variable | Default |
|---|---|
| `RCON_HOST` | `127.0.0.1` |
| `RCON_PORT` | `25575` |
| `RCON_PASSWORD` | `[REDACTED]` |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` |
| `MODEL_NAME` | `qwen3-coder-next` |
| `MC_LOG_FILE` | `/path/to/minecraft-server-bumcraft/data/logs/latest.log` |
| `POLL_INTERVAL` | `1.0` |

## Gaps & risks (from `docs/AUDIT_REPORT.md`)

- Undo history is **in-memory only** — lost on restart.
- **No permission gating** — any player who can chat can trigger builds.
- **No rate limiting** — a player could spam `!build`.
- Log polling is **fragile to log rotation/format changes**.
- No block-protection integration (builds can overwrite spawn/other players' builds).
- Default RCON password hard-coded.

## Running

```bash
python src/mc_ai_builder.py
```

Requires: `httpx`, `mcrcon`. The server must be running with RCON enabled, and Ollama must be serving `qwen3-coder-next` on the configured base URL.
