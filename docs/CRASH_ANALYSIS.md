# Crash Analysis — Bumcraft Server

Source: `minecraft-server-bumcraft/data/crash-reports/` (3 reports, all 2026-10-23)

## Crash reports on disk

| File | Time |
|---|---|
| `crash-2026-10-23_17.34.43-fml.txt` | 17:34:43 |
| `crash-2026-10-23_17.34.56-fml.txt` | 17:34:56 |
| `crash-2026-10-23_17.35.09-fml.txt` | 17:35:09 |

## Root cause (from `crash-..._17.35.09-fml.txt`)

All three are **FML mod-loading failures** (`java.lang.Exception: Mod Loading has occurred`). The `17:35:09` report identifies the failing mod:

```
-- MOD framedblocks --
Details:
  Mod File: /data/mods/FramedBlocks-9.4.3.jar
  Failure message: Mod framedblocks only supports create 6.0.2 or above
    Currently, create is 0.5.1.j
  Mod Version: 9.4.3
  Mod Issue URL: https://www.github.com/xfacthd/framedblocks
```

Note: the disk inventory lists `FramedBlocks-9.3.1.jar` while the crash report references `FramedBlocks-9.4.3.jar` — the mod was likely swapped/updated between crashes, but the Create version constraint remained unsatisfied.

## Timeline

- **17:34:43** — First FML mod-loading crash.
- **17:34:56** — Second crash (13s later), likely an immediate restart attempt.
- **17:35:09** — Third crash with the FramedBlocks/Create detail captured.

## Root cause summary

| Factor | Detail |
|---|---|
| Failing mod | FramedBlocks (requires Create >= 6.0.2) |
| Installed Create | `create-1.20.1-0.5.1.j.jar` (0.5.1.j) |
| Forge version | 47.3.0 (MC 1.20.1) |
| Result | Server cannot complete mod loading; exits on startup |

## Remediation

Choose one path:

**Option A — Upgrade Create (recommended for a Create-focused pack)**
1. Upgrade `create` to >= 6.0.2 (Forge 1.20.1).
2. Upgrade Create-dependent mods to match: `Create Central Kitchen`, `CreateBB`, `Create Enchantment Industry`, `Create Deco`, `Bop Create Mod Rose Quartz`, `WaystoneandCreate`, etc.
3. Keep `FramedBlocks`.
4. Rebuild the modpack zip and restart.

**Option B — Downgrade/remove FramedBlocks**
1. Remove `FramedBlocks` or replace with a version compatible with Create 0.5.1.j.
2. No Create ecosystem changes needed.
3. Rebuild the modpack zip and restart.

**Additionally:** remove the duplicate `citadel-2.6.1.jar` (keep `citadel-2.6.3.jar`) to avoid classloading ambiguity.

## Verification

After changes, start the server and confirm `latest.log` reaches `Forge Mod Loader has successfully loaded X mods` and the `Done` / `Timings` lines appear, with no `FML` crash report generated.
