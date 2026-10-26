# Minecraft Bumcraft Server — Full Scope Audit & Documentation

**Bumcraft 2: Eviction Edition** — Forge 1.20.1 modded Minecraft server infrastructure, RCON tooling, and AI-assisted building service.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Minecraft 1.20.1](https://img.shields.io/badge/Minecraft-1.20.1-red.svg)](https://www.minecraft.net/)
[![Forge 47.3.0](https://img.shields.io/badge/Forge-47.3.0-orange.svg)](https://files.minecraftforge.net/)
[![Ollama](https://img.shields.io/badge/Ollama-qwen3--coder--next-blue.svg)](https://ollama.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg)](https://fastapi.tiangolo.com/)
[![itzg/docker](https://img.shields.io/badge/Container-itzg/minecraft--server:java21-green.svg)](https://github.com/itzg/docker-minecraft-server)

## Overview

This repository is a **full-scope audit and documentation bundle** for the **Bumcraft** Minecraft server implementation. It captures:

1. **The server stack** — a Forge 1.20.1 modpack ("Bumcraft 2: Eviction Edition") running under Docker via `itzg/minecraft-server:java21`, with 105 mods, 82 config files, CurseForge auto-install, RCON, and Simple Voice Chat.
2. **The AI builder service** (`src/mc_ai_builder.py`) — an asyncio-based RCON bot that tails the server log for `!build` / `!undo` chat commands, queries Ollama (`qwen3-coder-next`) to generate Minecraft commands from natural language, and executes them via RCON with undo history.
3. **The RCON HTTP API** (`src/mc_rcon_api.py`) — a FastAPI proxy exposing `/command`, `/commands`, `/build`, `/clear`, and `/health` endpoints over HTTP, backed by RCON and Ollama.

## Repository Layout

```
minecraft-bumcraft-audit/
├── README.md                 # This file (project overview + LLM disclosure)
├── LICENSE                   # MIT License
├── CODE_OF_CONDUCT.md        # Contributor Covenant
├── CONTRIBUTING.md           # Contribution guide
├── SECURITY.md               # Security policy + disclosure
├── .gitignore                # Git ignore rules
├── configs/                  # Server configuration samples (sanitized)
│   ├── docker-compose.yml    # Docker Compose service definition
│   ├── server.properties     # Minecraft server.properties
│   └── .env.example          # Environment variable template
├── docs/                     # Audit documentation
│   ├── AUDIT_REPORT.md       # Full scope audit findings & recommendations
│   ├── ARCHITECTURE.md       # System architecture & data flow
│   ├── SERVER_CONFIG.md      # Docker/compose + server.properties reference
│   ├── MOD_INVENTORY.md      # 105-mod inventory with categories
│   ├── CRASH_ANALYSIS.md     # Crash report analysis (3 crashes, Oct 2026)
│   ├── AI_BUILDER.md         # mc_ai_builder.py design & operation
│   ├── RCON_API.md           # mc_rcon_api.py endpoint reference
│   ├── DEPLOYMENT.md         # Step-by-step deployment guide
│   └── LLM_DISCLOSURE.md     # AI/LLM usage disclosure
├── src/                      # Audited source code (verbatim copies)
│   ├── mc_ai_builder.py
│   └── mc_rcon_api.py
└── assets/                   # Diagrams & diagrams-as-code
```

## Quick Reference

| Component | Detail |
|---|---|
| Game version | Minecraft 1.20.1 (Forge 47.3.0) |
| Modpack | Bumcraft 2: Eviction Edition (CurseForge) |
| Container image | `itzg/minecraft-server:java21` |
| JVM | 24 GB heap, Generational ZGC, Java 21 |
| Game port | `25565` (TCP/UDP) |
| Voice chat | `24454` (UDP, Simple Voice Chat) |
| RCON port | `25575` (TCP) |
| RCON API | FastAPI on `0.0.0.0:8090` |
| AI model | `qwen3-coder-next` via Ollama (`11434`) |
| Max players | 20 |
| Difficulty | Easy |
| Allow flight | `true` |
| View distance | 6 |

## Getting Started

1. Copy `configs/.env.example` to `.env` and fill in `CF_API_KEY` (CurseForge) and any RCON/Ollama settings.
2. Review `docs/DEPLOYMENT.md` for the full deployment procedure.
3. See `docs/AUDIT_REPORT.md` for known issues (including the Create/FramedBlocks version conflict that caused the Oct 2026 crashes).

## LLM Disclosure

This repository and its documentation were produced with the assistance of large language models (LLMs). See `docs/LLM_DISCLOSURE.md` for a detailed statement of what was AI-generated, what was verified, and how AI was used in the audit process.

## Security

⚠️ **The default RCON password and CurseForge API key placeholders are insecure.** Rotate all credentials before any production deployment. See `SECURITY.md` and `docs/AUDIT_REPORT.md`.

## License

MIT License. See `LICENSE` for details.

---

*This is an independent community documentation project and is not affiliated with Mojang, CurseForge, itzg, Ollama, or the Bumcraft modpack authors.*