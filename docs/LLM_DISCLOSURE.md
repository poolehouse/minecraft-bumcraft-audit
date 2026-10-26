# LLM / AI Disclosure

## Statement

This repository — including all documentation, the audit report, configuration samples, and this disclosure — was **produced with the assistance of large language models (LLMs)**. The underlying Minecraft server files, mod jars, configuration values, and the two Python services (`mc_ai_builder.py`, `mc_rcon_api.py`) are **pre-existing artifacts authored by the server operator**; they were copied verbatim into `src/` and `configs/` and are not LLM-generated.

## What was AI-assisted

| Item | AI role | Human verification |
|---|---|---|
| Repository structure & OSS file set (README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, .gitignore, issue templates) | Drafted | Reviewed & adapted |
| `docs/AUDIT_REPORT.md` — full audit findings, severity ratings, remediation checklist | Drafted from inspected evidence | Verified against actual files & crash reports |
| `docs/ARCHITECTURE.md` | Drafted (mermaid diagram) | Verified against compose/Python code |
| `docs/SERVER_CONFIG.md` | Drafted from compose + properties | Verified line-for-line |
| `docs/MOD_INVENTORY.md` | Categorized from `ls` output | Verified against mod directory |
| `docs/CRASH_ANALYSIS.md` | Summarized crash reports | Verified against crash report text |
| `docs/AI_BUILDER.md` | Documented `mc_ai_builder.py` | Verified against source |
| `docs/RCON_API.md` | Documented `mc_rcon_api.py` | Verified against source |
| `docs/DEPLOYMENT.md` | Drafted deployment steps | Not executed; for operator review |
| `docs/LLM_DISCLOSURE.md` | Drafted | Reviewed |

## What was NOT AI-generated

- All server binaries, mod `.jar` files, the CurseForge modpack zip, world data, logs, and crash reports.
- The source code of `mc_ai_builder.py` and `mc_rcon_api.py` (copied verbatim; only docstring-level context was used for documentation).
- Configuration values (ports, passwords, memory, mod names, version strings).

## Limitations

- LLM-generated documentation may contain inaccuracies, especially regarding mod version compatibility and runtime behavior. Operators should verify all commands, versions, and credentials against a live/test instance before deployment.
- Severity ratings are best-effort community assessments, not a formal security audit by a credentialed firm.

## Attribution

If you reuse this documentation, please retain this disclosure and attribute the original server operator for the audited artifacts.