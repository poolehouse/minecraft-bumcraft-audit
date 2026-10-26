# Full Scope Audit Report — Bumcraft Minecraft Server

**Project:** Minecraft Bumcraft Server Audit  
**Scope:** Server infrastructure, modpack, configuration, RCON tooling, AI builder service  
**Audit date:** October 2026  
**Status:** Complete  
**Classification:** Community / self-hosted  

---

## 1. Executive Summary

This audit covers the **Bumcraft 2: Eviction Edition** Minecraft server implementation: a Forge 1.20.1 modpack hosted in Docker (`itzg/minecraft-server:java21`), plus two custom Python services that extend the server with AI-assisted building (`mc_ai_builder.py`) and an HTTP→RCON API (`mc_rcon_api.py`).

**Overall finding:** The implementation is functional and follows the standard itgz/docker-minecraft-server pattern, but it contains several **high-severity operational risks**:

1. **Mod version conflict** — `FramedBlocks` requires Create 6.0.2+, but Create is pinned at `0.5.1.j`. This directly caused the three FML mod-loading crashes recorded on 2026-10-23.
2. **Duplicate mod jars** — `citadel-2.6.1` and `citadel-2.6.3` coexist; classloading conflicts are possible.
3. **Hard-coded default credentials** — RCON password `[REDACTED]` appears in `server.properties`, `.rcon-cli.env`, and both Python scripts as a default.
4. **Secrets in plaintext** — `CF_API_KEY` is referenced but empty; no secrets management is evident.
5. **Excessive JVM heap** — 24 GB heap with ZGC is oversized for most modded workloads and risks host memory pressure.
6. **No backup/restore automation** evident in the compose file (a `backups/` dir exists only in the non-bumcraft `minecraft-server`).

Detailed findings, root causes, and remediation steps are in Section 4.

---

## 2. Scope & Methodology

### In scope
| Item | Path / Artifact |
|---|---|
| Docker Compose (Bumcraft) | `minecraft-server-bumcraft/docker-compose.yml` |
| Docker Compose (reference/legacy) | `minecraft-server/docker-compose.yml` |
| Environment | `minecraft-server-bumcraft/.env` |
| Server properties | `minecraft-server-bumcraft/data/server.properties` |
| Modpack zip | `minecraft-server-bumcraft/modpacks/Bumcraft 2- Eviction Edition-1.0.zip` |
| Mod inventory | `minecraft-server-bumcraft/data/mods/` (105 jars) |
| Config inventory | `minecraft-server-bumcraft/data/config/` (82 files) |
| Crash reports | `minecraft-server-bumcraft/data/crash-reports/` (3 files) |
| Forge manifest | `minecraft-server-bumcraft/data/.forge-manifest.json` |
| RCON CLI env | `minecraft-server-bumcraft/data/.rcon-cli.env` |
| AI builder service | `mc_ai_builder.py` |
| RCON HTTP API | `mc_rcon_api.py` |

### Out of scope
- Client-side modpack / resource pack distribution
- In-game player data, world region files, and backups (present but not audited for content)
- Network/firewall topology beyond published ports
- The CurseForge modpack contents inside the zip (manifest-level only)

### Methodology
- Static review of all YAML, properties, env, JSON, and Python sources.
- Cross-referenced mod jar filenames against stated dependencies (Create, Citadel, FramedBlocks).
- Parsed crash report headers to identify the failing mod and root cause.
- Reviewed RCON/Ollama integration, command parsing, and undo logic for correctness and safety.
- No live server was running at audit time; runtime behavior was inferred from code and logs.

---

## 3. Architecture Overview

```
┌─────────────────┐      RCON (25575/TCP)      ┌──────────────────────┐
│  Minecraft Client│◀───────────────────────────│  itgz docker container│
│  (game port 25565│      Query 25565/UDP        │  Forge 1.20.1 server │
│   + Voice 24454) │◀───────────────────────────│  + 105 mods + configs│
└─────────────────┘      RCON API (8090/TCP)    └──────────┬───────────┘
                                                            │
                              HTTP (FastAPI)                │ RCON
                        ┌───────────────┐                  ▼
                        │ mc_rcon_api.py│─────────────────► mc_ai_builder.py
                        │ (port 8090)   │  (Ollama qwen3  │  (tails latest.log,
                        │ /command      │   coder-next)    │  polls !build/!undo)
                        │ /commands     │                  │  executes /fill,
                        │ /build        │                  │  /setblock, undo)
                        │ /clear        │
                        │ /health       │
                        └───────────────┘
```

Key design traits:
- **Single container** for game + mods + world (`./data:/data`).
- **RCON** is the control plane for both custom services.
- **Ollama** (`qwen3-coder-next`) generates command JSON from natural-language prompts.
- **Undo history** is kept in-memory only (lost on restart).

---

## 4. Findings & Recommendations

### CRITICAL / HIGH

#### F-01: Mod version conflict — FramedBlocks vs Create (crash cause)
**Severity:** High  
**Evidence:** `crash-2026-10-23_17.35.09-fml.txt`:  
`Mod framedblocks only supports create 6.0.2 or above. Currently, create is 0.5.1.j`  
**Impact:** Server fails to start (FML mod-loading failure). Three crashes recorded on 2026-10-23.  
**Root cause:** `FramedBlocks-9.4.3.jar` (requires Create ≥ 6.0.2) ships alongside `create-1.20.1-0.5.1.j.jar`.  
**Remediation:** Either (a) upgrade Create to ≥ 6.0.2 and its ecosystem (Create Central Kitchen, CreateBB, Create Enchantment Industry, etc.) to compatible versions, or (b) downgrade/remove FramedBlocks to a version compatible with Create 0.5.1. Regenerate the modpack zip after changes.

#### F-02: Duplicate Citadel versions
**Severity:** Medium  
**Evidence:** `citadel-2.6.1-1.20.1.jar` and `citadel-2.6.3-1.20.1.jar` both present in `data/mods/`.  
**Impact:** Potential classloading conflicts / non-deterministic mod behavior.  
**Remediation:** Remove the older `citadel-2.6.1`; keep `citadel-2.6.3` (required by `iwannaskate`).

#### F-03: Hard-coded default RCON password
**Severity:** High  
**Evidence:** `rcon.password=[REDACTED]` in `server.properties`; same value in `.rcon-cli.env`; used as default in both Python scripts.  
**Impact:** Any actor with network reach to port 25575 can execute arbitrary commands with op-level privileges.  
**Remediation:** Rotate to a strong, unique password; inject via `RCON_PASSWORD` env var only; never commit real values.

#### F-04: CurseForge API key absent / plaintext
**Severity:** Medium  
**Evidence:** `.env` contains `CF_API_KEY=` (empty). `docker-compose.yml` references `${CF_API_KEY}`.  
**Impact:** `AUTO_CURSEFORGE` cannot download the modpack without a key; local zip fallback is used instead. No secret rotation or vaulting.  
**Remediation:** Populate from a secrets manager / CI secret; add `.env` to `.gitignore`.

### MEDIUM

#### F-05: Oversized JVM heap (24 GB)
**Severity:** Medium  
**Evidence:** `MEMORY: "24G"` with `USE_AIKAR_FLAGS: "false"` and custom `JVM_XX_OPTS` using Generational ZGC.  
**Impact:** Risk of host OOM / container eviction; diminishing returns for a 20-player modded server.  
**Remediation:** Right-size to 8–12 GB unless telemetry shows sustained pressure; re-enable or validate AIKAR flags.

#### F-06: In-memory undo history
**Severity:** Medium  
**Evidence:** `UNDO_HISTORY: Dict[str, List[...]]` in `mc_ai_builder.py`, non-persistent.  
**Impact:** Undo capability lost on service restart; no audit trail of AI-built structures.  
**Remediation:** Persist undo history to disk/database; log all executed commands with player + timestamp.

#### F-07: No automated backups
**Severity:** Medium  
**Evidence:** `docker-compose.yml` mounts only `./data`, `./modpacks`, `./mods`; no backup volume or scheduled task. (A `backups/` dir exists in the sibling `minecraft-server` but is not wired.)  
**Impact:** World/config loss on container failure.  
**Remediation:** Add a scheduled world-backup job (e.g., `tar` to a backup volume or cloud storage) and test restore.

### LOW / INFORMATIONAL

#### F-08: Online mode enabled
`online-mode=true` — requires legitimate Mojang accounts; fine for private servers, blocks cracked clients.

#### F-09: CORS allow-all
`mc_rcon_api.py` sets `allow_origins=["*"]`. Acceptable for a local/trusted LAN; tighten for internet exposure.

#### F-10: `allow-flight=true`
Enabled for skate/vehicle mods; intended design, but can be abused for evasion/combat. Documented as intentional.

#### F-11: Log polling instead of events
`mc_ai_builder.py` tails `latest.log` every 1.0s. Works but is fragile to log rotation/format changes. Consider RCON `execute` + command-block hooks or a Fabric/Forge event listener for robustness.

---

## 5. Mod Inventory Summary

- **Total mods:** 105 jars in `data/mods/`
- **Total config files:** 82 in `data/config/`
- **Major themes:** Create (automation), Farmers Delight suite (farming/cooking), Quark, Alex's Mobs, Ars Nouveau, TConstruct, Waystones, Sophisticated Backpacks, Plasmovoice (voice chat), I Wanna Skate + Citadel (skateboarding), McW doors/fences/stairs/roofs (decoration), Create Central Kitchen / CreateBB / Create Enchantment Industry (Create addons).
- **Notable version pins:** Create `0.5.1.j`; Forge `47.3.0`; Java 21.
- **Duplicate:** Citadel 2.6.1 & 2.6.3.

See `docs/MOD_INVENTORY.md` for the full categorized list.

---

## 6. Crash Analysis Summary

Three FML crash reports from 2026-10-23 (17:34:43, 17:34:56, 17:35:09), all "Mod loading error has occurred". The `17:35:09` report identifies **FramedBlocks** as the suspected mod due to the Create version mismatch (see F-01). See `docs/CRASH_ANALYSIS.md` for full detail.

---

## 7. Tooling Review

### `mc_ai_builder.py`
- Asyncio RCON bot polling `latest.log` for `!build <prompt>` / `!build preset:<name>` / `!undo`.
- Presets: `halfpipe`, `streetplaza` (skate-themed, relative `~ ~ ~` coordinates).
- Queries Ollama (`qwen3-coder-next`) for free-text builds; parses JSON command arrays; includes truncated-JSON recovery.
- Executes via RCON with 0.1s spacing; records undo history (in-memory); notifies players via `/tellraw`.
- **Gaps:** no persistence, no rate limiting, no permission gating (any player who can chat can trigger builds), no block-protection integration.

### `mc_rcon_api.py`
- FastAPI app on `0.0.0.0:8090` with endpoints: `/health`, `/command`, `/commands`, `/build`, `/clear`.
- Lifespan-managed RCON connection with auto-reconnect; Ollama integration with 10-minute timeout.
- **Gaps:** no authentication/authorization on the HTTP API; CORS allow-all; no request validation beyond pydantic models.

See `docs/AI_BUILDER.md` and `docs/RCON_API.md`.

---

## 8. Remediation Checklist

- [ ] Resolve FramedBlocks/Create version conflict (F-01)
- [ ] Remove duplicate Citadel jar (F-02)
- [ ] Rotate RCON password; remove defaults from code (F-03)
- [ ] Provision CurseForge API key via secrets; gitignore `.env` (F-04)
- [ ] Right-size JVM heap; validate GC flags (F-05)
- [ ] Persist undo history + command audit log (F-06)
- [ ] Implement scheduled world backups (F-07)
- [ ] Restrict CORS; add HTTP API auth (F-09/F-11)
- [ ] Add permission gating to `!build`/`!undo` (AI builder)

---

## 9. Conclusion

The Bumcraft implementation is a coherent, itgz-pattern Forge 1.20.1 server with useful AI/RCON tooling. It is **not production-ready as-is**: the Create/FramedBlocks conflict prevents stable startup, and default credentials plus absent backups present operational risk. Applying the remediation checklist in Section 8 will bring it to a stable, maintainable baseline.

---

*Appendix: `docs/LLM_DISCLOSURE.md` describes AI usage in the production of this report.*